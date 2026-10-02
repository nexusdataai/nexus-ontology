#!/usr/bin/env python3
"""
Enhanced BDD HTML Report Generator (Backward Compatibility Wrapper)

DEPRECATED: This module is now a wrapper for backward compatibility.
New code should use: tests.report_generators.bdd_report_generator.BDDReportGenerator

Creates professional, visually appealing BDD test reports with:
- Visual charts (pie/bar charts)
- Expandable features and scenarios
- Step-by-step execution details
- Modern, responsive UI
"""

import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from new location
from report_generators.bdd_report_generator import BDDReportGenerator

# Re-export with legacy name for backward compatibility
EnhancedBDDReportGenerator = BDDReportGenerator


def main():
    """Main CLI entry point - delegates to new implementation"""
    parser = argparse.ArgumentParser(description='Generate enhanced BDD HTML report')
    parser.add_argument('--input', required=True, help='Input behave JSON file')
    parser.add_argument('--output', required=True, help='Output HTML file path')
    parser.add_argument('--title', default='BDD Test Report', help='Report title')
    
    args = parser.parse_args()
    
    generator = EnhancedBDDReportGenerator(
        behave_json_path=args.input,
        output_html_path=args.output,
        title=args.title
    )
    
    success = generator.generate_report()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
