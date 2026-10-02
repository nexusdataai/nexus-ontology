# Enhanced BDD Reports

## Overview

The AI Job Engine now features **professional, interactive BDD test reports** with visual charts, expandable features/scenarios, and step-by-step execution details.

**Enhanced Report URL**: http://127.0.0.1:5500/bdd/index.html

## Features

### 1. Visual Charts

- **Pie Chart**: Status distribution (Passed/Failed/Error/Skipped)
- **Bar Chart**: Feature comparison showing pass/fail by feature
- **Interactive**: Hover for details, click for drill-down

### 2. Expandable Organization

- **Feature Cards**: Click to expand/collapse
- **Scenario Cards**: Nested within features, expandable
- **Step Details**: Complete execution trace with timing

### 3. Summary Dashboard

- **4 Metric Cards**: Total, Passed, Failed, Error scenarios
- **Statistics Table**: Detailed metrics including duration stats
- **Color Coding**: Green (passed), Red (failed), Orange (error)

### 4. Navigation

- **Overview Tab**: Summary, charts, statistics
- **Features Tab**: All features with scenarios
- **Requirements Tab**: Scenarios grouped by tags

### 5. Interactive Controls

- **Search**: Search across all scenarios
- **Filter by Status**: Show only passed/failed/error scenarios
- **Expand/Collapse**: Expand all, collapse all, expand failed
- **Quick Links**: Jump to specific scenarios

### 6. Step-by-Step Details

Each scenario shows:
- Step keyword (Given/When/Then)
- Step text
- Status icon (✓/✗/?)
- Execution duration
- Step location (file:line)
- Error messages for failures
- Data tables (if present)

---

## Report Structure

### Header Section

- Report title with icon
- Generation timestamp
- Total duration
- Overall status (✅/❌)
- Navigation tabs

### Overview Tab

- **Summary Cards**: 4 cards showing key metrics
- **Pie Chart**: Visual status distribution
- **Bar Chart**: Feature comparison
- **Statistics Table**: Detailed metrics

### Features Tab

- **Feature Cards**: One per feature
  - Feature name and tags
  - Pass rate and scenario count
  - Status indicator
  - Expandable to show scenarios

- **Scenario Cards**: Nested within features
  - Scenario name and tags
  - Duration
  - Status badge
  - Expandable to show steps

- **Steps List**: Within scenarios
  - Numbered steps (1, 2, 3...)
  - Keyword + text
  - Status icon and color coding
  - Duration per step
  - Error messages if failed

### Requirements Tab

- Scenarios grouped by tags
- Coverage per tag
- Links to scenarios

---

## Generating Reports

### Automatic Generation

Enhanced reports are automatically generated when running BDD tests:

```bash
# From project root
cd /opt/mycode/ptr/ai-job-engine/tests
./run_tests.sh bdd

# Or from tests/bdd
cd /opt/mycode/ptr/ai-job-engine/tests/bdd
./run_bdd_tests.sh
```

### Manual Generation

Generate report from existing behave JSON:

```bash
cd /opt/mycode/ptr/ai-job-engine

python3 tests/bdd/enhanced_report_generator.py \
    --input test_reports/bdd/bdd_test_raw_TIMESTAMP_pretty.json \
    --output test_reports/bdd/bdd_report_enhanced_TIMESTAMP.html \
    --title "BDD Test Report"
```

---

## Viewing Reports

### Enhanced Report (Recommended)

```bash
# Via HTTP server
http://127.0.0.1:5500/bdd/index.html

# Or direct file access
open /opt/mycode/ptr/ai-job-engine/test_reports/bdd/index.html
```

### From Unified Dashboard

```bash
# Open unified dashboard
http://127.0.0.1:5500/test_reports.html

# Click on "📝 BDD Tests" card
# Or click "View HTML Report →" link
```

---

## Report Comparison

### Old Basic Report

- Plain HTML listing
- No charts
- No expandable sections
- Limited formatting

### New Enhanced Report

- ✅ Professional UI with charts
- ✅ Expandable features/scenarios
- ✅ Step-by-step execution details
- ✅ Search and filter
- ✅ Visual status indicators
- ✅ Timing information
- ✅ Error messages highlighted
- ✅ Responsive design
- ✅ Print-friendly

---

## Technical Details

### Generator

- **Language**: Python 3
- **Input**: Behave JSON (pretty format preferred)
- **Output**: Single HTML file (self-contained)
- **Size**: ~300KB (includes embedded CSS/JS)
- **Dependencies**: Chart.js (via CDN)

### Report Components

1. **HTML Structure**: Semantic HTML5
2. **CSS**: Modern, responsive design with CSS Grid/Flexbox
3. **JavaScript**: Vanilla JS for interactivity
4. **Charts**: Chart.js 4.4.0 for pie/bar charts

### Files

- `enhanced_report_generator.py` - Report generator script (~400 lines)
- `bdd_report_enhanced_*.html` - Generated reports
- `index.html` - Symlink to latest report

---

## Usage Examples

### Example 1: Run All BDD Tests

```bash
cd /opt/mycode/ptr/ai-job-engine/tests
./run_tests.sh bdd

# Output:
# - Console output
# - JSON: test_reports/bdd/bdd_test_results.json
# - Enhanced HTML: test_reports/bdd/bdd_report_enhanced_*.html
# - Symlink: test_reports/bdd/index.html
# - Dashboard updated automatically
```

### Example 2: Run Specific Feature

```bash
cd /opt/mycode/ptr/ai-job-engine/tests/bdd
./run_bdd_tests.sh -f journey_management

# Generates enhanced report for journey management only
```

### Example 3: Run with Tags

```bash
./run_bdd_tests.sh -t @smoke

# Generates report for smoke test scenarios only
```

---

## Customization

### Modify Colors

Edit `enhanced_report_generator.py`, search for `:root` in CSS:

```css
:root {
    --success: #10b981;      /* Green for passed */
    --fail: #ef4444;         /* Red for failed */
    --error: #f59e0b;        /* Orange for error */
    --primary: #667eea;      /* Primary theme color */
}
```

### Add Custom Sections

Add new methods to `EnhancedBDDReportGenerator`:

```python
def _generate_custom_section(self):
    return '<section>...</section>'
```

Then call in `_build_complete_html()`.

### Modify Charts

Edit the Chart.js configuration in `_generate_javascript()` method.

---

## Integration with Unified Dashboard

The unified dashboard (`test_reports/test_reports.html`) automatically links to enhanced BDD reports:

- **BDD Card**: Shows summary from JSON
- **Click Card**: Drill-down view
- **"View HTML Report →"**: Opens enhanced report in new tab

---

## Benefits

### For Developers
- ✅ Visual feedback on test status
- ✅ Easy debugging with step details
- ✅ Quick identification of failures
- ✅ Timing information for optimization

### For Stakeholders
- ✅ Professional, readable format
- ✅ Visual charts for quick understanding
- ✅ Human-readable Given/When/Then scenarios
- ✅ Shareable single HTML file

### For Teams
- ✅ Standardized reporting across all test types
- ✅ No external tools required (just Python + browser)
- ✅ Fast generation (<5 seconds)
- ✅ CI/CD artifacts ready

---

## Troubleshooting

### Report Not Generating

**Check**:
```bash
# Verify JSON exists
ls test_reports/bdd/*.json

# Run generator manually
python3 tests/bdd/enhanced_report_generator.py \
    --input test_reports/bdd/bdd_test_raw_*_pretty.json \
    --output test_reports/bdd/test.html
```

### Charts Not Showing

- Requires internet connection for Chart.js CDN
- Or modify generator to use local Chart.js

### Styles Not Applied

- Report is self-contained, should work offline
- Try different browser
- Check browser console for errors

---

## Related Documentation

- [`tests/README.md`](../README.md) - Complete test suite guide
- [`tests/bdd/README.md`](README.md) - BDD test guide
- [`test_reports/UNIFIED_DASHBOARD.md`](../../test_reports/UNIFIED_DASHBOARD.md) - Dashboard documentation

---

**Created**: December 4, 2025  
**Generator**: `tests/bdd/enhanced_report_generator.py`  
**Report Format**: Self-contained HTML with charts  
**Status**: ✅ Fully Implemented

