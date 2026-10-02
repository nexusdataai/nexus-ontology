# MCP Troubleshooting Guide

This guide helps you diagnose and fix common issues with MCP (Model Context Protocol) servers in Cursor IDE, making local development smooth and reliable.

## 🚀 Quick Start

### Option 1: Simple Wrapper (Easiest)
```bash
# Quick health check
./diagnose

# Fix common issues automatically
./diagnose fix

# Full comprehensive diagnostics
./diagnose full

# Clean up stuck processes
./diagnose clean
```

### Option 2: Shell Script (Advanced)
```bash
# Quick health check
./mcp-doctor.sh

# Fix common issues automatically
./mcp-doctor.sh fix

# Full comprehensive diagnostics
./mcp-doctor.sh full

# Clean up stuck processes
./mcp-doctor.sh cleanup
```

### Option 3: Python Script (Direct)
```bash
# Basic diagnostics
.venv/bin/python mcp_diagnostics.py

# Auto-fix issues
.venv/bin/python mcp_diagnostics.py --fix

# Verbose output
.venv/bin/python mcp_diagnostics.py --verbose

# Skip tool testing (faster)
.venv/bin/python mcp_diagnostics.py --no-tools
```

## 🔧 Common Issues & Solutions

### 1. **"Not connected" Error**
**Symptoms**: MCP tools return `{"error":"Not connected"}`

**Solutions**:
```bash
# Clean up stuck processes
./diagnose clean

# Restart with auto-fix
./diagnose fix
```

**Manual Steps**:
1. Disable MCP server in Cursor settings
2. Run cleanup: `./diagnose clean`
3. Re-enable MCP server in Cursor
4. Test: `./diagnose`

### 2. **Empty Results from Tools**
**Symptoms**: Tools return empty arrays or zero counts

**Causes & Fixes**:
- **Wrong table names**: Run `./diagnose fix` to update defaults
- **AWS credentials**: Check with `aws configure list`
- **Table doesn't exist**: Verify with `aws dynamodb list-tables`

### 3. **JSON Serialization Errors**
**Symptoms**: "Object of type Decimal is not JSON serializable"

**Fix**: Already handled in the diagnostic script - run `./diagnose fix`

### 4. **Multiple MCP Processes**
**Symptoms**: Slow responses, inconsistent behavior

**Fix**:
```bash
./diagnose clean
```

### 5. **Environment Variables Not Working**
**Symptoms**: Server uses wrong configuration despite mcp-config.json

**Fix**: The diagnostic script sets correct defaults in the code itself.

## 📊 Diagnostic Features

### Environment Checks
- ✅ Python version (3.8+)
- ✅ Required dependencies (boto3, loguru, psutil)
- ✅ Project structure validation
- ✅ UV package manager

### AWS Configuration
- ✅ Credentials validation
- ✅ Region configuration
- ✅ DynamoDB table existence
- ✅ Table access permissions

### MCP Server Health
- ✅ Configuration file validation
- ✅ Process monitoring
- ✅ Stdio communication testing
- ✅ Tool registration verification
- ✅ Tool execution testing

### Database Service
- ✅ Direct service testing
- ✅ Real data validation
- ✅ Performance monitoring

## 🛠️ Advanced Usage

### Custom Diagnostics
```python
from mcp_diagnostics import MCPDiagnostics

# Create diagnostics instance
diagnostics = MCPDiagnostics(verbose=True, auto_fix=True)

# Run specific checks
await diagnostics.check_environment()
await diagnostics.test_mcp_stdio_communication()
await diagnostics.test_tool_execution()
```

### Process Management
```python
# Get all MCP processes
processes = diagnostics.get_mcp_processes()

# Clean up stuck processes
diagnostics.cleanup_mcp_processes()
```

### Configuration Validation
```python
# Check MCP config
config_valid = diagnostics.check_mcp_config()

# Check AWS setup
aws_valid = diagnostics.check_aws_credentials()
```

## 📋 Troubleshooting Checklist

### Before Starting Development
- [ ] Run `./mcp-doctor.sh quick` to verify setup
- [ ] Check AWS credentials: `aws sts get-caller-identity`
- [ ] Verify tables exist: `aws dynamodb list-tables`

### When Tools Stop Working
1. [ ] Run `./mcp-doctor.sh fix`
2. [ ] Restart Cursor IDE
3. [ ] Disable/enable MCP server in Cursor
4. [ ] Test with `./mcp-doctor.sh test`

### For New Environment Setup
1. [ ] Install dependencies: `./mcp-doctor.sh install`
2. [ ] Configure AWS credentials
3. [ ] Run full diagnostics: `./mcp-doctor.sh full`
4. [ ] Test tools: `./mcp-doctor.sh test`

## 📁 Generated Reports

The diagnostic script generates detailed reports saved as:
```
mcp_diagnostics_report_YYYYMMDD_HHMMSS.txt
```

These reports include:
- Issues found
- Fixes applied
- Recommendations
- System configuration details

## 🔍 Debugging Tips

### Enable Verbose Logging
```bash
# Shell script
./mcp-doctor.sh full

# Python script
python3 mcp_diagnostics.py --verbose
```

### Test Individual Components
```bash
# Test only MCP communication (no tools)
python3 mcp_diagnostics.py --no-tools

# Test only database service
python3 -c "
import asyncio
from src.services.ecommerce_service import EcommerceService
from src.models.ecommerce_models import CategoryCountsRequest

async def test():
    service = EcommerceService()
    result = await service.get_category_counts(CategoryCountsRequest())
    print(f'Status: {result.status}, Products: {result.total_products}')

asyncio.run(test())
"
```

### Monitor MCP Processes
```bash
# Watch MCP processes in real-time
watch -n 2 'ps aux | grep mcp_stdio_server.py | grep -v grep'

# Check process resource usage
ps aux | grep mcp_stdio_server.py | grep -v grep
```

## 🚨 Emergency Recovery

If everything breaks:

1. **Nuclear Option**:
   ```bash
   ./mcp-doctor.sh cleanup
   pkill -f cursor
   # Restart Cursor
   ./mcp-doctor.sh fix
   ```

2. **Reset Configuration**:
   ```bash
   # Backup current config
   cp mcp-config.json mcp-config.json.bak
   
   # Reset to defaults
   ./mcp-doctor.sh fix
   ```

3. **Reinstall Dependencies**:
   ```bash
   ./mcp-doctor.sh install
   ```

## 📞 Getting Help

1. Run full diagnostics: `./mcp-doctor.sh full`
2. Check the generated report
3. Look for specific error messages
4. Use verbose mode for detailed output

## 🎯 Best Practices

1. **Regular Health Checks**: Run `./mcp-doctor.sh quick` before starting development
2. **Clean Processes**: Run `./mcp-doctor.sh cleanup` if you notice slow responses
3. **Monitor Resources**: Keep an eye on multiple MCP processes
4. **Update Regularly**: Keep diagnostic scripts updated
5. **Save Reports**: Keep diagnostic reports for troubleshooting patterns

---

**Happy MCP Development! 🎉**
