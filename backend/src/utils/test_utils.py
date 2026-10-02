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

"""Test utility functions for TMF ODA Transformer."""

from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock

from loguru import logger
from mcp.server.fastmcp import Context

from ..models import TMFODAComponentType, DatabaseType, SchemaFormat


async def run_test_imports(ctx: Context, include_performance: bool = False) -> Dict[str, Any]:
    """Test that all tools can be imported successfully."""
    test_start = datetime.now()
    
    try:
        # Test imports one by one to identify specific failures
        imports_tested = []
        
        # Test server tools
        try:
            from ..tools import (
                # schema_analyzer_tool,  # Commented out for focus on core execution tools
                # db_analyzer_tool,      # Commented out for focus on core execution tools
                raw_analysis_tool,
                stripped_schema_tool,
                get_job_logs_tool,
                test_runner_tool,
                journeys_tool,
                run_jobs_tool
            )
            imports_tested.append(('Server Tools', True, 'All 6 tools imported successfully'))
        except Exception as e:
            imports_tested.append(('Server Tools', False, f'Import failed: {str(e)}'))
        
        # Test models
        try:
            from ..models import (
                TMFODAComponentType,
                DatabaseType,
                SchemaFormat,
                ComplianceLevel
            )
            imports_tested.append(('Models', True, 'All model classes imported successfully'))
        except Exception as e:
            imports_tested.append(('Models', False, f'Import failed: {str(e)}'))
        
        # Test services (only services that exist for the remaining tools)
        try:
            from ..services import (
                # SchemaAnalysisService,      # Commented out for focus on core execution tools
                # DatabaseAnalysisService,    # Commented out for focus on core execution tools
                SimpleJourneyService,
                ValidationService
            )
            imports_tested.append(('Services', True, 'All available service classes imported successfully'))
        except Exception as e:
            imports_tested.append(('Services', False, f'Import failed: {str(e)}'))
        
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        # Calculate results
        all_passed = all(result[1] for result in imports_tested)
        passed_count = sum(1 for result in imports_tested if result[1])
        
        return {
            'test_name': 'Import Verification',
            'status': 'success' if all_passed else 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'details': {
                'imports_tested': len(imports_tested),
                'imports_passed': passed_count,
                'results': imports_tested
            },
            'message': f'✅ All imports successful' if all_passed else f'❌ {len(imports_tested) - passed_count}/{len(imports_tested)} imports failed'
        }
        
    except Exception as e:
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        return {
            'test_name': 'Import Verification',
            'status': 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'error': str(e),
            'message': f'❌ Import test failed: {str(e)}'
        }


async def run_validation_tests(ctx: Context, include_performance: bool = False) -> List[Dict[str, Any]]:
    """Run validation tests for available tools (excluding removed schema and db analyzers)."""
    validation_tests = []
    
    # Test raw analysis validation
    test_result = await _test_raw_analysis_validation(ctx, include_performance)
    validation_tests.append(test_result)
    
    # Test stripped schema validation
    test_result = await _test_stripped_schema_validation(ctx, include_performance)
    validation_tests.append(test_result)
    
    # Test get job logs validation
    test_result = await _test_get_job_logs_validation(ctx, include_performance)
    validation_tests.append(test_result)
    
    # Test run jobs validation
    test_result = await _test_run_jobs_validation(ctx, include_performance)
    validation_tests.append(test_result)
    
    # Test journeys tool validation
    test_result = await _test_journeys_validation(ctx, include_performance)
    validation_tests.append(test_result)
    
    # Test test runner validation
    test_result = await _test_test_runner_validation(ctx, include_performance)
    validation_tests.append(test_result)
    
    return validation_tests


async def _test_raw_analysis_validation(ctx: Context, include_performance: bool = False) -> Dict[str, Any]:
    """Test raw analysis tool validation."""
    test_start = datetime.now()
    
    try:
        from ..tools.execution_tools import raw_analysis_tool
        
        mock_ctx = AsyncMock()
        mock_ctx.error = AsyncMock()
        
        validation_tests = []
        
        # Test empty journey ID validation
        try:
            await raw_analysis_tool(
                ctx=mock_ctx,
                journey_id="",
                stage_id="raw_analysis",
                triggered_by="test",
                reason="test"
            )
            validation_tests.append(('Empty journey ID', False, 'Should have raised ValueError'))
        except ValueError:
            validation_tests.append(('Empty journey ID', True, 'Correctly validates empty journey ID'))
        except Exception as e:
            validation_tests.append(('Empty journey ID', False, f'Unexpected error: {str(e)}'))
        
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        all_passed = all(result[1] for result in validation_tests)
        passed_count = sum(1 for result in validation_tests if result[1])
        
        return {
            'test_name': 'Raw Analysis Validation',
            'status': 'success' if all_passed else 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'details': {
                'validations_tested': len(validation_tests),
                'validations_passed': passed_count,
                'results': validation_tests
            },
            'message': f'✅ All validations passed' if all_passed else f'❌ {len(validation_tests) - passed_count}/{len(validation_tests)} validations failed'
        }
        
    except Exception as e:
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        return {
            'test_name': 'Raw Analysis Validation',
            'status': 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'error': str(e),
            'message': f'❌ Raw analysis test failed: {str(e)}'
        }


async def _test_stripped_schema_validation(ctx: Context, include_performance: bool = False) -> Dict[str, Any]:
    """Test stripped schema tool validation."""
    test_start = datetime.now()
    
    try:
        from ..tools.execution_tools import stripped_schema_tool
        
        mock_ctx = AsyncMock()
        mock_ctx.error = AsyncMock()
        
        validation_tests = []
        
        # Test empty journey ID validation
        try:
            await stripped_schema_tool(
                ctx=mock_ctx,
                journey_id="",
                stage_id="stripped_schema",
                triggered_by="test",
                reason="test"
            )
            validation_tests.append(('Empty journey ID', False, 'Should have raised ValueError'))
        except ValueError:
            validation_tests.append(('Empty journey ID', True, 'Correctly validates empty journey ID'))
        except Exception as e:
            validation_tests.append(('Empty journey ID', False, f'Unexpected error: {str(e)}'))
        
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        all_passed = all(result[1] for result in validation_tests)
        passed_count = sum(1 for result in validation_tests if result[1])
        
        return {
            'test_name': 'Stripped Schema Validation',
            'status': 'success' if all_passed else 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'details': {
                'validations_tested': len(validation_tests),
                'validations_passed': passed_count,
                'results': validation_tests
            },
            'message': f'✅ All validations passed' if all_passed else f'❌ {len(validation_tests) - passed_count}/{len(validation_tests)} validations failed'
        }
        
    except Exception as e:
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        return {
            'test_name': 'Stripped Schema Validation',
            'status': 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'error': str(e),
            'message': f'❌ Stripped schema test failed: {str(e)}'
        }


async def _test_get_job_logs_validation(ctx: Context, include_performance: bool = False) -> Dict[str, Any]:
    """Test get job logs tool validation."""
    test_start = datetime.now()
    
    try:
        from ..tools.utility_tools import get_job_logs_tool
        
        mock_ctx = AsyncMock()
        mock_ctx.error = AsyncMock()
        
        validation_tests = []
        
        # Test empty journey ID validation
        try:
            await get_job_logs_tool(
                ctx=mock_ctx,
                journey_id="",
                stage_name="raw_analysis",
                job_id="JOB-001-20240101120000",
                step_name="schema_parsing"
            )
            validation_tests.append(('Empty journey ID', False, 'Should have raised ValueError'))
        except ValueError:
            validation_tests.append(('Empty journey ID', True, 'Correctly validates empty journey ID'))
        except Exception as e:
            validation_tests.append(('Empty journey ID', False, f'Unexpected error: {str(e)}'))
        
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        all_passed = all(result[1] for result in validation_tests)
        passed_count = sum(1 for result in validation_tests if result[1])
        
        return {
            'test_name': 'Get Job Logs Validation',
            'status': 'success' if all_passed else 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'details': {
                'validations_tested': len(validation_tests),
                'validations_passed': passed_count,
                'results': validation_tests
            },
            'message': f'✅ All validations passed' if all_passed else f'❌ {len(validation_tests) - passed_count}/{len(validation_tests)} validations failed'
        }
        
    except Exception as e:
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        return {
            'test_name': 'Get Job Logs Validation',
            'status': 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'error': str(e),
            'message': f'❌ Get job logs test failed: {str(e)}'
        }


async def _test_run_jobs_validation(ctx: Context, include_performance: bool = False) -> Dict[str, Any]:
    """Test run jobs tool validation."""
    test_start = datetime.now()
    
    try:
        from ..tools.execution_tools import run_jobs_tool
        
        mock_ctx = AsyncMock()
        mock_ctx.error = AsyncMock()
        
        validation_tests = []
        
        # Test empty journey ID validation
        try:
            await run_jobs_tool(
                ctx=mock_ctx,
                journey_id="",
                stage_id="raw_analysis",
                triggered_by="test",
                reason="test"
            )
            validation_tests.append(('Empty journey ID', False, 'Should have raised ValueError'))
        except ValueError:
            validation_tests.append(('Empty journey ID', True, 'Correctly validates empty journey ID'))
        except Exception as e:
            validation_tests.append(('Empty journey ID', False, f'Unexpected error: {str(e)}'))
        
        # Test empty stage ID validation
        try:
            await run_jobs_tool(
                ctx=mock_ctx,
                journey_id="JRN-TEST-001",
                stage_id="",
                triggered_by="test",
                reason="test"
            )
            validation_tests.append(('Empty stage ID', False, 'Should have raised ValueError'))
        except ValueError:
            validation_tests.append(('Empty stage ID', True, 'Correctly validates empty stage ID'))
        except Exception as e:
            validation_tests.append(('Empty stage ID', False, f'Unexpected error: {str(e)}'))
        
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        all_passed = all(result[1] for result in validation_tests)
        passed_count = sum(1 for result in validation_tests if result[1])
        
        return {
            'test_name': 'Run Jobs Validation',
            'status': 'success' if all_passed else 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'details': {
                'validations_tested': len(validation_tests),
                'validations_passed': passed_count,
                'results': validation_tests
            },
            'message': f'✅ All validations passed' if all_passed else f'❌ {len(validation_tests) - passed_count}/{len(validation_tests)} validations failed'
        }
        
    except Exception as e:
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        return {
            'test_name': 'Run Jobs Validation',
            'status': 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'error': str(e),
            'message': f'❌ Run jobs test failed: {str(e)}'
        }


async def _test_journeys_validation(ctx: Context, include_performance: bool = False) -> Dict[str, Any]:
    """Test journeys tool validation."""
    test_start = datetime.now()
    
    try:
        from ..tools.management_tools import journeys_tool
        
        mock_ctx = AsyncMock()
        mock_ctx.error = AsyncMock()
        
        validation_tests = []
        
        # Test valid READ operation
        try:
            result = await journeys_tool(
                ctx=mock_ctx,
                action="read",
                journey_id="",
                journey_data=None,
                stage_id="",
                include_stages=True,
                include_job_history=True,
                job_limit=10
            )
            # This should succeed even with empty params for READ operation
            validation_tests.append(('READ operation', True, 'Successfully handles READ operation'))
        except Exception as e:
            validation_tests.append(('READ operation', False, f'Unexpected error: {str(e)}'))
        
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        all_passed = all(result[1] for result in validation_tests)
        passed_count = sum(1 for result in validation_tests if result[1])
        
        return {
            'test_name': 'Journeys Validation',
            'status': 'success' if all_passed else 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'details': {
                'validations_tested': len(validation_tests),
                'validations_passed': passed_count,
                'results': validation_tests
            },
            'message': f'✅ All validations passed' if all_passed else f'❌ {len(validation_tests) - passed_count}/{len(validation_tests)} validations failed'
        }
        
    except Exception as e:
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        return {
            'test_name': 'Journeys Validation',
            'status': 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'error': str(e),
            'message': f'❌ Journeys test failed: {str(e)}'
        }


async def _test_test_runner_validation(ctx: Context, include_performance: bool = False) -> Dict[str, Any]:
    """Test test runner tool validation."""
    test_start = datetime.now()
    
    try:
        from ..tools.utility_tools import test_runner_tool
        
        mock_ctx = AsyncMock()
        mock_ctx.error = AsyncMock()
        
        validation_tests = []
        
        # Test that the test runner tool function exists and can be imported
        try:
            # Just verify the tool exists and is callable
            if callable(test_runner_tool):
                validation_tests.append(('Test runner callable', True, 'Test runner tool is callable'))
            else:
                validation_tests.append(('Test runner callable', False, 'Test runner tool is not callable'))
        except Exception as e:
            validation_tests.append(('Test runner callable', False, f'Unexpected error: {str(e)}'))
        
        # Test that the tool has the expected signature
        try:
            import inspect
            sig = inspect.signature(test_runner_tool)
            expected_params = ['ctx', 'test_type', 'include_performance']
            actual_params = list(sig.parameters.keys())
            
            if all(param in actual_params for param in expected_params):
                validation_tests.append(('Test runner signature', True, 'Test runner has expected parameters'))
            else:
                validation_tests.append(('Test runner signature', False, f'Expected params {expected_params}, got {actual_params}'))
        except Exception as e:
            validation_tests.append(('Test runner signature', False, f'Signature check failed: {str(e)}'))
        
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        all_passed = all(result[1] for result in validation_tests)
        passed_count = sum(1 for result in validation_tests if result[1])
        
        return {
            'test_name': 'Test Runner Validation',
            'status': 'success' if all_passed else 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'details': {
                'validations_tested': len(validation_tests),
                'validations_passed': passed_count,
                'results': validation_tests
            },
            'message': f'✅ All validations passed' if all_passed else f'❌ {len(validation_tests) - passed_count}/{len(validation_tests)} validations failed'
        }
        
    except Exception as e:
        test_end = datetime.now()
        test_duration = (test_end - test_start).total_seconds()
        
        return {
            'test_name': 'Test Runner Validation',
            'status': 'error',  # Fix: Use 'status' instead of 'passed'
            'duration_seconds': test_duration if include_performance else None,
            'error': str(e),
            'message': f'❌ Test runner test failed: {str(e)}'
        }


def generate_test_recommendations(test_results: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on test results."""
    recommendations = []
    
    failed_tests = [test for test in test_results if not test['status'] == 'success']
    
    if not failed_tests:
        recommendations.append("🎉 All tests passed! Your TMF ODA MCP Server is fully operational.")
        recommendations.append("💡 Consider running periodic tests to ensure continued reliability.")
    else:
        recommendations.append(f"⚠️ {len(failed_tests)} test(s) failed. Review the detailed results above.")
        
        if any('Import' in test['test_name'] for test in failed_tests):
            recommendations.append("🔧 Import failures detected. Check Python path and dependencies.")
        
        if any('Validation' in test['test_name'] for test in failed_tests):
            recommendations.append("🔍 Validation failures detected. Review tool parameter handling.")
    
    return recommendations


def generate_next_steps(status: str, test_results: List[Dict[str, Any]]) -> List[str]:
    """Generate next steps based on overall test status."""
    if status == 'success':
        return [
            "✅ All systems operational - ready for production use",
            "📝 You can now use all TMF ODA transformer tools with confidence",
            "🔄 Run this test periodically to ensure continued reliability"
        ]
    elif status == 'partial_success':
        return [
            "⚠️ Some tests failed - investigate specific issues",
            "🔧 Fix failing components before production use",
            "🧪 Re-run tests after applying fixes"
        ]
    else:
        return [
            "❌ Multiple test failures - requires immediate attention",
            "🔍 Review detailed error messages and fix critical issues",
            "🛠️ Consider reinstalling dependencies or checking configuration"
        ]


def calculate_performance_metrics(test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate performance metrics from test results."""
    durations = [test.get('duration_seconds', 0) for test in test_results if test.get('duration_seconds')]
    
    if not durations:
        return {'note': 'No performance data collected'}
    
    return {
        'total_test_duration': sum(durations),
        'average_test_duration': sum(durations) / len(durations),
        'fastest_test': min(durations),
        'slowest_test': max(durations),
        'tests_with_timing': len(durations)
    } 