#!/usr/bin/env python3
"""
Server Health Monitor for BDD Endurance Testing
Collects system and application metrics during endurance test runs
"""

import os
import time
import psutil
import threading
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import logging
import subprocess
import boto3
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class ServerHealthMonitor:
    """Monitor server health metrics during endurance testing"""
    
    def __init__(self, 
                 interval_seconds: int = 10,
                 history_size: int = 360,  # 1 hour of 10-second intervals
                 thresholds: Optional[Dict[str, Any]] = None):
        """Initialize health monitor
        
        Args:
            interval_seconds: Sampling interval for metrics
            history_size: Number of historical samples to keep
            thresholds: Alert thresholds for metrics
        """
        self.interval = interval_seconds
        self.history_size = history_size
        self.thresholds = thresholds or self._get_default_thresholds()
        
        # Metric storage
        self.metrics_history = {
            'timestamps': deque(maxlen=history_size),
            'cpu': deque(maxlen=history_size),
            'memory': deque(maxlen=history_size),
            'swap': deque(maxlen=history_size),
            'disk_io': deque(maxlen=history_size),
            'network_io': deque(maxlen=history_size),
            'file_descriptors': deque(maxlen=history_size),
            'threads': deque(maxlen=history_size),
            'processes': deque(maxlen=history_size),
            'connections': deque(maxlen=history_size),
            'response_times': deque(maxlen=history_size),
        }
        
        # Process tracking
        self.monitored_processes = {}
        self.baseline_metrics = None
        self.alerts = []
        
        # Control flags
        self.monitoring = False
        self.monitor_thread = None
        
        # Application-specific monitors
        self.mcp_server_pid = None
        self.cli_processes = []
        self.dynamodb_client = None
        
    def _get_default_thresholds(self) -> Dict[str, Any]:
        """Get default alert thresholds"""
        return {
            'cpu_percent': 80.0,
            'memory_gb': 8.0,  # Raised from 4.0 to match config default
            'memory_growth_mb_per_hour': 100,
            'swap_percent': 20.0,
            'file_descriptors': 1000,
            'threads': 500,
            'response_time_ms': 5000,
            'error_rate_percent': 5.0,
            'disk_usage_percent': 90.0,
        }
    
    def start_monitoring(self, 
                        mcp_server_pid: Optional[int] = None,
                        dynamodb_region: str = 'us-east-1') -> None:
        """Start monitoring in a background thread
        
        Args:
            mcp_server_pid: PID of MCP server process to monitor
            dynamodb_region: AWS region for DynamoDB monitoring
        """
        if self.monitoring:
            logger.warning("Monitoring already started")
            return
            
        self.monitoring = True
        self.mcp_server_pid = mcp_server_pid
        
        # Initialize DynamoDB client if needed
        if dynamodb_region:
            try:
                self.dynamodb_client = boto3.client('dynamodb', region_name=dynamodb_region)
            except Exception as e:
                logger.warning(f"Could not initialize DynamoDB client: {e}")
        
        # Capture baseline metrics
        self.baseline_metrics = self._collect_metrics()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Health monitoring started")
        
    def stop_monitoring(self) -> None:
        """Stop the monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=self.interval + 5)
        logger.info("Health monitoring stopped")
        
    def _monitoring_loop(self) -> None:
        """Main monitoring loop running in background thread"""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                self._store_metrics(metrics)
                self._check_thresholds(metrics)
                self._detect_leaks(metrics)
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                
            time.sleep(self.interval)
            
    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current system and application metrics"""
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'system': self._collect_system_metrics(),
            'application': self._collect_application_metrics(),
        }
        return metrics
        
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_usage = psutil.disk_usage('/')
        
        # Network I/O
        net_io = psutil.net_io_counters()
        
        # File descriptors (Linux only)
        try:
            fd_info = self._get_file_descriptors()
        except:
            fd_info = {'open': 0, 'max': 0}
            
        # Process and thread counts
        process_count = len(psutil.pids())
        
        # Get thread count for current process
        current_process = psutil.Process()
        thread_count = current_process.num_threads()
        
        # Network connections
        connections = len(psutil.net_connections())
        
        return {
            'cpu': {
                'percent': cpu_percent,
                'per_core': cpu_per_core,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
            },
            'memory': {
                'total_gb': memory.total / (1024**3),
                'used_gb': memory.used / (1024**3),
                'available_gb': memory.available / (1024**3),
                'percent': memory.percent,
                'rss_mb': current_process.memory_info().rss / (1024**2),
                'vms_mb': current_process.memory_info().vms / (1024**2),
            },
            'swap': {
                'total_gb': swap.total / (1024**3),
                'used_gb': swap.used / (1024**3),
                'percent': swap.percent,
            },
            'disk': {
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0,
                'usage_percent': disk_usage.percent,
                'free_gb': disk_usage.free / (1024**3),
            },
            'network': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
            },
            'resources': {
                'file_descriptors': fd_info,
                'threads': thread_count,
                'processes': process_count,
                'connections': connections,
            },
        }
        
    def _collect_application_metrics(self) -> Dict[str, Any]:
        """Collect application-specific metrics"""
        metrics = {}
        
        # MCP server metrics
        if self.mcp_server_pid:
            try:
                mcp_process = psutil.Process(self.mcp_server_pid)
                metrics['mcp_server'] = {
                    'cpu_percent': mcp_process.cpu_percent(),
                    'memory_mb': mcp_process.memory_info().rss / (1024**2),
                    'threads': mcp_process.num_threads(),
                    'connections': len(mcp_process.connections()),
                    'status': mcp_process.status(),
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                metrics['mcp_server'] = {'status': 'not_found'}
                
        # CLI process metrics
        cli_metrics = []
        for pid in self.cli_processes[:]:  # Copy list to avoid modification during iteration
            try:
                proc = psutil.Process(pid)
                cli_metrics.append({
                    'pid': pid,
                    'cpu_percent': proc.cpu_percent(),
                    'memory_mb': proc.memory_info().rss / (1024**2),
                    'status': proc.status(),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.cli_processes.remove(pid)
                
        metrics['cli_processes'] = cli_metrics
        metrics['active_cli_count'] = len(cli_metrics)
        
        # DynamoDB metrics
        if self.dynamodb_client:
            metrics['dynamodb'] = self._collect_dynamodb_metrics()
            
        return metrics
        
    def _collect_dynamodb_metrics(self) -> Dict[str, Any]:
        """Collect DynamoDB metrics"""
        try:
            # Get table description
            response = self.dynamodb_client.describe_table(
                TableName='aurorastack-transformation-jobs'
            )
            
            table = response['Table']
            return {
                'item_count': table.get('ItemCount', 0),
                'table_size_bytes': table.get('TableSizeBytes', 0),
                'table_status': table.get('TableStatus', 'UNKNOWN'),
            }
        except Exception as e:
            return {'error': str(e)}
            
    def _get_file_descriptors(self) -> Dict[str, int]:
        """Get file descriptor information (Linux only)"""
        try:
            # Get open file descriptors
            pid = os.getpid()
            fd_path = f'/proc/{pid}/fd'
            open_fds = len(os.listdir(fd_path))
            
            # Get max file descriptors
            with open(f'/proc/{pid}/limits', 'r') as f:
                for line in f:
                    if 'open files' in line.lower():
                        parts = line.split()
                        max_fds = int(parts[-1])
                        break
                else:
                    max_fds = 0
                    
            return {'open': open_fds, 'max': max_fds}
        except:
            # Fallback for non-Linux systems
            import resource
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            return {'open': 0, 'max': soft}
            
    def _store_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store metrics in history"""
        self.metrics_history['timestamps'].append(metrics['timestamp'])
        
        system = metrics['system']
        self.metrics_history['cpu'].append(system['cpu']['percent'])
        self.metrics_history['memory'].append(system['memory']['used_gb'])
        self.metrics_history['swap'].append(system['swap']['percent'])
        self.metrics_history['disk_io'].append({
            'read': system['disk']['read_bytes'],
            'write': system['disk']['write_bytes'],
        })
        self.metrics_history['network_io'].append({
            'sent': system['network']['bytes_sent'],
            'recv': system['network']['bytes_recv'],
        })
        self.metrics_history['file_descriptors'].append(system['resources']['file_descriptors']['open'])
        self.metrics_history['threads'].append(system['resources']['threads'])
        self.metrics_history['processes'].append(system['resources']['processes'])
        self.metrics_history['connections'].append(system['resources']['connections'])
        
    def _check_thresholds(self, metrics: Dict[str, Any]) -> None:
        """Check metrics against thresholds and generate alerts"""
        system = metrics['system']
        timestamp = metrics['timestamp']
        
        # CPU threshold
        if system['cpu']['percent'] > self.thresholds['cpu_percent']:
            self._add_alert('HIGH_CPU', f"CPU usage {system['cpu']['percent']:.1f}% exceeds threshold", timestamp)
            
        # Memory threshold
        if system['memory']['used_gb'] > self.thresholds['memory_gb']:
            self._add_alert('HIGH_MEMORY', f"Memory usage {system['memory']['used_gb']:.2f}GB exceeds threshold", timestamp)
            
        # Swap threshold
        if system['swap']['percent'] > self.thresholds['swap_percent']:
            self._add_alert('HIGH_SWAP', f"Swap usage {system['swap']['percent']:.1f}% exceeds threshold", timestamp)
            
        # File descriptors threshold
        fd = system['resources']['file_descriptors']
        if fd['open'] > self.thresholds['file_descriptors']:
            self._add_alert('HIGH_FD', f"File descriptors {fd['open']} exceeds threshold", timestamp)
            
        # Thread threshold
        if system['resources']['threads'] > self.thresholds['threads']:
            self._add_alert('HIGH_THREADS', f"Thread count {system['resources']['threads']} exceeds threshold", timestamp)
            
        # Disk usage threshold
        if system['disk']['usage_percent'] > self.thresholds['disk_usage_percent']:
            self._add_alert('HIGH_DISK', f"Disk usage {system['disk']['usage_percent']:.1f}% exceeds threshold", timestamp)
            
    def _detect_leaks(self, metrics: Dict[str, Any]) -> None:
        """Detect resource leaks by analyzing trends"""
        if not self.baseline_metrics or len(self.metrics_history['memory']) < 10:
            return
            
        # Memory leak detection
        current_memory = metrics['system']['memory']['rss_mb']
        baseline_memory = self.baseline_metrics['system']['memory']['rss_mb']
        time_elapsed_hours = len(self.metrics_history['memory']) * self.interval / 3600
        
        if time_elapsed_hours > 0:
            memory_growth_rate = (current_memory - baseline_memory) / time_elapsed_hours
            
            if memory_growth_rate > self.thresholds['memory_growth_mb_per_hour']:
                self._add_alert('MEMORY_LEAK', 
                              f"Memory growing at {memory_growth_rate:.2f}MB/hour", 
                              metrics['timestamp'])
                
        # File descriptor leak detection
        if len(self.metrics_history['file_descriptors']) >= 10:
            recent_fds = list(self.metrics_history['file_descriptors'])[-10:]
            if all(recent_fds[i] <= recent_fds[i+1] for i in range(9)):
                # Monotonically increasing
                growth = recent_fds[-1] - recent_fds[0]
                if growth > 50:  # More than 50 FDs in 10 samples
                    self._add_alert('FD_LEAK', 
                                  f"File descriptors increasing: +{growth} in last {10*self.interval}s", 
                                  metrics['timestamp'])
                    
    def _add_alert(self, alert_type: str, message: str, timestamp: str) -> None:
        """Add an alert to the list"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': timestamp,
        }
        self.alerts.append(alert)
        logger.warning(f"ALERT: {alert_type} - {message}")
        
    def register_cli_process(self, pid: int) -> None:
        """Register a CLI process for monitoring"""
        if pid not in self.cli_processes:
            self.cli_processes.append(pid)
            logger.debug(f"Registered CLI process {pid} for monitoring")
            
    def unregister_cli_process(self, pid: int) -> None:
        """Unregister a CLI process from monitoring"""
        if pid in self.cli_processes:
            self.cli_processes.remove(pid)
            logger.debug(f"Unregistered CLI process {pid}")
            
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the monitoring period"""
        if not self.metrics_history['cpu']:
            return {}
            
        return {
            'duration_seconds': len(self.metrics_history['cpu']) * self.interval,
            'samples_collected': len(self.metrics_history['cpu']),
            'cpu': {
                'mean': statistics.mean(self.metrics_history['cpu']),
                'max': max(self.metrics_history['cpu']),
                'min': min(self.metrics_history['cpu']),
                'stdev': statistics.stdev(self.metrics_history['cpu']) if len(self.metrics_history['cpu']) > 1 else 0,
            },
            'memory_gb': {
                'mean': statistics.mean(self.metrics_history['memory']),
                'max': max(self.metrics_history['memory']),
                'min': min(self.metrics_history['memory']),
                'growth': self.metrics_history['memory'][-1] - self.metrics_history['memory'][0] if self.metrics_history['memory'] else 0,
            },
            'file_descriptors': {
                'max': max(self.metrics_history['file_descriptors']),
                'final': self.metrics_history['file_descriptors'][-1] if self.metrics_history['file_descriptors'] else 0,
            },
            'threads': {
                'max': max(self.metrics_history['threads']),
                'final': self.metrics_history['threads'][-1] if self.metrics_history['threads'] else 0,
            },
            'alerts': len(self.alerts),
            'alert_types': list(set(a['type'] for a in self.alerts)),
        }
        
    def export_metrics(self, output_file: str) -> None:
        """Export collected metrics to a file
        
        Args:
            output_file: Path to output JSON file
        """
        data = {
            'summary': self.get_summary_stats(),
            'alerts': self.alerts,
            'history': {
                'timestamps': list(self.metrics_history['timestamps']),
                'cpu': list(self.metrics_history['cpu']),
                'memory': list(self.metrics_history['memory']),
                'swap': list(self.metrics_history['swap']),
                'file_descriptors': list(self.metrics_history['file_descriptors']),
                'threads': list(self.metrics_history['threads']),
                'processes': list(self.metrics_history['processes']),
                'connections': list(self.metrics_history['connections']),
            },
            'thresholds': self.thresholds,
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
        logger.info(f"Metrics exported to {output_file}")
        
    def is_healthy(self) -> bool:
        """Check if system is healthy based on alerts and thresholds
        
        Returns:
            True if healthy, False if critical issues detected
        """
        # Check for critical alerts
        critical_alerts = ['MEMORY_LEAK', 'FD_LEAK', 'HIGH_MEMORY', 'HIGH_SWAP']
        for alert in self.alerts:
            if alert['type'] in critical_alerts:
                return False
                
        # Check current metrics if available
        if self.metrics_history['memory']:
            # Memory doubled from baseline
            if self.baseline_metrics:
                current = self.metrics_history['memory'][-1]
                baseline = self.baseline_metrics['system']['memory']['used_gb']
                if current > baseline * 2:
                    return False
                    
        return True


if __name__ == "__main__":
    # Test the health monitor
    monitor = ServerHealthMonitor(interval_seconds=5)
    monitor.start_monitoring()
    
    print("Monitoring for 30 seconds...")
    time.sleep(30)
    
    monitor.stop_monitoring()
    
    # Print summary
    stats = monitor.get_summary_stats()
    print("\nSummary Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Export metrics
    monitor.export_metrics("health_metrics_test.json")
