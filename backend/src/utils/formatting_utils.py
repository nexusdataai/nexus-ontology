# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Formatting utility functions for TMF ODA Transformer."""

import re
from typing import Dict, Any, List


def sanitize_connection_string(connection_string: str) -> str:
    """Remove sensitive information from connection string."""
    # Remove password from connection string for security
    sanitized = re.sub(r'password=[^;]*', 'password=***', connection_string, flags=re.IGNORECASE)
    sanitized = re.sub(r':[^@]*@', ':***@', sanitized)
    return sanitized


def format_analysis_report(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format analysis report for display."""
    formatted = {
        'summary': report_data.get('summary', {}),
        'details': report_data.get('details', {}),
        'recommendations': report_data.get('recommendations', []),
        'total_files': report_data.get('total_files_found', 0),
        'analyzed_files': report_data.get('total_files_analyzed', 0),
        'compliance_score': report_data.get('summary', {}).get('average_compliance_score', 0),
        'duration': report_data.get('analysis_duration', 0)
    }
    
    return formatted


def format_test_results(test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format test results for display."""
    total_tests = len(test_results)
    passed_tests = sum(1 for test in test_results if test.get('passed', False))
    failed_tests = total_tests - passed_tests
    
    formatted = {
        'summary': {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 1)
        },
        'details': test_results,
        'status': 'success' if failed_tests == 0 else 'partial_success' if passed_tests > failed_tests else 'failure'
    }
    
    return formatted


def format_journey_summary(journey_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format journey data for summary display."""
    formatted = {
        'journey_id': journey_data.get('journey_id', 'N/A'),
        'name': journey_data.get('name', 'Unnamed Journey'),
        'status': journey_data.get('status', 'unknown'),
        'progress': journey_data.get('overall_progress') or journey_data.get('overallProgress', 0),
        'current_stage': journey_data.get('current_stage') or journey_data.get('currentStageId', 'N/A'),
        'created_at': journey_data.get('created_at') or journey_data.get('createdAt', 'N/A'),
        'oda_component_type': journey_data.get('oda_component_type', 'N/A')
    }
    
    return formatted


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_compliance_score(score: float) -> str:
    """Format compliance score with color indicator."""
    if score >= 90:
        return f"🟢 {score:.1f}% (Excellent)"
    elif score >= 75:
        return f"🟡 {score:.1f}% (Good)"
    elif score >= 50:
        return f"🟠 {score:.1f}% (Needs Improvement)"
    else:
        return f"🔴 {score:.1f}% (Poor)"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_table_row(data: List[str], widths: List[int]) -> str:
    """Format a table row with proper column widths."""
    formatted_columns = []
    for i, (item, width) in enumerate(zip(data, widths)):
        formatted_columns.append(item.ljust(width))
    return " | ".join(formatted_columns)


def create_status_emoji(status: str) -> str:
    """Get appropriate emoji for status."""
    status_emojis = {
        'completed': '✅',
        'running': '🏃',
        'pending': '⏳',
        'failed': '❌',
        'cancelled': '⚠️',
        'success': '🎉',
        'error': '💥',
        'warning': '⚠️',
        'info': 'ℹ️'
    }
    return status_emojis.get(status.lower(), '❓') 