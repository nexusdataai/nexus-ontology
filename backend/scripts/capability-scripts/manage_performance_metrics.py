#!/usr/bin/env python3
"""
Performance Metrics Management Script
Handles runtime metrics and health data for operational monitoring
"""

import boto3
import json
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from botocore.exceptions import ClientError
import statistics

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from db_utils import (
    get_table_name,
    get_dynamodb_resource,
    format_decimal,
    print_with_flush,
    get_current_timestamp
)


class PerformanceMetricsManager:
    """Manager for Performance Metrics operations"""
    
    def __init__(self, dynamodb=None):
        """
        Initialize the Performance Metrics Manager
        
        Args:
            dynamodb: Optional DynamoDB resource (for dependency injection/testing)
        """
        if dynamodb is not None:
            # Dependency injection mode (for testing)
            self.dynamodb = dynamodb
            self.table_name = get_table_name()
            self.table = self.dynamodb.Table(self.table_name) if hasattr(dynamodb, 'Table') else None
        else:
            # Normal operation - create AWS client
            self.dynamodb = get_dynamodb_resource()
            self.table_name = get_table_name()
            self.table = self.dynamodb.Table(self.table_name)
        
        # Metric types
        self.metric_types = [
            'performance', 'resource', 'business', 
            'quality', 'security', 'custom'
        ]
        
        # Intervals
        self.intervals = ['1m', '5m', '15m', '1h', '6h', '1d']
        
        # Health statuses
        self.health_statuses = ['healthy', 'degraded', 'unhealthy', 'critical', 'unknown']
        
        # Trend types
        self.trend_types = ['improving', 'stable', 'degrading', 'volatile']
        
        # Default TTL in days
        self.default_ttl_days = 90
    
    # ==================== METRIC CRUD OPERATIONS ====================
    
    def record_metric(self, capability_id: str, component_id: str, 
                     metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a performance metric
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
            metric_data: Dictionary containing metric details
            
        Returns:
            Created metric with metadata
        """
        try:
            timestamp = get_current_timestamp()
            metric_type = metric_data.get('metricType', 'performance')
            
            # Build the data structure
            data = {
                'componentId': component_id,
                'componentName': metric_data.get('componentName', component_id),
                'metricType': metric_type,
                'timestamp': timestamp,
                'interval': metric_data.get('interval', '1m'),
                'dimensions': metric_data.get('dimensions', {
                    'environment': 'production',
                    'region': 'us-east-1',
                    'availability_zone': 'us-east-1a'
                }),
                'values': metric_data.get('values', {}),
                'alerts': metric_data.get('alerts', {
                    'active': [],
                    'resolved': []
                }),
                'trends': metric_data.get('trends', {})
            }
            
            # Process and enrich metric values
            data['values'] = self._process_metric_values(data['values'], metric_type)
            
            # Calculate trends if not provided
            if not data['trends']:
                data['trends'] = self._calculate_trends(capability_id, component_id, data['values'])
            
            # Calculate TTL (90 days from now)
            ttl_timestamp = datetime.now(timezone.utc) + timedelta(days=self.default_ttl_days)
            ttl = int(ttl_timestamp.timestamp())
            
            # Create the DynamoDB item
            item = {
                'PK': f'CAPABILITY#{capability_id}',
                'SK': f'METRIC#{component_id}#{metric_type}#{timestamp}',
                'EntityType': 'PerformanceMetric',
                'GSI1PK': f'METRICS#{component_id}',
                'GSI1SK': timestamp,
                'CreatedAt': timestamp,
                'TTL': ttl,
                'Data': data
            }
            
            # Put item in DynamoDB
            self.table.put_item(Item=item)
            
            # Update component health status based on metrics
            self._update_component_health(capability_id, component_id, data['values'])
            
            print_with_flush(f"✅ Recorded metric for component: {component_id}")
            return item
            
        except ClientError as e:
            print_with_flush(f"❌ Error recording metric: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            print_with_flush(f"❌ Unexpected error: {str(e)}")
            raise
    
    def get_metrics(self, capability_id: str, component_id: str,
                   metric_type: Optional[str] = None,
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get metrics for a component
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
            metric_type: Optional metric type filter
            start_time: Start time for range query
            end_time: End time for range query
            limit: Maximum number of metrics to return
            
        Returns:
            List of metrics
        """
        try:
            metrics = []
            
            # Build the SK range based on parameters
            sk_prefix = f'METRIC#{component_id}#'
            if metric_type:
                sk_prefix += f'{metric_type}#'
            
            # Build key condition
            key_condition = 'PK = :pk AND begins_with(SK, :sk_prefix)'
            expression_values = {
                ':pk': f'CAPABILITY#{capability_id}',
                ':sk_prefix': sk_prefix
            }
            
            # Add time range if specified
            if start_time and end_time:
                key_condition = 'PK = :pk AND SK BETWEEN :start AND :end'
                expression_values[':start'] = f'{sk_prefix}{start_time}'
                expression_values[':end'] = f'{sk_prefix}{end_time}'
            elif start_time:
                key_condition = 'PK = :pk AND SK >= :start'
                expression_values[':start'] = f'{sk_prefix}{start_time}'
            
            # Query metrics
            response = self.table.query(
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=expression_values,
                ScanIndexForward=False,  # Newest first
                Limit=limit
            )
            
            metrics.extend(response.get('Items', []))
            
            print_with_flush(f"📊 Found {len(metrics)} metrics for component {component_id}")
            return metrics
            
        except ClientError as e:
            print_with_flush(f"❌ Error getting metrics: {e.response['Error']['Message']}")
            return []
    
    def get_latest_metrics(self, capability_id: str, 
                          component_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get the latest metrics for a capability or specific component
        
        Args:
            capability_id: The capability ID
            component_id: Optional component ID filter
            
        Returns:
            Latest metrics
        """
        try:
            # Get metrics from the last hour
            one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat() + 'Z'
            
            if component_id:
                return self.get_metrics(capability_id, component_id, 
                                      start_time=one_hour_ago, limit=10)
            else:
                # Get metrics for all components
                all_metrics = []
                
                # Query all recent metrics for the capability
                response = self.table.query(
                    KeyConditionExpression='PK = :pk AND SK >= :sk',
                    ExpressionAttributeValues={
                        ':pk': f'CAPABILITY#{capability_id}',
                        ':sk': f'METRIC#{one_hour_ago}'
                    },
                    ScanIndexForward=False,
                    Limit=100
                )
                
                all_metrics.extend(response.get('Items', []))
                return all_metrics
                
        except Exception as e:
            print_with_flush(f"❌ Error getting latest metrics: {str(e)}")
            return []
    
    def aggregate_metrics(self, metrics: List[Dict[str, Any]], 
                         aggregation_type: str = 'average') -> Dict[str, Any]:
        """
        Aggregate multiple metrics
        
        Args:
            metrics: List of metrics to aggregate
            aggregation_type: Type of aggregation (average, sum, max, min, p95)
            
        Returns:
            Aggregated metrics
        """
        if not metrics:
            return {}
        
        aggregated = {
            'metricType': 'aggregated',
            'aggregationType': aggregation_type,
            'sampleCount': len(metrics),
            'timeRange': {
                'start': None,
                'end': None
            },
            'values': {}
        }
        
        # Collect all values by metric name
        value_collections = {}
        
        for metric in metrics:
            data = metric.get('Data', {})
            values = data.get('values', {})
            
            # Update time range
            timestamp = data.get('timestamp')
            if timestamp:
                if not aggregated['timeRange']['start'] or timestamp < aggregated['timeRange']['start']:
                    aggregated['timeRange']['start'] = timestamp
                if not aggregated['timeRange']['end'] or timestamp > aggregated['timeRange']['end']:
                    aggregated['timeRange']['end'] = timestamp
            
            # Collect values
            for metric_name, metric_data in values.items():
                if metric_name not in value_collections:
                    value_collections[metric_name] = []
                
                # Extract numeric value
                if isinstance(metric_data, dict):
                    if 'value' in metric_data:
                        value_collections[metric_name].append(float(metric_data['value']))
                    elif 'p50' in metric_data:  # Latency metrics
                        value_collections[metric_name].append(float(metric_data['p50']))
                elif isinstance(metric_data, (int, float)):
                    value_collections[metric_name].append(float(metric_data))
        
        # Perform aggregation
        for metric_name, values in value_collections.items():
            if not values:
                continue
            
            if aggregation_type == 'average':
                aggregated['values'][metric_name] = statistics.mean(values)
            elif aggregation_type == 'sum':
                aggregated['values'][metric_name] = sum(values)
            elif aggregation_type == 'max':
                aggregated['values'][metric_name] = max(values)
            elif aggregation_type == 'min':
                aggregated['values'][metric_name] = min(values)
            elif aggregation_type == 'p95':
                sorted_values = sorted(values)
                index = int(len(sorted_values) * 0.95)
                aggregated['values'][metric_name] = sorted_values[index] if index < len(sorted_values) else sorted_values[-1]
            elif aggregation_type == 'median':
                aggregated['values'][metric_name] = statistics.median(values)
        
        return aggregated
    
    # ==================== HEALTH & ALERTING ====================
    
    def check_health_thresholds(self, metric_values: Dict[str, Any], 
                               thresholds: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Check metric values against health thresholds
        
        Args:
            metric_values: Current metric values
            thresholds: Threshold definitions
            
        Returns:
            Tuple of (health_status, list_of_violations)
        """
        violations = []
        severity_score = 0
        
        # Default thresholds if not provided
        default_thresholds = {
            'availability': {'critical': 95, 'warning': 99},
            'errorRate': {'critical': 5, 'warning': 1},
            'latency': {'critical': 1000, 'warning': 500},
            'cpu': {'critical': 90, 'warning': 80},
            'memory': {'critical': 90, 'warning': 80}
        }
        
        thresholds = {**default_thresholds, **thresholds}
        
        # Check each metric
        for metric_name, threshold in thresholds.items():
            if metric_name not in metric_values:
                continue
            
            value = metric_values[metric_name]
            if isinstance(value, dict):
                value = value.get('value', value.get('p50', 0))
            
            # Check thresholds
            if metric_name == 'availability':
                # Lower is worse for availability
                if value < threshold.get('critical', 95):
                    violations.append(f"{metric_name} is critical: {value}%")
                    severity_score += 3
                elif value < threshold.get('warning', 99):
                    violations.append(f"{metric_name} warning: {value}%")
                    severity_score += 1
            else:
                # Higher is worse for other metrics
                if value > threshold.get('critical', float('inf')):
                    violations.append(f"{metric_name} is critical: {value}")
                    severity_score += 3
                elif value > threshold.get('warning', float('inf')):
                    violations.append(f"{metric_name} warning: {value}")
                    severity_score += 1
        
        # Determine health status
        if severity_score >= 6:
            health_status = 'critical'
        elif severity_score >= 3:
            health_status = 'unhealthy'
        elif severity_score >= 1:
            health_status = 'degraded'
        else:
            health_status = 'healthy'
        
        return health_status, violations
    
    def create_alert(self, capability_id: str, component_id: str,
                    alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an alert for a component
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
            alert_data: Alert details
            
        Returns:
            Created alert
        """
        try:
            timestamp = get_current_timestamp()
            alert_id = f"ALT-{component_id[:8]}-{datetime.now().strftime('%H%M%S')}"
            
            alert = {
                'alertId': alert_id,
                'componentId': component_id,
                'condition': alert_data.get('condition', ''),
                'severity': alert_data.get('severity', 'warning'),
                'message': alert_data.get('message', ''),
                'triggeredAt': timestamp,
                'resolvedAt': None,
                'metricValues': alert_data.get('metricValues', {})
            }
            
            # Get latest metric for the component
            latest_metrics = self.get_latest_metrics(capability_id, component_id)
            
            if latest_metrics:
                # Add alert to the latest metric
                latest = latest_metrics[0]
                data = latest.get('Data', {})
                if 'alerts' not in data:
                    data['alerts'] = {'active': [], 'resolved': []}
                
                data['alerts']['active'].append(alert)
                
                # Update the metric with the alert
                self.table.update_item(
                    Key={
                        'PK': latest['PK'],
                        'SK': latest['SK']
                    },
                    UpdateExpression='SET #data = :data',
                    ExpressionAttributeNames={'#data': 'Data'},
                    ExpressionAttributeValues={':data': data}
                )
            
            print_with_flush(f"🚨 Created alert {alert_id} for component {component_id}")
            return alert
            
        except Exception as e:
            print_with_flush(f"❌ Error creating alert: {str(e)}")
            raise
    
    # ==================== ANALYSIS FUNCTIONS ====================
    
    def _process_metric_values(self, values: Dict[str, Any], 
                              metric_type: str) -> Dict[str, Any]:
        """
        Process and enrich metric values based on type
        
        Args:
            values: Raw metric values
            metric_type: Type of metric
            
        Returns:
            Processed values
        """
        processed = {}
        
        if metric_type == 'performance':
            # Standard performance metrics
            for key in ['availability', 'latency', 'throughput', 'errors', 'saturation']:
                if key in values:
                    processed[key] = values[key]
                    
                    # Add status based on value
                    if key == 'availability':
                        value = values[key].get('value', 0) if isinstance(values[key], dict) else values[key]
                        processed[key] = {
                            'value': value,
                            'unit': 'percent',
                            'status': 'healthy' if value >= 99.9 else 'degraded' if value >= 99 else 'unhealthy'
                        }
                    elif key == 'latency':
                        if isinstance(values[key], dict):
                            processed[key] = values[key]
                        else:
                            processed[key] = {
                                'p50': values[key],
                                'p95': values[key] * 1.5,
                                'p99': values[key] * 2,
                                'unit': 'milliseconds'
                            }
        
        elif metric_type == 'resource':
            # Resource utilization metrics
            for key in ['cpu', 'memory', 'disk', 'network', 'connections']:
                if key in values:
                    value = values[key]
                    processed[key] = {
                        'value': value,
                        'unit': 'percent' if key in ['cpu', 'memory', 'disk'] else 'count',
                        'status': 'healthy' if value < 80 else 'degraded' if value < 90 else 'unhealthy'
                    }
        
        elif metric_type == 'business':
            # Business metrics
            processed = values  # Keep as-is for business metrics
        
        else:
            # Default processing
            processed = values
        
        return processed
    
    def _calculate_trends(self, capability_id: str, component_id: str,
                        current_values: Dict[str, Any]) -> Dict[str, str]:
        """
        Calculate trends by comparing with historical data
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
            current_values: Current metric values
            
        Returns:
            Trend analysis
        """
        trends = {}
        
        try:
            # Get metrics from the last hour
            one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat() + 'Z'
            historical_metrics = self.get_metrics(
                capability_id, component_id,
                start_time=one_hour_ago,
                limit=60
            )
            
            if len(historical_metrics) < 2:
                # Not enough data for trends
                for key in current_values:
                    trends[key] = 'stable'
                return trends
            
            # Analyze each metric
            for metric_name in current_values:
                historical_values = []
                
                for metric in historical_metrics:
                    data = metric.get('Data', {})
                    values = data.get('values', {})
                    if metric_name in values:
                        value = values[metric_name]
                        if isinstance(value, dict):
                            value = value.get('value', value.get('p50', 0))
                        historical_values.append(float(value))
                
                if len(historical_values) < 2:
                    trends[metric_name] = 'stable'
                    continue
                
                # Calculate trend
                avg_old = statistics.mean(historical_values[:len(historical_values)//2])
                avg_new = statistics.mean(historical_values[len(historical_values)//2:])
                
                change_percent = ((avg_new - avg_old) / avg_old * 100) if avg_old != 0 else 0
                
                # Determine trend
                if abs(change_percent) < 5:
                    trends[metric_name] = 'stable'
                elif change_percent > 0:
                    # For availability, increasing is good
                    if metric_name == 'availability':
                        trends[metric_name] = 'improving'
                    else:
                        # For most metrics, increasing is bad
                        trends[metric_name] = 'degrading'
                else:
                    # For availability, decreasing is bad
                    if metric_name == 'availability':
                        trends[metric_name] = 'degrading'
                    else:
                        trends[metric_name] = 'improving'
            
        except Exception as e:
            print_with_flush(f"⚠️ Error calculating trends: {str(e)}")
            # Default to stable
            for key in current_values:
                trends[key] = 'stable'
        
        return trends
    
    def _update_component_health(self, capability_id: str, component_id: str,
                                metric_values: Dict[str, Any]):
        """
        Update component health status based on metrics
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
            metric_values: Current metric values
        """
        try:
            # Check health thresholds
            health_status, violations = self.check_health_thresholds(metric_values, {})
            
            # Create alerts for violations
            if violations:
                for violation in violations:
                    if 'critical' in violation:
                        self.create_alert(capability_id, component_id, {
                            'condition': violation,
                            'severity': 'critical',
                            'message': f"Component health check failed: {violation}",
                            'metricValues': metric_values
                        })
            
            print_with_flush(f"💓 Component {component_id} health: {health_status}")
            
        except Exception as e:
            print_with_flush(f"⚠️ Error updating component health: {str(e)}")
    
    # ==================== DISPLAY FUNCTIONS ====================
    
    def display_metric(self, metric: Dict[str, Any]):
        """Display metric details in a formatted way"""
        data = metric.get('Data', {})
        
        print_with_flush("\n" + "="*80)
        print_with_flush(f"📊 METRIC: {data.get('componentName', 'Unknown')} - {data.get('metricType', 'Unknown')}")
        print_with_flush("="*80)
        
        # Basic Information
        print_with_flush("\n📋 BASIC INFORMATION:")
        print_with_flush(f"  Component ID: {data.get('componentId', 'N/A')}")
        print_with_flush(f"  Type: {data.get('metricType', 'N/A')}")
        print_with_flush(f"  Timestamp: {data.get('timestamp', 'N/A')}")
        print_with_flush(f"  Interval: {data.get('interval', 'N/A')}")
        
        # Dimensions
        dimensions = data.get('dimensions', {})
        if dimensions:
            print_with_flush("\n🌍 DIMENSIONS:")
            for key, value in dimensions.items():
                print_with_flush(f"  {key}: {value}")
        
        # Values
        values = data.get('values', {})
        if values:
            print_with_flush("\n📈 VALUES:")
            for metric_name, metric_data in values.items():
                if isinstance(metric_data, dict):
                    status = metric_data.get('status', '')
                    status_icon = {
                        'healthy': '✅',
                        'degraded': '⚠️',
                        'unhealthy': '❌',
                        'critical': '🔴'
                    }.get(status, '')
                    
                    if 'value' in metric_data:
                        print_with_flush(f"  {metric_name}: {metric_data['value']} {metric_data.get('unit', '')} {status_icon}")
                    elif 'p50' in metric_data:
                        print_with_flush(f"  {metric_name}:")
                        print_with_flush(f"    p50: {metric_data.get('p50', 'N/A')}ms")
                        print_with_flush(f"    p95: {metric_data.get('p95', 'N/A')}ms")
                        print_with_flush(f"    p99: {metric_data.get('p99', 'N/A')}ms")
                    else:
                        print_with_flush(f"  {metric_name}: {json.dumps(metric_data)}")
                else:
                    print_with_flush(f"  {metric_name}: {metric_data}")
        
        # Trends
        trends = data.get('trends', {})
        if trends:
            print_with_flush("\n📊 TRENDS:")
            for metric_name, trend in trends.items():
                trend_icon = {
                    'improving': '📈',
                    'stable': '➡️',
                    'degrading': '📉',
                    'volatile': '📊'
                }.get(trend, '❓')
                print_with_flush(f"  {metric_name}: {trend_icon} {trend}")
        
        # Alerts
        alerts = data.get('alerts', {})
        if alerts:
            active = alerts.get('active', [])
            resolved = alerts.get('resolved', [])
            
            if active:
                print_with_flush("\n🚨 ACTIVE ALERTS:")
                for alert in active:
                    print_with_flush(f"  • {alert.get('alertId', 'N/A')}: {alert.get('message', 'N/A')}")
                    print_with_flush(f"    Severity: {alert.get('severity', 'N/A')}")
                    print_with_flush(f"    Triggered: {alert.get('triggeredAt', 'N/A')}")
            
            if resolved:
                print_with_flush("\n✅ RESOLVED ALERTS:")
                for alert in resolved:
                    print_with_flush(f"  • {alert.get('alertId', 'N/A')}")
                    print_with_flush(f"    Resolved: {alert.get('resolvedAt', 'N/A')}")
        
        print_with_flush("\n" + "="*80)
    
    def display_metrics_summary(self, metrics: List[Dict[str, Any]]):
        """Display summary of multiple metrics"""
        if not metrics:
            print_with_flush("No metrics found")
            return
        
        print_with_flush("\n" + "="*100)
        print_with_flush("📊 METRICS SUMMARY")
        print_with_flush("="*100)
        
        # Group by component
        by_component = {}
        for metric in metrics:
            data = metric.get('Data', {})
            comp_id = data.get('componentId', 'Unknown')
            if comp_id not in by_component:
                by_component[comp_id] = []
            by_component[comp_id].append(metric)
        
        for comp_id, comp_metrics in by_component.items():
            print_with_flush(f"\n🔧 Component: {comp_id}")
            print_with_flush("-"*50)
            
            # Get latest metric
            latest = comp_metrics[0]  # Already sorted newest first
            data = latest.get('Data', {})
            values = data.get('values', {})
            
            # Display key metrics
            if 'availability' in values:
                avail = values['availability']
                avail_value = avail.get('value', avail) if isinstance(avail, dict) else avail
                print_with_flush(f"  Availability: {avail_value}%")
            
            if 'latency' in values:
                latency = values['latency']
                if isinstance(latency, dict):
                    print_with_flush(f"  Latency: p50={latency.get('p50', 'N/A')}ms, p99={latency.get('p99', 'N/A')}ms")
            
            if 'errorRate' in values or 'errors' in values:
                errors = values.get('errorRate', values.get('errors', {}))
                if isinstance(errors, dict):
                    error_rate = errors.get('rate', errors.get('value', 'N/A'))
                else:
                    error_rate = errors
                print_with_flush(f"  Error Rate: {error_rate}%")
            
            # Show alerts
            alerts = data.get('alerts', {})
            active_alerts = alerts.get('active', [])
            if active_alerts:
                print_with_flush(f"  ⚠️ Active Alerts: {len(active_alerts)}")
            
            # Show trends
            trends = data.get('trends', {})
            if trends:
                trend_summary = []
                for metric_name, trend in trends.items():
                    if trend != 'stable':
                        trend_summary.append(f"{metric_name} is {trend}")
                if trend_summary:
                    print_with_flush(f"  Trends: {', '.join(trend_summary)}")
        
        print_with_flush("\n" + "="*100)
        print_with_flush(f"Total metrics: {len(metrics)}")


def main():
    """Main function for testing"""
    print_with_flush("\n📊 PERFORMANCE METRICS MANAGEMENT SYSTEM")
    print_with_flush("="*60)
    
    # Get capability and component IDs
    capability_id = input("Enter capability ID (or 'test' for testing): ").strip() or 'test'
    component_id = input("Enter component ID (or 'test-comp' for testing): ").strip() or 'test-comp'
    
    manager = PerformanceMetricsManager()
    
    while True:
        print_with_flush("\n📋 MAIN MENU:")
        print_with_flush("1. Record metric")
        print_with_flush("2. View latest metrics")
        print_with_flush("3. View metric history")
        print_with_flush("4. Aggregate metrics")
        print_with_flush("5. Create alert")
        print_with_flush("6. Check health status")
        print_with_flush("7. View metrics summary")
        print_with_flush("0. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            # Record metric
            print_with_flush("\n📝 Enter metric details:")
            metric_type = input(f"Metric type ({'/'.join(manager.metric_types)}): ").strip() or 'performance'
            
            values = {}
            if metric_type == 'performance':
                avail = input("Availability % (0-100): ").strip()
                if avail:
                    values['availability'] = {'value': float(avail), 'unit': 'percent'}
                
                latency = input("Latency (ms): ").strip()
                if latency:
                    values['latency'] = {'p50': float(latency), 'p95': float(latency) * 1.5, 'p99': float(latency) * 2}
                
                error_rate = input("Error rate % (0-100): ").strip()
                if error_rate:
                    values['errorRate'] = {'value': float(error_rate), 'unit': 'percent'}
            
            elif metric_type == 'resource':
                cpu = input("CPU usage % (0-100): ").strip()
                if cpu:
                    values['cpu'] = float(cpu)
                
                memory = input("Memory usage % (0-100): ").strip()
                if memory:
                    values['memory'] = float(memory)
            
            metric_data = {
                'metricType': metric_type,
                'componentName': component_id,
                'values': values
            }
            
            metric = manager.record_metric(capability_id, component_id, metric_data)
            if metric:
                manager.display_metric(metric)
                
        elif choice == '2':
            # View latest metrics
            metrics = manager.get_latest_metrics(capability_id, component_id)
            if metrics:
                for metric in metrics[:3]:  # Show last 3
                    manager.display_metric(metric)
            else:
                print_with_flush("No recent metrics found")
                
        elif choice == '3':
            # View metric history
            hours = input("Hours of history (default 1): ").strip()
            hours = int(hours) if hours else 1
            
            start_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat() + 'Z'
            metrics = manager.get_metrics(capability_id, component_id, start_time=start_time)
            
            if metrics:
                manager.display_metrics_summary(metrics)
            else:
                print_with_flush("No metrics found")
                
        elif choice == '4':
            # Aggregate metrics
            hours = input("Hours to aggregate (default 1): ").strip()
            hours = int(hours) if hours else 1
            
            start_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat() + 'Z'
            metrics = manager.get_metrics(capability_id, component_id, start_time=start_time)
            
            if metrics:
                agg_type = input("Aggregation type (average/max/min/p95) [average]: ").strip() or 'average'
                aggregated = manager.aggregate_metrics(metrics, agg_type)
                
                print_with_flush("\n📊 AGGREGATED METRICS:")
                print_with_flush("="*40)
                print_with_flush(f"Type: {aggregated.get('aggregationType', 'N/A')}")
                print_with_flush(f"Samples: {aggregated.get('sampleCount', 0)}")
                print_with_flush(f"Time Range: {aggregated.get('timeRange', {}).get('start', 'N/A')} to {aggregated.get('timeRange', {}).get('end', 'N/A')}")
                print_with_flush("\nValues:")
                for name, value in aggregated.get('values', {}).items():
                    print_with_flush(f"  {name}: {value:.2f}")
                print_with_flush("="*40)
            else:
                print_with_flush("No metrics to aggregate")
                
        elif choice == '5':
            # Create alert
            print_with_flush("\n🚨 Create Alert:")
            condition = input("Alert condition: ").strip()
            severity = input("Severity (warning/critical) [warning]: ").strip() or 'warning'
            message = input("Alert message: ").strip()
            
            alert_data = {
                'condition': condition,
                'severity': severity,
                'message': message
            }
            
            alert = manager.create_alert(capability_id, component_id, alert_data)
            if alert:
                print_with_flush(f"✅ Alert created: {alert.get('alertId', 'N/A')}")
                
        elif choice == '6':
            # Check health status
            # Get latest metrics
            metrics = manager.get_latest_metrics(capability_id, component_id)
            if metrics:
                latest = metrics[0]
                data = latest.get('Data', {})
                values = data.get('values', {})
                
                health_status, violations = manager.check_health_thresholds(values, {})
                
                print_with_flush("\n❤️ HEALTH CHECK:")
                print_with_flush("="*40)
                print_with_flush(f"Status: {health_status}")
                if violations:
                    print_with_flush("\nViolations:")
                    for violation in violations:
                        print_with_flush(f"  • {violation}")
                else:
                    print_with_flush("✅ All metrics within healthy thresholds")
                print_with_flush("="*40)
            else:
                print_with_flush("No metrics available for health check")
                
        elif choice == '7':
            # View metrics summary
            metrics = manager.get_latest_metrics(capability_id)
            if metrics:
                manager.display_metrics_summary(metrics)
            else:
                print_with_flush("No metrics found")
                
        elif choice == '0':
            print_with_flush("\n👋 Goodbye!")
            break
        else:
            print_with_flush("❌ Invalid choice")


if __name__ == "__main__":
    main()
