"""
LocalStack Report Generator

Generates HTML reports for LocalStack test results.
Extends the base report generator with LocalStack-specific functionality.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .logging_config import get_logger, TestAutomationLogger
from .models import TestType, TestSuiteResult, TestCaseResult, ReportInfo


class LocalStackReportGenerator:
    """Generates HTML reports for LocalStack test results."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory for generated reports
        """
        self.logger = get_logger()
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path("test_reports/localstack")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def generate_integration_report(self, results: TestSuiteResult) -> Path:
        """
        Generate integration test HTML report.
        
        Args:
            results: TestSuiteResult from integration tests
            
        Returns:
            Path to generated report
        """
        TestAutomationLogger.log_step("Generating integration test report...")
        
        report_path = self.output_dir / f"integration_report_{self.timestamp}.html"
        
        html = self._generate_report_html(
            title="Integration Test Report",
            subtitle="LocalStack Integration Tests",
            results=results,
            icon="🧪"
        )
        
        self._write_report(report_path, html)
        TestAutomationLogger.log_success(f"Integration report: {report_path}")
        return report_path
    
    def generate_bdd_report(self, results: TestSuiteResult) -> Path:
        """
        Generate BDD test HTML report.
        
        Args:
            results: TestSuiteResult from BDD tests
            
        Returns:
            Path to generated report
        """
        TestAutomationLogger.log_step("Generating BDD test report...")
        
        report_path = self.output_dir / f"bdd_report_{self.timestamp}.html"
        
        html = self._generate_report_html(
            title="BDD Test Report",
            subtitle="Behavior-Driven Development Tests",
            results=results,
            icon="📋"
        )
        
        self._write_report(report_path, html)
        TestAutomationLogger.log_success(f"BDD report: {report_path}")
        return report_path
    
    def generate_endurance_report(self, results: TestSuiteResult) -> Path:
        """
        Generate endurance test HTML report.
        
        Args:
            results: TestSuiteResult from endurance tests
            
        Returns:
            Path to generated report
        """
        TestAutomationLogger.log_step("Generating endurance test report...")
        
        report_path = self.output_dir / f"endurance_report_{self.timestamp}.html"
        
        html = self._generate_report_html(
            title="Endurance Test Report",
            subtitle="Long-Running Stability Tests",
            results=results,
            icon="⏱️"
        )
        
        self._write_report(report_path, html)
        TestAutomationLogger.log_success(f"Endurance report: {report_path}")
        return report_path

    def generate_index(self, reports: List[ReportInfo]) -> Path:
        """
        Generate index page linking all reports.
        
        Args:
            reports: List of ReportInfo for generated reports
            
        Returns:
            Path to generated index page
        """
        TestAutomationLogger.log_step("Generating index page...")
        
        index_path = self.output_dir / f"index_{self.timestamp}.html"
        
        # Build report cards
        report_cards = []
        for report in reports:
            status_class = "passed" if report.failed_tests == 0 else "failed"
            report_cards.append(f'''
            <div class="report-card {status_class}">
                <h3>{report.test_type.value.title()} Tests</h3>
                <div class="stats">
                    <span class="total">Total: {report.total_tests}</span>
                    <span class="passed">Passed: {report.passed_tests}</span>
                    <span class="failed">Failed: {report.failed_tests}</span>
                </div>
                <div class="pass-rate">Pass Rate: {report.pass_rate:.1f}%</div>
                <a href="{report.local_path.name}" class="view-btn">View Report</a>
                {f'<a href="{report.s3_url}" class="s3-btn">S3 Link</a>' if report.s3_url else ''}
            </div>
            ''')
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LocalStack Test Reports - {self.timestamp}</title>
    {self._get_index_css()}
</head>
<body>
    <header>
        <h1>📊 LocalStack Test Reports</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </header>
    <main>
        <div class="reports-grid">
            {''.join(report_cards)}
        </div>
    </main>
    <footer>
        <p>LocalStack Test Automation Framework</p>
    </footer>
</body>
</html>'''
        
        self._write_report(index_path, html)
        TestAutomationLogger.log_success(f"Index page: {index_path}")
        return index_path

    def _generate_report_html(
        self,
        title: str,
        subtitle: str,
        results: TestSuiteResult,
        icon: str = "📊"
    ) -> str:
        """Generate complete HTML report."""
        
        # Determine overall status
        overall_status = "passed" if results.failed == 0 and results.errors == 0 else "failed"
        status_icon = "✅" if overall_status == "passed" else "❌"
        
        # Generate test case rows
        test_rows = self._generate_test_rows(results.test_cases)
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
    {self._get_report_css()}
</head>
<body>
    <header class="report-header">
        <div class="container">
            <div class="header-content">
                <div class="title-section">
                    <h1>{icon} {title}</h1>
                    <p class="subtitle">{subtitle}</p>
                </div>
                <div class="meta-info">
                    <div class="meta-item">
                        <span class="label">Generated</span>
                        <span class="value">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
                    <div class="meta-item">
                        <span class="label">Duration</span>
                        <span class="value">{self._format_duration(results.duration)}</span>
                    </div>
                    <div class="meta-item">
                        <span class="label">Status</span>
                        <span class="value">{status_icon} {overall_status.upper()}</span>
                    </div>
                </div>
            </div>
        </div>
    </header>
    
    <main class="container">
        <section class="summary">
            <h2>Summary</h2>
            <div class="summary-cards">
                <div class="card total"><div class="value">{results.total}</div><div class="label">Total</div></div>
                <div class="card passed"><div class="value">{results.passed}</div><div class="label">Passed</div></div>
                <div class="card failed"><div class="value">{results.failed}</div><div class="label">Failed</div></div>
                <div class="card skipped"><div class="value">{results.skipped}</div><div class="label">Skipped</div></div>
                <div class="card errors"><div class="value">{results.errors}</div><div class="label">Errors</div></div>
            </div>
            <div class="chart-container">
                <canvas id="resultsChart"></canvas>
            </div>
        </section>
        
        <section class="details">
            <h2>Test Details</h2>
            <div class="controls">
                <input type="text" id="searchBox" placeholder="Search tests..." onkeyup="filterTests()">
                <select id="statusFilter" onchange="filterByStatus()">
                    <option value="all">All Status</option>
                    <option value="passed">Passed</option>
                    <option value="failed">Failed</option>
                    <option value="skipped">Skipped</option>
                    <option value="error">Error</option>
                </select>
                <button onclick="expandAllFailed()">Expand Failed</button>
            </div>
            <div class="test-list">
                {test_rows}
            </div>
        </section>
    </main>
    
    <footer>
        <p>LocalStack Test Automation Framework</p>
        <p>Test Type: {results.test_type.value} | Pass Rate: {results.pass_rate:.1f}%</p>
    </footer>
    
    {self._get_chart_script(results)}
    {self._get_filter_script()}
</body>
</html>'''

    def _generate_test_rows(self, test_cases: List[TestCaseResult]) -> str:
        """Generate HTML rows for test cases."""
        rows = []
        for i, tc in enumerate(test_cases):
            status_class = tc.status.lower()
            status_icon = self._get_status_icon(tc.status)
            
            error_section = ""
            if tc.error_message or tc.stack_trace:
                error_section = f'''
                <div class="error-details">
                    <div class="error-header">Error Details</div>
                    <pre class="error-message">{self._escape_html(tc.error_message or '')}</pre>
                    {f'<pre class="stack-trace">{self._escape_html(tc.stack_trace)}</pre>' if tc.stack_trace else ''}
                </div>
                '''
            
            rows.append(f'''
            <div class="test-item {status_class}" id="test-{i}" data-status="{status_class}">
                <div class="test-header" onclick="toggleTest({i})">
                    <span class="status-icon">{status_icon}</span>
                    <span class="test-name">{self._escape_html(tc.name)}</span>
                    <span class="test-duration">{tc.duration:.3f}s</span>
                    <span class="expand-icon">▶</span>
                </div>
                <div class="test-body" id="test-body-{i}">
                    <div class="test-info">
                        <p><strong>Status:</strong> {tc.status}</p>
                        <p><strong>Duration:</strong> {tc.duration:.3f}s</p>
                    </div>
                    {error_section}
                    {f'<div class="test-output"><pre>{self._escape_html(tc.output)}</pre></div>' if tc.output else ''}
                </div>
            </div>
            ''')
        
        return ''.join(rows)
    
    def _get_status_icon(self, status: str) -> str:
        """Get icon for test status."""
        icons = {
            'passed': '✓',
            'failed': '✗',
            'error': '⚠',
            'skipped': '○'
        }
        return icons.get(status.lower(), '?')
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ''
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))
    
    def _write_report(self, path: Path, content: str) -> None:
        """Write report content to file."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            TestAutomationLogger.log_error(f"Failed to write report: {e}")
            raise

    def _get_report_css(self) -> str:
        """Get CSS styles for report."""
        return '''<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
    --success: #10b981; --fail: #ef4444; --error: #f59e0b;
    --skip: #9ca3af; --primary: #667eea; --bg-light: #f9fafb;
}
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg-light); }
.container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.report-header { background: linear-gradient(135deg, var(--primary), #764ba2); color: white; padding: 30px 0; }
.header-content { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }
.title-section h1 { font-size: 28px; margin-bottom: 5px; }
.subtitle { opacity: 0.9; }
.meta-info { display: flex; gap: 20px; }
.meta-item { display: flex; flex-direction: column; }
.meta-item .label { font-size: 12px; opacity: 0.8; text-transform: uppercase; }
.meta-item .value { font-size: 16px; font-weight: 600; }
section { padding: 30px 0; }
h2 { font-size: 22px; margin-bottom: 20px; }
.summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 30px; }
.card { background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.card .value { font-size: 32px; font-weight: 700; }
.card .label { font-size: 12px; color: #666; text-transform: uppercase; }
.card.passed .value { color: var(--success); }
.card.failed .value { color: var(--fail); }
.card.errors .value { color: var(--error); }
.card.skipped .value { color: var(--skip); }
.chart-container { background: white; padding: 20px; border-radius: 10px; max-width: 400px; margin: 0 auto; }
.controls { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
.controls input, .controls select, .controls button { padding: 10px 15px; border: 1px solid #ddd; border-radius: 5px; }
.controls input { flex: 1; min-width: 200px; }
.controls button { background: var(--primary); color: white; border: none; cursor: pointer; }
.test-list { display: flex; flex-direction: column; gap: 10px; }
.test-item { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.test-item.passed { border-left: 4px solid var(--success); }
.test-item.failed { border-left: 4px solid var(--fail); }
.test-item.error { border-left: 4px solid var(--error); }
.test-item.skipped { border-left: 4px solid var(--skip); }
.test-header { padding: 15px; display: flex; align-items: center; gap: 10px; cursor: pointer; }
.test-header:hover { background: #f5f5f5; }
.status-icon { font-size: 18px; }
.test-item.passed .status-icon { color: var(--success); }
.test-item.failed .status-icon { color: var(--fail); }
.test-item.error .status-icon { color: var(--error); }
.test-name { flex: 1; font-weight: 500; word-break: break-all; }
.test-duration { color: #666; font-size: 14px; }
.expand-icon { color: #999; transition: transform 0.2s; }
.test-item.expanded .expand-icon { transform: rotate(90deg); }
.test-body { display: none; padding: 15px; border-top: 1px solid #eee; background: #fafafa; }
.test-item.expanded .test-body { display: block; }
.error-details { margin-top: 10px; background: #fff5f5; padding: 10px; border-radius: 5px; border-left: 3px solid var(--fail); }
.error-header { font-weight: 600; color: var(--fail); margin-bottom: 5px; }
.error-message, .stack-trace { font-family: monospace; font-size: 13px; white-space: pre-wrap; overflow-x: auto; }
footer { background: #333; color: white; padding: 20px; text-align: center; margin-top: 40px; }
footer p { margin: 5px 0; opacity: 0.8; }
</style>'''

    def _get_index_css(self) -> str:
        """Get CSS styles for index page."""
        return '''<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; min-height: 100vh; }
header { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 40px 20px; text-align: center; }
header h1 { font-size: 32px; margin-bottom: 10px; }
main { max-width: 1000px; margin: 0 auto; padding: 40px 20px; }
.reports-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
.report-card { background: white; border-radius: 12px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.report-card.passed { border-top: 4px solid #10b981; }
.report-card.failed { border-top: 4px solid #ef4444; }
.report-card h3 { font-size: 20px; margin-bottom: 15px; }
.stats { display: flex; gap: 15px; margin-bottom: 10px; font-size: 14px; }
.stats .passed { color: #10b981; }
.stats .failed { color: #ef4444; }
.pass-rate { font-size: 18px; font-weight: 600; color: #667eea; margin-bottom: 15px; }
.view-btn, .s3-btn { display: inline-block; padding: 8px 16px; border-radius: 5px; text-decoration: none; font-size: 14px; margin-right: 10px; }
.view-btn { background: #667eea; color: white; }
.s3-btn { background: #f59e0b; color: white; }
footer { text-align: center; padding: 20px; color: #666; }
</style>'''
    
    def _get_chart_script(self, results: TestSuiteResult) -> str:
        """Get Chart.js initialization script."""
        return f'''<script>
document.addEventListener('DOMContentLoaded', function() {{
    const ctx = document.getElementById('resultsChart');
    if (ctx) {{
        new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: ['Passed', 'Failed', 'Skipped', 'Errors'],
                datasets: [{{
                    data: [{results.passed}, {results.failed}, {results.skipped}, {results.errors}],
                    backgroundColor: ['#10b981', '#ef4444', '#9ca3af', '#f59e0b']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ legend: {{ position: 'bottom' }} }}
            }}
        }});
    }}
}});
</script>'''
    
    def _get_filter_script(self) -> str:
        """Get JavaScript for filtering and expanding tests."""
        return '''<script>
function toggleTest(id) {
    const item = document.getElementById('test-' + id);
    item.classList.toggle('expanded');
}
function filterTests() {
    const search = document.getElementById('searchBox').value.toLowerCase();
    document.querySelectorAll('.test-item').forEach(item => {
        const name = item.querySelector('.test-name').textContent.toLowerCase();
        item.style.display = name.includes(search) ? 'block' : 'none';
    });
}
function filterByStatus() {
    const status = document.getElementById('statusFilter').value;
    document.querySelectorAll('.test-item').forEach(item => {
        if (status === 'all' || item.dataset.status === status) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}
function expandAllFailed() {
    document.querySelectorAll('.test-item.failed, .test-item.error').forEach(item => {
        item.classList.add('expanded');
    });
}
</script>'''
