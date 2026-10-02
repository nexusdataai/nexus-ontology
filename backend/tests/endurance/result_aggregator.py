#!/usr/bin/env python3
"""
Test Result Aggregator for BDD Endurance Testing
Collects, analyzes, and aggregates test results over time
"""

import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ResultAggregator:
    """Aggregates and analyzes BDD test results during endurance testing"""
    
    def __init__(self):
        """Initialize result aggregator"""
        self.results = []
        self.scenario_stats = defaultdict(lambda: {
            'total_runs': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'timeouts': 0,
            'execution_times': [],
            'failure_reasons': [],
            'last_status': None,
            'flaky_score': 0,
        })
        
        self.time_buckets = {}  # Results grouped by time intervals
        self.performance_trends = []
        self.error_patterns = Counter()
        self.flaky_tests = set()
        
    def add_result(self, result: Dict[str, Any]) -> None:
        """Add a test result to the aggregator
        
        Args:
            result: Test execution result containing scenario, status, timing, etc.
        """
        self.results.append(result)
        
        # Extract scenario key
        scenario = result.get('scenario', {})
        scenario_key = f"{scenario.get('feature', 'Unknown')} - {scenario.get('scenario', 'Unknown')}"
        
        # Update scenario statistics
        self._update_scenario_stats(scenario_key, result)
        
        # Update time-based buckets
        self._update_time_buckets(result)
        
        # Analyze for patterns
        self._analyze_patterns(scenario_key, result)
        
    def _update_scenario_stats(self, scenario_key: str, result: Dict[str, Any]) -> None:
        """Update statistics for a specific scenario"""
        stats = self.scenario_stats[scenario_key]
        stats['total_runs'] += 1
        
        status = result.get('result', {}).get('status', 'error')
        execution_time = result.get('execution_time', 0)
        
        if status == 'passed':
            stats['passed'] += 1
        elif status == 'failed':
            stats['failed'] += 1
            # Track failure reason
            error = result.get('result', {}).get('error', 'Unknown error')
            stats['failure_reasons'].append({
                'timestamp': result.get('timestamp'),
                'error': error[:200],  # Limit error message length
            })
        elif status == 'timeout':
            stats['timeouts'] += 1
        else:
            stats['errors'] += 1
            
        stats['execution_times'].append(execution_time)
        stats['last_status'] = status
        
        # Calculate flaky score
        if stats['total_runs'] >= 5:
            # Test is considered flaky if it has both passes and failures
            if stats['passed'] > 0 and (stats['failed'] + stats['errors']) > 0:
                failure_rate = (stats['failed'] + stats['errors']) / stats['total_runs']
                if 0.1 < failure_rate < 0.9:  # Between 10% and 90% failure rate
                    stats['flaky_score'] = min(failure_rate * 2, 1.0)
                    self.flaky_tests.add(scenario_key)
                    
    def _update_time_buckets(self, result: Dict[str, Any]) -> None:
        """Group results into time buckets for trend analysis"""
        timestamp = result.get('timestamp')
        if not timestamp:
            return
            
        # Create 5-minute buckets
        dt = datetime.fromisoformat(timestamp)
        bucket_key = dt.replace(minute=dt.minute // 5 * 5, second=0, microsecond=0)
        
        if bucket_key not in self.time_buckets:
            self.time_buckets[bucket_key] = {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'execution_times': [],
            }
            
        bucket = self.time_buckets[bucket_key]
        bucket['total'] += 1
        
        status = result.get('result', {}).get('status', 'error')
        if status == 'passed':
            bucket['passed'] += 1
        elif status == 'failed':
            bucket['failed'] += 1
        else:
            bucket['errors'] += 1
            
        bucket['execution_times'].append(result.get('execution_time', 0))
        
    def _analyze_patterns(self, scenario_key: str, result: Dict[str, Any]) -> None:
        """Analyze results for patterns and anomalies"""
        status = result.get('result', {}).get('status')
        
        # Track error patterns
        if status in ['failed', 'error']:
            error = result.get('result', {}).get('error', 'Unknown')
            # Extract key error patterns
            if 'timeout' in error.lower():
                self.error_patterns['timeout'] += 1
            elif 'connection' in error.lower():
                self.error_patterns['connection'] += 1
            elif 'assert' in error.lower():
                self.error_patterns['assertion'] += 1
            elif 'dynamodb' in error.lower():
                self.error_patterns['dynamodb'] += 1
            else:
                self.error_patterns['other'] += 1
                
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of aggregated results"""
        if not self.results:
            return {'error': 'No results to aggregate'}
            
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.get('result', {}).get('status') == 'passed')
        failed = sum(1 for r in self.results if r.get('result', {}).get('status') == 'failed')
        errors = sum(1 for r in self.results if r.get('result', {}).get('status') not in ['passed', 'failed'])
        
        execution_times = [r.get('execution_time', 0) for r in self.results if r.get('execution_time')]
        
        return {
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'pass_rate': (passed / total_tests * 100) if total_tests > 0 else 0,
            'execution_times': {
                'mean': statistics.mean(execution_times) if execution_times else 0,
                'median': statistics.median(execution_times) if execution_times else 0,
                'stdev': statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                'min': min(execution_times) if execution_times else 0,
                'max': max(execution_times) if execution_times else 0,
            },
            'unique_scenarios': len(self.scenario_stats),
            'flaky_tests_count': len(self.flaky_tests),
            'error_patterns': dict(self.error_patterns),
        }
        
    def get_scenario_analysis(self) -> List[Dict[str, Any]]:
        """Get detailed analysis for each scenario"""
        analysis = []
        
        for scenario_key, stats in self.scenario_stats.items():
            if stats['total_runs'] == 0:
                continue
                
            pass_rate = (stats['passed'] / stats['total_runs'] * 100)
            
            scenario_analysis = {
                'scenario': scenario_key,
                'total_runs': stats['total_runs'],
                'passed': stats['passed'],
                'failed': stats['failed'],
                'errors': stats['errors'],
                'timeouts': stats['timeouts'],
                'pass_rate': pass_rate,
                'is_flaky': scenario_key in self.flaky_tests,
                'flaky_score': stats['flaky_score'],
            }
            
            if stats['execution_times']:
                scenario_analysis['execution_times'] = {
                    'mean': statistics.mean(stats['execution_times']),
                    'median': statistics.median(stats['execution_times']),
                    'min': min(stats['execution_times']),
                    'max': max(stats['execution_times']),
                }
                
            # Get most recent failures
            if stats['failure_reasons']:
                recent_failures = stats['failure_reasons'][-3:]  # Last 3 failures
                scenario_analysis['recent_failures'] = recent_failures
                
            analysis.append(scenario_analysis)
            
        # Sort by failure rate (worst first)
        analysis.sort(key=lambda x: x['pass_rate'])
        
        return analysis
        
    def get_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        if not self.time_buckets:
            return {}
            
        trends = {
            'time_buckets': [],
            'degradation_detected': False,
            'performance_regression': None,
        }
        
        sorted_buckets = sorted(self.time_buckets.items())
        
        for timestamp, bucket in sorted_buckets:
            pass_rate = (bucket['passed'] / bucket['total'] * 100) if bucket['total'] > 0 else 0
            avg_time = statistics.mean(bucket['execution_times']) if bucket['execution_times'] else 0
            
            trends['time_buckets'].append({
                'timestamp': timestamp.isoformat(),
                'total': bucket['total'],
                'pass_rate': pass_rate,
                'avg_execution_time': avg_time,
            })
            
        # Detect performance degradation
        if len(trends['time_buckets']) >= 3:
            # Compare first third with last third
            third_size = len(trends['time_buckets']) // 3
            early_buckets = trends['time_buckets'][:third_size]
            late_buckets = trends['time_buckets'][-third_size:]
            
            early_pass_rate = statistics.mean([b['pass_rate'] for b in early_buckets])
            late_pass_rate = statistics.mean([b['pass_rate'] for b in late_buckets])
            
            early_exec_time = statistics.mean([b['avg_execution_time'] for b in early_buckets if b['avg_execution_time'] > 0])
            late_exec_time = statistics.mean([b['avg_execution_time'] for b in late_buckets if b['avg_execution_time'] > 0])
            
            # Check for degradation
            if late_pass_rate < early_pass_rate * 0.9:  # 10% drop in pass rate
                trends['degradation_detected'] = True
                trends['pass_rate_change'] = late_pass_rate - early_pass_rate
                
            if late_exec_time > early_exec_time * 1.5:  # 50% increase in execution time
                trends['performance_regression'] = {
                    'early_avg': early_exec_time,
                    'late_avg': late_exec_time,
                    'increase_percent': ((late_exec_time - early_exec_time) / early_exec_time * 100),
                }
                
        return trends
        
    def identify_flaky_tests(self) -> List[Dict[str, Any]]:
        """Identify and rank flaky tests"""
        flaky_analysis = []
        
        for scenario_key in self.flaky_tests:
            stats = self.scenario_stats[scenario_key]
            
            if stats['total_runs'] < 5:
                continue  # Need sufficient runs to determine flakiness
                
            # Analyze failure pattern
            recent_results = []
            for result in self.results[-20:]:  # Last 20 results
                if f"{result.get('scenario', {}).get('feature')} - {result.get('scenario', {}).get('scenario')}" == scenario_key:
                    recent_results.append(result.get('result', {}).get('status'))
                    
            # Calculate flip-flop rate (status changes)
            flip_flops = 0
            for i in range(1, len(recent_results)):
                if recent_results[i] != recent_results[i-1]:
                    flip_flops += 1
                    
            flip_flop_rate = flip_flops / len(recent_results) if recent_results else 0
            
            flaky_analysis.append({
                'scenario': scenario_key,
                'flaky_score': stats['flaky_score'],
                'flip_flop_rate': flip_flop_rate,
                'total_runs': stats['total_runs'],
                'failure_rate': (stats['failed'] + stats['errors']) / stats['total_runs'],
                'recent_pattern': ''.join(['P' if s == 'passed' else 'F' for s in recent_results[-10:]]),
            })
            
        # Sort by flaky score
        flaky_analysis.sort(key=lambda x: x['flaky_score'], reverse=True)
        
        return flaky_analysis
        
    def get_error_analysis(self) -> Dict[str, Any]:
        """Analyze error patterns and root causes"""
        total_errors = sum(self.error_patterns.values())
        
        if total_errors == 0:
            return {'total_errors': 0, 'patterns': {}}
            
        analysis = {
            'total_errors': total_errors,
            'patterns': {},
            'most_common': None,
            'recommendations': [],
        }
        
        # Calculate percentages
        for pattern, count in self.error_patterns.items():
            analysis['patterns'][pattern] = {
                'count': count,
                'percentage': count / total_errors * 100,
            }
            
        # Find most common error
        if self.error_patterns:
            most_common = self.error_patterns.most_common(1)[0]
            analysis['most_common'] = {
                'type': most_common[0],
                'count': most_common[1],
            }
            
            # Generate recommendations
            if most_common[0] == 'timeout':
                analysis['recommendations'].append("Increase test timeout values or optimize test execution")
            elif most_common[0] == 'connection':
                analysis['recommendations'].append("Check network stability and service availability")
            elif most_common[0] == 'dynamodb':
                analysis['recommendations'].append("Verify DynamoDB mock configuration and table setup")
                
        return analysis
        
    def export_detailed_results(self, output_file: str) -> None:
        """Export detailed results to JSON file
        
        Args:
            output_file: Path to output JSON file
        """
        report = {
            'summary': self.get_summary(),
            'scenario_analysis': self.get_scenario_analysis(),
            'performance_trends': self.get_performance_trends(),
            'flaky_tests': self.identify_flaky_tests(),
            'error_analysis': self.get_error_analysis(),
            'raw_results_count': len(self.results),
            'aggregation_timestamp': datetime.utcnow().isoformat(),
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
            
        logger.info(f"Detailed results exported to {output_file}")
        
    def generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        summary = self.get_summary()
        trends = self.get_performance_trends()
        flaky_tests = self.identify_flaky_tests()
        error_analysis = self.get_error_analysis()
        
        # Pass rate recommendations
        if summary['pass_rate'] < 95:
            recommendations.append(f"Pass rate is {summary['pass_rate']:.1f}%, below 95% threshold. Investigate failing tests.")
            
        # Performance recommendations
        if trends.get('performance_regression'):
            increase = trends['performance_regression']['increase_percent']
            recommendations.append(f"Performance degradation detected: {increase:.1f}% increase in execution time")
            
        # Flaky test recommendations
        if len(flaky_tests) > 0:
            recommendations.append(f"Found {len(flaky_tests)} flaky tests that need stabilization")
            
        # Error pattern recommendations
        if error_analysis.get('most_common'):
            error_type = error_analysis['most_common']['type']
            recommendations.append(f"Most common error type is '{error_type}' - focus debugging efforts here")
            
        # Resource recommendations
        if trends.get('degradation_detected'):
            recommendations.append("System degradation detected over time - check for resource leaks")
            
        return recommendations


if __name__ == "__main__":
    # Test the aggregator
    import random
    
    aggregator = ResultAggregator()
    
    # Generate sample results
    scenarios = [
        {'feature': 'Journey Management', 'scenario': 'Create journey'},
        {'feature': 'Journey Management', 'scenario': 'List journeys'},
        {'feature': 'Stage Management', 'scenario': 'Add stage'},
    ]
    
    for i in range(100):
        scenario = random.choice(scenarios)
        status = random.choices(['passed', 'failed', 'error'], weights=[0.8, 0.15, 0.05])[0]
        
        result = {
            'timestamp': (datetime.utcnow() - timedelta(minutes=30-i/3)).isoformat(),
            'iteration': i,
            'scenario': scenario,
            'result': {'status': status},
            'execution_time': random.uniform(1, 10),
        }
        
        aggregator.add_result(result)
        
    # Print analysis
    print("Summary:", json.dumps(aggregator.get_summary(), indent=2))
    print("\nTop Flaky Tests:", json.dumps(aggregator.identify_flaky_tests()[:3], indent=2))
    print("\nRecommendations:")
    for rec in aggregator.generate_recommendations():
        print(f"  - {rec}")
