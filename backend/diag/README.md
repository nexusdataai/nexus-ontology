# Diagnostic Tools and Documentation

This directory contains all diagnostic scripts, troubleshooting documents, and testing utilities for the E-commerce MCP Server project.

## Files Overview

### 📋 Documentation
- **MCP_TROUBLESHOOTING.md** - Comprehensive MCP troubleshooting guide
- **CURSOR_TROUBLESHOOTING.md** - Cursor IDE specific troubleshooting
- **README.md** - This file

### 🔧 Diagnostic Scripts
- **mcp-doctor.sh** - Main diagnostic script for MCP server health checks
- **mcp_diagnostics.py** - Python-based comprehensive diagnostics tool
- **diagnose** - Quick diagnostic script

### 🧪 Testing Scripts
- **test-stdio-mcp.sh** - Test script for MCP stdio server
- **rebuild-and-test.sh** - Build and test automation script
- **verify_database.py** - Database verification script

### 📊 Reports
- **../logs/mcp_diagnostics_report_*.txt** - Generated diagnostic reports (saved in logs/ folder)

### ⚙️ Configuration
- **pytest.ini** - Python testing configuration (if present)

## Usage

### Quick Diagnostics
```bash
# From within the diag/ directory:
cd diag/

# Run quick diagnosis
./diagnose

# Run comprehensive health check
./mcp-doctor.sh

# Run Python diagnostics
python mcp_diagnostics.py

# Or from project root:
./diag/diagnose
./diag/mcp-doctor.sh
python ./diag/mcp_diagnostics.py
```

### Testing
```bash
# From within the diag/ directory:
cd diag/

# Test MCP stdio server
./test-stdio-mcp.sh

# Rebuild and test
./rebuild-and-test.sh

# Verify database
python verify_database.py

# Or from project root:
./diag/test-stdio-mcp.sh
./diag/rebuild-and-test.sh
python ./diag/verify_database.py
```

## Available Commands

### diagnose (Simple wrapper)
- `./diagnose` or `./diagnose quick` - Quick health check
- `./diagnose full` - Full comprehensive diagnostics  
- `./diagnose fix` - Auto-fix common issues
- `./diagnose clean` - Clean up stuck MCP processes
- `./diagnose test` - Test tools only
- `./diagnose install` - Install missing dependencies

### mcp-doctor.sh (Advanced shell script)
- `./mcp-doctor.sh quick` - Quick health check
- `./mcp-doctor.sh full` - Full diagnostics with verbose output
- `./mcp-doctor.sh fix` - Run diagnostics with auto-fix
- `./mcp-doctor.sh cleanup` - Kill stuck MCP processes
- `./mcp-doctor.sh test` - Test MCP tools
- `./mcp-doctor.sh install` - Install dependencies

### mcp_diagnostics.py (Python script)
- `python mcp_diagnostics.py` - Basic diagnostics
- `python mcp_diagnostics.py --fix` - Auto-fix issues
- `python mcp_diagnostics.py --verbose` - Verbose output
- `python mcp_diagnostics.py --no-tools` - Skip tool testing

## Organization
All diagnostic and troubleshooting files have been moved here to keep the project root clean while maintaining easy access to debugging tools.
