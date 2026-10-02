#!/usr/bin/env python3
"""
Endurance Test Report Generator
Creates comprehensive HTML and JSON reports for endurance test results
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class EnduranceReportGenerator:
    """Generates comprehensive reports for BDD endurance testing"""
    
    def __init__(self, result_aggregator, health_monitor=None):
        """Initialize report generator
        
        Args:
            result_aggregator: ResultAggregator instance with test results
            health_monitor: Optional ServerHealthMonitor instance
        """
        self.aggregator = result_aggregator
        self.health_monitor = health_monitor
        self.timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
    def generate_all_reports(self, output_dir: str) -> Dict[str, str]:
        """Generate all report formats
        
        Args:
            output_dir: Directory to save reports
            
        Returns:
            Dictionary of report types and their file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        reports = {}
        
        # Generate JSON report
        json_file = output_path / f'endurance_report_{self.timestamp}.json'
        self.generate_json_report(str(json_file))
        reports['json'] = str(json_file)
        
        # Generate HTML report
        html_file = output_path / f'endurance_report_{self.timestamp}.html'
        self.generate_html_report(str(html_file))
        reports['html'] = str(html_file)
        
        # Generate health metrics if available
        if self.health_monitor:
            metrics_file = output_path / f'health_metrics_{self.timestamp}.json'
            self.health_monitor.export_metrics(str(metrics_file))
            reports['health_metrics'] = str(metrics_file)
            
        logger.info(f"Generated {len(reports)} reports in {output_dir}")
        return reports
        
    def generate_json_report(self, output_file: str) -> None:
        """Generate comprehensive JSON report
        
        Args:
            output_file: Path to output JSON file
        """
        report = self._build_report_data()
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
            
        logger.info(f"JSON report saved to {output_file}")
        
    def generate_html_report(self, output_file: str) -> None:
        """Generate interactive HTML report
        
        Args:
            output_file: Path to output HTML file
        """
        report_data = self._build_report_data()
        html_content = self._generate_html_content(report_data)
        
        with open(output_file, 'w') as f:
            f.write(html_content)
            
        logger.info(f"HTML report saved to {output_file}")
        
    def _build_report_data(self) -> Dict[str, Any]:
        """Build comprehensive report data structure"""
        report = {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'report_version': '1.0.0',
            },
            'summary': self.aggregator.get_summary(),
            'scenario_analysis': self.aggregator.get_scenario_analysis(),
            'performance_trends': self.aggregator.get_performance_trends(),
            'flaky_tests': self.aggregator.identify_flaky_tests(),
            'error_analysis': self.aggregator.get_error_analysis(),
            'recommendations': self.aggregator.generate_recommendations(),
        }
        
        # Add health metrics if available
        if self.health_monitor:
            report['health'] = {
                'is_healthy': self.health_monitor.is_healthy(),
                'summary': self.health_monitor.get_summary_stats(),
                'alerts': self.health_monitor.alerts,
            }
            
        return report
        
    def _generate_html_content(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML report content"""
        summary = report_data['summary']
        health = report_data.get('health', {})
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BDD Endurance Test Report - {self.timestamp}</title>
    <style>
        {self._get_css_styles()}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏃 BDD Endurance Test Report</h1>
            <div class="timestamp">Generated: {report_data['metadata']['generated_at']}</div>
        </header>
        
        {self._generate_summary_section(summary, health)}
        {self._generate_health_section(health)}
        {self._generate_performance_section(report_data['performance_trends'])}
        {self._generate_scenario_section(report_data['scenario_analysis'])}
        {self._generate_flaky_section(report_data['flaky_tests'])}
        {self._generate_error_section(report_data['error_analysis'])}
        {self._generate_recommendations_section(report_data['recommendations'])}
        
        <footer>
            <p>© 2024 Journey Manager Endurance Testing Suite</p>
        </footer>
    </div>
    
    <script>
        {self._get_javascript_code(report_data)}
    </script>
</body>
</html>
"""
        return html
        
    def _get_css_styles(self) -> str:
        """Get CSS styles for HTML report"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .timestamp {
            opacity: 0.9;
            font-size: 0.9em;
        }
        
        .section {
            padding: 40px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .section:last-child {
            border-bottom: none;
        }
        
        h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.8em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .status-passed {
            background: #4caf50;
            color: white;
        }
        
        .status-failed {
            background: #f44336;
            color: white;
        }
        
        .status-warning {
            background: #ff9800;
            color: white;
        }
        
        .status-info {
            background: #2196f3;
            color: white;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        th {
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
        }
        
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        tr:hover {
            background: #f9f9f9;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin: 30px 0;
        }
        
        .recommendations {
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 20px;
            margin-top: 20px;
        }
        
        .recommendations ul {
            list-style-type: none;
            padding: 0;
        }
        
        .recommendations li {
            margin-bottom: 10px;
            padding-left: 25px;
            position: relative;
        }
        
        .recommendations li:before {
            content: "⚠️";
            position: absolute;
            left: 0;
        }
        
        .alert {
            background: #ffebee;
            border-left: 4px solid #f44336;
            padding: 15px;
            margin: 10px 0;
        }
        
        .success {
            background: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin: 10px 0;
        }
        
        footer {
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            color: #666;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4caf50, #8bc34a);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.3s ease;
        }
        
        .flaky-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .flaky-high { background: #f44336; }
        .flaky-medium { background: #ff9800; }
        .flaky-low { background: #ffc107; }
        """
        
    def _generate_summary_section(self, summary: Dict[str, Any], health: Dict[str, Any]) -> str:
        """Generate summary section HTML"""
        pass_rate = summary.get('pass_rate', 0)
        health_status = "HEALTHY" if health.get('is_healthy', True) else "DEGRADED"
        health_class = "passed" if health.get('is_healthy', True) else "failed"
        
        return f"""
        <section class="section">
            <h2>📊 Test Summary</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_tests', 0)}</div>
                    <div class="metric-label">Total Tests</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{pass_rate:.1f}%</div>
                    <div class="metric-label">Pass Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('passed', 0)}</div>
                    <div class="metric-label">Passed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('failed', 0)}</div>
                    <div class="metric-label">Failed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('errors', 0)}</div>
                    <div class="metric-label">Errors</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        <span class="status-badge status-{health_class}">{health_status}</span>
                    </div>
                    <div class="metric-label">System Health</div>
                </div>
            </div>
            
            <div class="progress-bar">
                <div class="progress-fill" style="width: {pass_rate}%">
                    {pass_rate:.1f}% Pass Rate
                </div>
            </div>
        </section>
        """
        
    def _generate_health_section(self, health: Dict[str, Any]) -> str:
        """Generate health metrics section HTML"""
        if not health:
            return ""
            
        summary = health.get('summary', {})
        alerts = health.get('alerts', [])
        
        alerts_html = ""
        if alerts:
            alerts_html = "<h3>⚠️ Health Alerts</h3><div>"
            for alert in alerts[:5]:  # Show first 5 alerts
                alerts_html += f"""
                <div class="alert">
                    <strong>{alert.get('type', 'UNKNOWN')}</strong>: {alert.get('message', '')}
                    <br><small>{alert.get('timestamp', '')}</small>
                </div>
                """
            alerts_html += "</div>"
            
        cpu_stats = summary.get('cpu', {})
        memory_stats = summary.get('memory_gb', {})
        
        return f"""
        <section class="section">
            <h2>💓 System Health</h2>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{cpu_stats.get('mean', 0):.1f}%</div>
                    <div class="metric-label">Average CPU</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{cpu_stats.get('max', 0):.1f}%</div>
                    <div class="metric-label">Peak CPU</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{memory_stats.get('mean', 0):.2f} GB</div>
                    <div class="metric-label">Average Memory</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{memory_stats.get('max', 0):.2f} GB</div>
                    <div class="metric-label">Peak Memory</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{memory_stats.get('growth', 0):.2f} GB</div>
                    <div class="metric-label">Memory Growth</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{len(alerts)}</div>
                    <div class="metric-label">Total Alerts</div>
                </div>
            </div>
            
            {alerts_html}
            
            <div class="chart-container">
                <canvas id="healthChart"></canvas>
            </div>
        </section>
        """
        
    def _generate_performance_section(self, trends: Dict[str, Any]) -> str:
        """Generate performance trends section HTML"""
        degradation = trends.get('degradation_detected', False)
        regression = trends.get('performance_regression')
        
        status_html = ""
        if degradation:
            status_html = '<div class="alert">⚠️ Performance degradation detected over time</div>'
        else:
            status_html = '<div class="success">✓ Performance remained stable throughout the test</div>'
            
        regression_html = ""
        if regression:
            increase = regression.get('increase_percent', 0)
            regression_html = f"""
            <div class="alert">
                <strong>Performance Regression Detected:</strong><br>
                Execution time increased by {increase:.1f}% from early to late stages<br>
                Early average: {regression.get('early_avg', 0):.2f}s → 
                Late average: {regression.get('late_avg', 0):.2f}s
            </div>
            """
            
        return f"""
        <section class="section">
            <h2>📈 Performance Trends</h2>
            {status_html}
            {regression_html}
            
            <div class="chart-container">
                <canvas id="performanceChart"></canvas>
            </div>
        </section>
        """
        
    def _generate_scenario_section(self, scenarios: List[Dict[str, Any]]) -> str:
        """Generate scenario analysis section HTML"""
        if not scenarios:
            return ""
            
        rows = ""
        for scenario in scenarios[:20]:  # Show top 20 scenarios
            pass_rate = scenario.get('pass_rate', 0)
            status_class = "passed" if pass_rate >= 95 else "warning" if pass_rate >= 80 else "failed"
            flaky_badge = '<span class="status-badge status-warning">FLAKY</span>' if scenario.get('is_flaky') else ''
            
            rows += f"""
            <tr>
                <td>{scenario.get('scenario', 'Unknown')}</td>
                <td>{scenario.get('total_runs', 0)}</td>
                <td>{scenario.get('passed', 0)}</td>
                <td>{scenario.get('failed', 0)}</td>
                <td>{scenario.get('errors', 0)}</td>
                <td><span class="status-badge status-{status_class}">{pass_rate:.1f}%</span></td>
                <td>{flaky_badge}</td>
            </tr>
            """
            
        return f"""
        <section class="section">
            <h2>🎯 Scenario Analysis</h2>
            <table>
                <thead>
                    <tr>
                        <th>Scenario</th>
                        <th>Runs</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Errors</th>
                        <th>Pass Rate</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </section>
        """
        
    def _generate_flaky_section(self, flaky_tests: List[Dict[str, Any]]) -> str:
        """Generate flaky tests section HTML"""
        if not flaky_tests:
            return """
            <section class="section">
                <h2>🎲 Flaky Tests</h2>
                <div class="success">✓ No flaky tests detected</div>
            </section>
            """
            
        rows = ""
        for test in flaky_tests[:10]:  # Show top 10 flaky tests
            score = test.get('flaky_score', 0)
            indicator_class = "high" if score > 0.7 else "medium" if score > 0.4 else "low"
            pattern = test.get('recent_pattern', '')
            
            rows += f"""
            <tr>
                <td><span class="flaky-indicator flaky-{indicator_class}"></span> {test.get('scenario', 'Unknown')}</td>
                <td>{score:.2f}</td>
                <td>{test.get('flip_flop_rate', 0):.2f}</td>
                <td><code>{pattern}</code></td>
                <td>{test.get('failure_rate', 0)*100:.1f}%</td>
            </tr>
            """
            
        return f"""
        <section class="section">
            <h2>🎲 Flaky Tests</h2>
            <div class="alert">Found {len(flaky_tests)} flaky tests that need attention</div>
            <table>
                <thead>
                    <tr>
                        <th>Scenario</th>
                        <th>Flaky Score</th>
                        <th>Flip-Flop Rate</th>
                        <th>Recent Pattern</th>
                        <th>Failure Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            <p><small>Pattern: P = Passed, F = Failed</small></p>
        </section>
        """
        
    def _generate_error_section(self, error_analysis: Dict[str, Any]) -> str:
        """Generate error analysis section HTML"""
        if not error_analysis.get('total_errors'):
            return """
            <section class="section">
                <h2>🐛 Error Analysis</h2>
                <div class="success">✓ No errors detected during testing</div>
            </section>
            """
            
        patterns = error_analysis.get('patterns', {})
        rows = ""
        for pattern_type, data in patterns.items():
            rows += f"""
            <tr>
                <td>{pattern_type.capitalize()}</td>
                <td>{data.get('count', 0)}</td>
                <td>{data.get('percentage', 0):.1f}%</td>
            </tr>
            """
            
        return f"""
        <section class="section">
            <h2>🐛 Error Analysis</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{error_analysis.get('total_errors', 0)}</div>
                    <div class="metric-label">Total Errors</div>
                </div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Error Type</th>
                        <th>Count</th>
                        <th>Percentage</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </section>
        """
        
    def _generate_recommendations_section(self, recommendations: List[str]) -> str:
        """Generate recommendations section HTML"""
        if not recommendations:
            return """
            <section class="section">
                <h2>💡 Recommendations</h2>
                <div class="success">✓ No critical issues found. System performing optimally.</div>
            </section>
            """
            
        rec_items = "".join([f"<li>{rec}</li>" for rec in recommendations])
        
        return f"""
        <section class="section">
            <h2>💡 Recommendations</h2>
            <div class="recommendations">
                <ul>
                    {rec_items}
                </ul>
            </div>
        </section>
        """
        
    def _get_javascript_code(self, report_data: Dict[str, Any]) -> str:
        """Generate JavaScript code for charts"""
        trends = report_data.get('performance_trends', {})
        buckets = trends.get('time_buckets', [])
        
        # Prepare data for charts
        labels = [b['timestamp'][-8:-3] for b in buckets]  # Extract time HH:MM
        pass_rates = [b.get('pass_rate', 0) for b in buckets]
        exec_times = [b.get('avg_execution_time', 0) for b in buckets]
        
        return f"""
        // Performance Chart
        const perfCtx = document.getElementById('performanceChart');
        if (perfCtx) {{
            new Chart(perfCtx.getContext('2d'), {{
                type: 'line',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: 'Pass Rate (%)',
                        data: {json.dumps(pass_rates)},
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        yAxisID: 'y',
                    }}, {{
                        label: 'Avg Execution Time (s)',
                        data: {json.dumps(exec_times)},
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        yAxisID: 'y1',
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{
                        mode: 'index',
                        intersect: false,
                    }},
                    scales: {{
                        y: {{
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {{
                                display: true,
                                text: 'Pass Rate (%)'
                            }}
                        }},
                        y1: {{
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {{
                                display: true,
                                text: 'Execution Time (s)'
                            }},
                            grid: {{
                                drawOnChartArea: false,
                            }},
                        }},
                    }},
                }}
            }});
        }}
        
        // Health Chart (placeholder for future implementation)
        const healthCtx = document.getElementById('healthChart');
        if (healthCtx) {{
            // Add health metrics visualization here
        }}
        """


if __name__ == "__main__":
    # Test the report generator
    from result_aggregator import ResultAggregator
    from server_health_monitor import ServerHealthMonitor
    import time
    
    # Create sample data
    aggregator = ResultAggregator()
    monitor = ServerHealthMonitor()
    
    # Add some sample results
    for i in range(50):
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'iteration': i,
            'scenario': {'feature': 'Test', 'scenario': f'Scenario {i%5}'},
            'result': {'status': 'passed' if i % 3 != 0 else 'failed'},
            'execution_time': 2.5 + (i % 10) * 0.3,
        }
        aggregator.add_result(result)
        
    # Generate reports
    generator = EnduranceReportGenerator(aggregator, monitor)
    reports = generator.generate_all_reports('test_reports/endurance')
    
    print("Generated reports:")
    for report_type, path in reports.items():
        print(f"  - {report_type}: {path}")
