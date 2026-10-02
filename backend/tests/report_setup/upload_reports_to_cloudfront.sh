#!/bin/bash
#
# Quick Upload Script - Upload existing test reports to CloudFront
#

set -e

BUCKET="ai-engine-test-reports"
REGION="us-east-1"
CLOUDFRONT_DIST="E269STPYK4FJVQ"
CLOUDFRONT_DOMAIN="d37vwg02pj6oqg.cloudfront.net"
PREFIX="test-reports"

# Detect Python
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Upload Existing Reports to CloudFront                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo

# Find latest reports
UNIT_REPORT=$(ls -t test_reports/unit/unit_test_report_enhanced_*.html 2>/dev/null | head -1)
INTEGRATION_REPORT=$(ls -t test_reports/integration/integration_test_report_enhanced_*.html 2>/dev/null | head -1)
BDD_REPORT=$(ls -t test_reports/bdd/bdd_test_report_enhanced_*.html 2>/dev/null | head -1)
ENDURANCE_REPORT=$(ls -t test_reports/endurance/endurance_test_report_enhanced_*.html 2>/dev/null | head -1)

if [ -z "$UNIT_REPORT" ] && [ -z "$INTEGRATION_REPORT" ] && [ -z "$BDD_REPORT" ] && [ -z "$ENDURANCE_REPORT" ]; then
    echo "❌ No enhanced test reports found"
    echo "   Run tests first: ./tests/run_tests.sh unit,integration,bdd,endurance"
    exit 1
fi

echo "Found reports to upload:"
if [ -n "$UNIT_REPORT" ]; then
    echo "  📦 Unit Report: $(basename "$UNIT_REPORT") ($(du -h "$UNIT_REPORT" | cut -f1))"
fi
if [ -n "$INTEGRATION_REPORT" ]; then
    echo "  📦 Integration Report: $(basename "$INTEGRATION_REPORT") ($(du -h "$INTEGRATION_REPORT" | cut -f1))"
fi
if [ -n "$BDD_REPORT" ]; then
    echo "  📦 BDD Report: $(basename "$BDD_REPORT") ($(du -h "$BDD_REPORT" | cut -f1))"
fi
if [ -n "$ENDURANCE_REPORT" ]; then
    echo "  📦 Endurance Report: $(basename "$ENDURANCE_REPORT") ($(du -h "$ENDURANCE_REPORT" | cut -f1))"
fi
echo

# Upload directly to S3 with correct path for CloudFront OriginPath
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Upload unit report
if [ -n "$UNIT_REPORT" ]; then
    echo "📤 Uploading unit test report..."
    echo "  To S3: test-reports/unit/$TIMESTAMP/report.html"
    echo "  CloudFront URL: https://$CLOUDFRONT_DOMAIN/unit/$TIMESTAMP/report.html"
    echo

    aws s3 cp "$UNIT_REPORT" \
        "s3://$BUCKET/test-reports/unit/$TIMESTAMP/report.html" \
        --content-type "text/html; charset=utf-8" \
        --region "$REGION"

    echo "✅ Unit report uploaded"
    echo
fi

# Upload integration report
if [ -n "$INTEGRATION_REPORT" ]; then
    echo "📤 Uploading integration test report..."
    echo "  To S3: test-reports/integration/$TIMESTAMP/report.html"
    echo "  CloudFront URL: https://$CLOUDFRONT_DOMAIN/integration/$TIMESTAMP/report.html"
    echo

    aws s3 cp "$INTEGRATION_REPORT" \
        "s3://$BUCKET/test-reports/integration/$TIMESTAMP/report.html" \
        --content-type "text/html; charset=utf-8" \
        --region "$REGION"

    echo "✅ Integration report uploaded"
    echo
fi

# Upload BDD report
if [ -n "$BDD_REPORT" ]; then
    echo "📤 Uploading BDD test report..."
    echo "  To S3: test-reports/bdd/$TIMESTAMP/report.html"
    echo "  CloudFront URL: https://$CLOUDFRONT_DOMAIN/bdd/$TIMESTAMP/report.html"
    echo

    aws s3 cp "$BDD_REPORT" \
        "s3://$BUCKET/test-reports/bdd/$TIMESTAMP/report.html" \
        --content-type "text/html; charset=utf-8" \
        --region "$REGION"

    echo "✅ BDD report uploaded"
    echo
fi

# Upload Endurance report
if [ -n "$ENDURANCE_REPORT" ]; then
    echo "📤 Uploading Endurance test report..."
    echo "  To S3: test-reports/endurance/$TIMESTAMP/report.html"
    echo "  CloudFront URL: https://$CLOUDFRONT_DOMAIN/endurance/$TIMESTAMP/report.html"
    echo

    aws s3 cp "$ENDURANCE_REPORT" \
        "s3://$BUCKET/test-reports/endurance/$TIMESTAMP/report.html" \
        --content-type "text/html; charset=utf-8" \
        --region "$REGION"

    echo "✅ Endurance report uploaded"
    echo
fi

# Create index with correct CloudFront path (no test-reports prefix)
echo "📝 Creating index with all uploaded reports..."

# Function to extract stats from HTML report
extract_stats() {
    local report_file="$1"
    local total=0
    local passed=0
    local failed=0
    local pass_rate=0
    
    if [ -f "$report_file" ]; then
        # Extract from card-value pattern: card-value">NUMBER
        local stats=($(grep -oP 'card-value">\d+' "$report_file" 2>/dev/null | grep -oP '\d+' | head -4))
        
        if [ ${#stats[@]} -ge 3 ]; then
            total=${stats[0]:-0}
            passed=${stats[1]:-0}
            failed=${stats[2]:-0}
        fi
        
        # Calculate pass rate
        if [ "$total" -gt 0 ] 2>/dev/null; then
            pass_rate=$((passed * 100 / total))
        fi
    fi
    
    echo "$total $passed $failed $pass_rate"
}

# Function to generate SVG ring chart
generate_ring_svg() {
    local percentage=$1
    local color=$2
    local size=${3:-80}
    local stroke_width=${4:-8}
    
    local radius=$((size / 2 - stroke_width))
    local circumference=$(echo "scale=2; 2 * 3.14159 * $radius" | bc)
    local dash_offset=$(echo "scale=2; $circumference * (100 - $percentage) / 100" | bc)
    local center=$((size / 2))
    
    # Color based on percentage
    if [ "$percentage" -ge 80 ]; then
        color="#10b981"  # Green
    elif [ "$percentage" -ge 60 ]; then
        color="#f59e0b"  # Yellow/Amber
    else
        color="#ef4444"  # Red
    fi
    
    echo "<svg width=\"$size\" height=\"$size\" viewBox=\"0 0 $size $size\" class=\"ring-chart\">
        <circle cx=\"$center\" cy=\"$center\" r=\"$radius\" fill=\"none\" stroke=\"#e2e8f0\" stroke-width=\"$stroke_width\"/>
        <circle cx=\"$center\" cy=\"$center\" r=\"$radius\" fill=\"none\" stroke=\"$color\" stroke-width=\"$stroke_width\" 
            stroke-dasharray=\"$circumference\" stroke-dashoffset=\"$dash_offset\" 
            stroke-linecap=\"round\" transform=\"rotate(-90 $center $center)\"/>
        <text x=\"$center\" y=\"$center\" text-anchor=\"middle\" dy=\"0.35em\" 
            font-size=\"16\" font-weight=\"bold\" fill=\"$color\">$percentage%</text>
    </svg>"
}

# Extract stats from reports
UNIT_TOTAL=0
UNIT_PASSED=0
UNIT_FAILED=0
UNIT_RATE=0

INT_TOTAL=0
INT_PASSED=0
INT_FAILED=0
INT_RATE=0

BDD_TOTAL=0
BDD_PASSED=0
BDD_FAILED=0
BDD_RATE=0

END_TOTAL=0
END_PASSED=0
END_FAILED=0
END_RATE=0

if [ -n "$UNIT_REPORT" ]; then
    read UNIT_TOTAL UNIT_PASSED UNIT_FAILED UNIT_RATE <<< $(extract_stats "$UNIT_REPORT")
    echo "   Unit stats: Total=$UNIT_TOTAL, Passed=$UNIT_PASSED, Failed=$UNIT_FAILED, Rate=$UNIT_RATE%"
fi

if [ -n "$INTEGRATION_REPORT" ]; then
    read INT_TOTAL INT_PASSED INT_FAILED INT_RATE <<< $(extract_stats "$INTEGRATION_REPORT")
    echo "   Integration stats: Total=$INT_TOTAL, Passed=$INT_PASSED, Failed=$INT_FAILED, Rate=$INT_RATE%"
fi

if [ -n "$BDD_REPORT" ]; then
    read BDD_TOTAL BDD_PASSED BDD_FAILED BDD_RATE <<< $(extract_stats "$BDD_REPORT")
    echo "   BDD stats: Total=$BDD_TOTAL, Passed=$BDD_PASSED, Failed=$BDD_FAILED, Rate=$BDD_RATE%"
fi

if [ -n "$ENDURANCE_REPORT" ]; then
    read END_TOTAL END_PASSED END_FAILED END_RATE <<< $(extract_stats "$ENDURANCE_REPORT")
    echo "   Endurance stats: Total=$END_TOTAL, Passed=$END_PASSED, Failed=$END_FAILED, Rate=$END_RATE%"
fi

# Generate index HTML with beautiful 2x2 grid layout
cat > /tmp/index.html << INDEXHTML
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Reports - AI Job Engine</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f2 100%);
            color: #1e293b;
            line-height: 1.6;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 50px 24px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
            animation: pulse 15s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.1); opacity: 0.3; }
        }
        .header-content { position: relative; z-index: 1; }
        .header h1 { font-size: 38px; margin-bottom: 10px; font-weight: 700; }
        .header p { font-size: 16px; opacity: 0.9; }
        
        .main-container {
            max-width: 1100px;
            margin: -40px auto 0;
            padding: 0 24px 40px;
            position: relative;
            z-index: 10;
        }
        
        .dashboard-box {
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 60px rgba(0,0,0,0.12);
            padding: 32px;
            margin-bottom: 24px;
        }
        
        .dashboard-title {
            text-align: center;
            margin-bottom: 32px;
        }
        .dashboard-title h2 {
            font-size: 24px;
            color: #374151;
            margin-bottom: 8px;
        }
        .dashboard-title p {
            color: #9ca3af;
            font-size: 14px;
        }
        
        .grid-2x2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
        }
        
        .category-card {
            background: linear-gradient(145deg, #fafbfc 0%, #f3f4f6 100%);
            border-radius: 16px;
            padding: 24px;
            position: relative;
            transition: all 0.3s ease;
            border: 2px solid transparent;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: flex;
            gap: 20px;
        }
        .category-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .card-left { flex: 1; }
        .card-right {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-width: 100px;
            padding-left: 20px;
            border-left: 2px dashed #e5e7eb;
        }
        .kpi-large {
            font-size: 48px;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 4px;
        }
        .kpi-large.high { color: #059669; }
        .kpi-large.medium { color: #d97706; }
        .kpi-large.low { color: #dc2626; }
        .kpi-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #6b7280;
            font-weight: 600;
        }
        .category-card.unit { border-color: #10b981; }
        .category-card.unit:hover { background: linear-gradient(145deg, #ecfdf5 0%, #d1fae5 100%); }
        .category-card.integration { border-color: #3b82f6; }
        .category-card.integration:hover { background: linear-gradient(145deg, #eff6ff 0%, #dbeafe 100%); }
        .category-card.bdd { border-color: #f59e0b; }
        .category-card.bdd:hover { background: linear-gradient(145deg, #fffbeb 0%, #fef3c7 100%); }
        .category-card.endurance { border-color: #8b5cf6; }
        .category-card.endurance:hover { background: linear-gradient(145deg, #f5f3ff 0%, #ede9fe 100%); }
        
        .card-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
        }
        
        .category-circle {
            width: 70px;
            height: 70px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            flex-shrink: 0;
            position: relative;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }
        .category-circle.unit { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
        .category-circle.integration { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
        .category-circle.bdd { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
        .category-circle.endurance { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
        
        .card-title-section h3 {
            font-size: 18px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 4px;
        }
        .card-title-section p {
            font-size: 12px;
            color: #6b7280;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }
        .stat-box {
            text-align: center;
            padding: 12px 8px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .stat-box .value {
            font-size: 24px;
            font-weight: 700;
            line-height: 1.2;
        }
        .stat-box .label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #9ca3af;
            margin-top: 4px;
        }
        .stat-box.total .value { color: #374151; }
        .stat-box.passed .value { color: #059669; }
        .stat-box.failed .value { color: #dc2626; }
        
        .pass-rate-bar {
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 12px;
        }
        .pass-rate-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        .pass-rate-fill.high { background: linear-gradient(90deg, #10b981 0%, #059669 100%); }
        .pass-rate-fill.medium { background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%); }
        .pass-rate-fill.low { background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%); }
        
        .card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .pass-rate-text {
            font-size: 14px;
            font-weight: 600;
        }
        .pass-rate-text.high { color: #059669; }
        .pass-rate-text.medium { color: #d97706; }
        .pass-rate-text.low { color: #dc2626; }
        
        .view-btn {
            font-size: 12px;
            color: #667eea;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .view-btn::after {
            content: '→';
            transition: transform 0.2s;
        }
        .category-card:hover .view-btn::after {
            transform: translateX(4px);
        }
        
        .timestamp {
            text-align: center;
            padding: 16px;
            color: #9ca3af;
            font-size: 13px;
        }
        
        @media (max-width: 768px) {
            .grid-2x2 { grid-template-columns: 1fr; }
            .main-container { margin-top: -20px; }
            .header { padding: 40px 24px; }
            .header h1 { font-size: 28px; }
            .category-card { flex-direction: column; }
            .card-right {
                border-left: none;
                border-top: 2px dashed #e5e7eb;
                padding-left: 0;
                padding-top: 16px;
                margin-top: 16px;
                flex-direction: row;
                gap: 8px;
            }
            .kpi-large { font-size: 36px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>🎯 Test Reports Dashboard</h1>
            <p>AI Job Engine - Comprehensive Test Analytics</p>
        </div>
    </div>
    
    <div class="main-container">
        <div class="dashboard-box">
            <div class="dashboard-title">
                <h2>Test Categories</h2>
                <p>Click on any category to view detailed analytics report</p>
            </div>
            
            <div class="grid-2x2">
INDEXHTML

# Add Unit Test Card
if [ -n "$UNIT_REPORT" ]; then
    RATE_CLASS="low"
    [ "$UNIT_RATE" -ge 60 ] && RATE_CLASS="medium"
    [ "$UNIT_RATE" -ge 80 ] && RATE_CLASS="high"
    cat >> /tmp/index.html << UNITCARD
                <a href="unit/$TIMESTAMP/report.html" class="category-card unit">
                    <div class="card-left">
                        <div class="card-header">
                            <div class="category-circle unit">🧪</div>
                            <div class="card-title-section">
                                <h3>Unit Tests</h3>
                                <p>Component-level test coverage</p>
                            </div>
                        </div>
                        <div class="stats-grid">
                            <div class="stat-box total">
                                <div class="value">$UNIT_TOTAL</div>
                                <div class="label">Total</div>
                            </div>
                            <div class="stat-box passed">
                                <div class="value">$UNIT_PASSED</div>
                                <div class="label">Passed</div>
                            </div>
                            <div class="stat-box failed">
                                <div class="value">$UNIT_FAILED</div>
                                <div class="label">Failed</div>
                            </div>
                        </div>
                        <div class="pass-rate-bar">
                            <div class="pass-rate-fill $RATE_CLASS" style="width: ${UNIT_RATE}%"></div>
                        </div>
                        <div class="card-footer">
                            <span class="pass-rate-text $RATE_CLASS">${UNIT_RATE}% Pass Rate</span>
                            <span class="view-btn">View Report</span>
                        </div>
                    </div>
                    <div class="card-right">
                        <div class="kpi-large $RATE_CLASS">${UNIT_RATE}%</div>
                        <div class="kpi-label">Pass Rate</div>
                    </div>
                </a>
UNITCARD
fi

# Add Integration Test Card
if [ -n "$INTEGRATION_REPORT" ]; then
    RATE_CLASS="low"
    [ "$INT_RATE" -ge 60 ] && RATE_CLASS="medium"
    [ "$INT_RATE" -ge 80 ] && RATE_CLASS="high"
    cat >> /tmp/index.html << INTCARD
                <a href="integration/$TIMESTAMP/report.html" class="category-card integration">
                    <div class="card-left">
                        <div class="card-header">
                            <div class="category-circle integration">🔗</div>
                            <div class="card-title-section">
                                <h3>Integration Tests</h3>
                                <p>End-to-end API & service tests</p>
                            </div>
                        </div>
                        <div class="stats-grid">
                            <div class="stat-box total">
                                <div class="value">$INT_TOTAL</div>
                                <div class="label">Total</div>
                            </div>
                            <div class="stat-box passed">
                                <div class="value">$INT_PASSED</div>
                                <div class="label">Passed</div>
                            </div>
                            <div class="stat-box failed">
                                <div class="value">$INT_FAILED</div>
                                <div class="label">Failed</div>
                            </div>
                        </div>
                        <div class="pass-rate-bar">
                            <div class="pass-rate-fill $RATE_CLASS" style="width: ${INT_RATE}%"></div>
                        </div>
                        <div class="card-footer">
                            <span class="pass-rate-text $RATE_CLASS">${INT_RATE}% Pass Rate</span>
                            <span class="view-btn">View Report</span>
                        </div>
                    </div>
                    <div class="card-right">
                        <div class="kpi-large $RATE_CLASS">${INT_RATE}%</div>
                        <div class="kpi-label">Pass Rate</div>
                    </div>
                </a>
INTCARD
fi

# Add BDD Test Card
if [ -n "$BDD_REPORT" ]; then
    RATE_CLASS="low"
    [ "$BDD_RATE" -ge 60 ] && RATE_CLASS="medium"
    [ "$BDD_RATE" -ge 80 ] && RATE_CLASS="high"
    cat >> /tmp/index.html << BDDCARD
                <a href="bdd/$TIMESTAMP/report.html" class="category-card bdd">
                    <div class="card-left">
                        <div class="card-header">
                            <div class="category-circle bdd">📝</div>
                            <div class="card-title-section">
                                <h3>BDD Tests</h3>
                                <p>Behavior-driven scenarios</p>
                            </div>
                        </div>
                        <div class="stats-grid">
                            <div class="stat-box total">
                                <div class="value">$BDD_TOTAL</div>
                                <div class="label">Scenarios</div>
                            </div>
                            <div class="stat-box passed">
                                <div class="value">$BDD_PASSED</div>
                                <div class="label">Passed</div>
                            </div>
                            <div class="stat-box failed">
                                <div class="value">$BDD_FAILED</div>
                                <div class="label">Failed</div>
                            </div>
                        </div>
                        <div class="pass-rate-bar">
                            <div class="pass-rate-fill $RATE_CLASS" style="width: ${BDD_RATE}%"></div>
                        </div>
                        <div class="card-footer">
                            <span class="pass-rate-text $RATE_CLASS">${BDD_RATE}% Pass Rate</span>
                            <span class="view-btn">View Report</span>
                        </div>
                    </div>
                    <div class="card-right">
                        <div class="kpi-large $RATE_CLASS">${BDD_RATE}%</div>
                        <div class="kpi-label">Pass Rate</div>
                    </div>
                </a>
BDDCARD
fi

# Add Endurance Test Card
if [ -n "$ENDURANCE_REPORT" ]; then
    RATE_CLASS="low"
    [ "$END_RATE" -ge 60 ] && RATE_CLASS="medium"
    [ "$END_RATE" -ge 80 ] && RATE_CLASS="high"
    cat >> /tmp/index.html << ENDCARD
                <a href="endurance/$TIMESTAMP/report.html" class="category-card endurance">
                    <div class="card-left">
                        <div class="card-header">
                            <div class="category-circle endurance">🏃</div>
                            <div class="card-title-section">
                                <h3>Endurance Tests</h3>
                                <p>Performance & stability tests</p>
                            </div>
                        </div>
                        <div class="stats-grid">
                            <div class="stat-box total">
                                <div class="value">$END_TOTAL</div>
                                <div class="label">Iterations</div>
                            </div>
                            <div class="stat-box passed">
                                <div class="value">$END_PASSED</div>
                                <div class="label">Passed</div>
                            </div>
                            <div class="stat-box failed">
                                <div class="value">$END_FAILED</div>
                                <div class="label">Failed</div>
                            </div>
                        </div>
                        <div class="pass-rate-bar">
                            <div class="pass-rate-fill $RATE_CLASS" style="width: ${END_RATE}%"></div>
                        </div>
                        <div class="card-footer">
                            <span class="pass-rate-text $RATE_CLASS">${END_RATE}% Pass Rate</span>
                            <span class="view-btn">View Report</span>
                        </div>
                    </div>
                    <div class="card-right">
                        <div class="kpi-large $RATE_CLASS">${END_RATE}%</div>
                        <div class="kpi-label">Pass Rate</div>
                    </div>
                </a>
ENDCARD
fi

# Close HTML
cat >> /tmp/index.html << INDEXEND
            </div>
        </div>
        
        <div class="timestamp">
            Last updated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
        </div>
    </div>
</body>
</html>
INDEXEND

aws s3 cp /tmp/index.html \
    "s3://$BUCKET/test-reports/index.html" \
    --content-type "text/html; charset=utf-8" \
    --region "$REGION"

rm /tmp/index.html

echo "✅ Index uploaded"

if [ $? -ne 0 ]; then
    echo "❌ Upload failed"
    exit 1
fi

echo
echo "🔄 Creating CloudFront cache invalidation..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DIST" \
    --paths "/*" --query 'Invalidation.Id' --output text)

echo "   Invalidation ID: $INVALIDATION_ID"
echo

# Wait for invalidation to complete
echo "⏳ Waiting for invalidation to complete..."
echo "   (This typically takes 30-60 seconds)"
echo

WAIT_COUNT=0
MAX_WAIT=120  # Max 2 minutes

while true; do
    STATUS=$(aws cloudfront get-invalidation \
        --distribution-id "$CLOUDFRONT_DIST" \
        --id "$INVALIDATION_ID" \
        --query 'Invalidation.Status' --output text 2>/dev/null || echo "InProgress")
    
    if [ "$STATUS" = "Completed" ]; then
        echo "   ✅ Invalidation completed!"
        break
    fi
    
    WAIT_COUNT=$((WAIT_COUNT + 5))
    if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
        echo "   ⚠️  Invalidation still in progress after ${MAX_WAIT}s"
        echo "   Reports should be available shortly"
        break
    fi
    
    printf "\r   ⏳ Status: $STATUS (${WAIT_COUNT}s elapsed)...  "
    sleep 5
done

echo
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ✅ UPLOAD & INVALIDATION COMPLETE!              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 View your test reports NOW at:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "  https://$CLOUDFRONT_DOMAIN/index.html"
echo
echo "Reports available:"
[ -n "$UNIT_REPORT" ] && echo "  🧪 Unit Test Report"
[ -n "$INTEGRATION_REPORT" ] && echo "  🔗 Integration Test Report"
[ -n "$BDD_REPORT" ] && echo "  📝 BDD Test Report"
[ -n "$ENDURANCE_REPORT" ] && echo "  🏃 Endurance Test Report"
echo
echo "📊 Features:"
echo "  • Interactive charts and analytics"
echo "  • Detailed test results"
echo "  • Drill-down capabilities"
echo "  • Search and filter"
echo
