"""
Unit tests for manage_performance_metrics.py

Tests all functionality of the PerformanceMetricsManager class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import uuid
import statistics

# Add scripts path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../scripts/capability-scripts'))

from manage_performance_metrics import PerformanceMetricsManager


class TestPerformanceMetricsManager:
    """Test suite for PerformanceMetricsManager."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_dynamodb_table, mock_s3_client, mock_boto3_session):
        """Set up test environment before each test."""
        # Inject mock dynamodb to avoid real AWS calls
        from unittest.mock import Mock
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_dynamodb_table
        self.manager = PerformanceMetricsManager(dynamodb=mock_dynamodb)
        self.manager.table = mock_dynamodb_table
        self.manager.s3_client = mock_s3_client
        self.mock_session = mock_boto3_session
    
    # ==================== Metric Recording Tests ====================
    
    def test_record_latency_metric(self, mock_dynamodb_table):
        """Test recording latency metrics."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        metric_data = {
            'value': 125.5,
            'unit': 'ms',
            'endpoint': '/api/v1/customers',
            'percentile': 'p95'
        }
        
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.record_metric(
            capability_id, component_id, 'latency', metric_data
        )
        
        # Verify
        assert result is True
        mock_dynamodb_table.put_item.assert_called_once()
        
        # Verify the put_item call
        put_call = mock_dynamodb_table.put_item.call_args
        item = put_call.kwargs['Item']
        assert f'CAPABILITY#{capability_id}' in item['PK']
        assert f'METRIC#{component_id}#latency' in item['SK']
    
    def test_record_throughput_metric(self, mock_dynamodb_table):
        """Test recording throughput metrics."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        metric_data = {
            'value': 1000,
            'unit': 'requests/sec',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.record_metric(
            capability_id, component_id, 'throughput', metric_data
        )
        
        # Verify
        assert result is True
    
    def test_record_error_rate_metric(self, mock_dynamodb_table):
        """Test recording error rate metrics."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        metric_data = {
            'value': 0.05,
            'unit': 'percentage',
            'errorCount': 5,
            'totalRequests': 10000
        }
        
        # Setup mock
        mock_dynamodb_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        # Execute
        result = self.manager.record_metric(
            capability_id, component_id, 'error_rate', metric_data
        )
        
        # Verify
        assert result is True
    
    def test_batch_record_metrics(self, mock_dynamodb_table):
        """Test recording multiple metrics in batch."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        metrics = [
            {'type': 'latency', 'value': 45, 'unit': 'ms'},
            {'type': 'throughput', 'value': 500, 'unit': 'rps'},
            {'type': 'cpu', 'value': 65, 'unit': 'percent'}
        ]
        
        # Setup batch writer mock
        batch_writer = MagicMock()
        mock_dynamodb_table.batch_writer.return_value.__enter__ = Mock(return_value=batch_writer)
        mock_dynamodb_table.batch_writer.return_value.__exit__ = Mock()
        
        # Execute
        result = self.manager.batch_record_metrics(capability_id, component_id, metrics)
        
        # Verify
        assert result is True
        mock_dynamodb_table.batch_writer.assert_called()
        assert batch_writer.put_item.call_count == len(metrics)
    
    # ==================== Metric Retrieval Tests ====================
    
    def test_get_metrics_by_type(self, mock_dynamodb_table):
        """Test retrieving metrics by type."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        metric_type = 'latency'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': f'METRIC#{component_id}#{metric_type}#2024-01-01T00:00:00Z',
                    'Value': 45.5,
                    'Unit': 'ms',
                    'Timestamp': '2024-01-01T00:00:00Z'
                },
                {
                    'SK': f'METRIC#{component_id}#{metric_type}#2024-01-01T01:00:00Z',
                    'Value': 48.2,
                    'Unit': 'ms',
                    'Timestamp': '2024-01-01T01:00:00Z'
                }
            ]
        }
        
        # Execute
        metrics = self.manager.get_metrics(capability_id, component_id, metric_type)
        
        # Verify
        assert len(metrics) == 2
        assert metrics[0]['Value'] == 45.5
        assert metrics[1]['Value'] == 48.2
    
    def test_get_metrics_time_range(self, mock_dynamodb_table):
        """Test retrieving metrics within time range."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'Timestamp': (start_time + timedelta(minutes=30)).isoformat(),
                    'Value': 100
                }
            ]
        }
        
        # Execute
        metrics = self.manager.get_metrics_time_range(
            capability_id, component_id, start_time, end_time
        )
        
        # Verify
        assert len(metrics) > 0
    
    def test_get_latest_metrics(self, mock_dynamodb_table):
        """Test getting latest metrics for all types."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'MetricType': 'latency', 'Value': 45, 'Timestamp': datetime.now(timezone.utc).isoformat()},
                {'MetricType': 'throughput', 'Value': 1000, 'Timestamp': datetime.now(timezone.utc).isoformat()},
                {'MetricType': 'error_rate', 'Value': 0.01, 'Timestamp': datetime.now(timezone.utc).isoformat()}
            ]
        }
        
        # Execute
        latest = self.manager.get_latest_metrics(capability_id, component_id)
        
        # Verify
        assert 'latency' in latest
        assert 'throughput' in latest
        assert 'error_rate' in latest
    
    # ==================== Aggregation Tests ====================
    
    def test_aggregate_metrics(self, mock_dynamodb_table):
        """Test aggregating metrics over time period."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock - return multiple metric values
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'Value': 40, 'Timestamp': '2024-01-01T00:00:00Z'},
                {'Value': 45, 'Timestamp': '2024-01-01T00:01:00Z'},
                {'Value': 50, 'Timestamp': '2024-01-01T00:02:00Z'},
                {'Value': 55, 'Timestamp': '2024-01-01T00:03:00Z'},
                {'Value': 60, 'Timestamp': '2024-01-01T00:04:00Z'}
            ]
        }
        
        # Execute
        aggregated = self.manager.aggregate_metrics(
            capability_id, component_id, 'latency', 'average'
        )
        
        # Verify
        assert aggregated is not None
        assert 'average' in aggregated
        assert aggregated['average'] == 50  # (40+45+50+55+60)/5
    
    def test_calculate_percentiles(self, mock_dynamodb_table):
        """Test calculating percentiles for metrics."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock with values for percentile calculation
        values = list(range(1, 101))  # 1 to 100
        mock_dynamodb_table.query.return_value = {
            'Items': [{'Value': v} for v in values]
        }
        
        # Execute
        percentiles = self.manager.calculate_percentiles(
            capability_id, component_id, 'latency', [50, 95, 99]
        )
        
        # Verify
        assert 'p50' in percentiles
        assert 'p95' in percentiles
        assert 'p99' in percentiles
        assert percentiles['p50'] == 50.5  # Median of 1-100
        assert percentiles['p95'] == 95.5
        assert percentiles['p99'] == 99.5
    
    def test_calculate_statistics(self, mock_dynamodb_table):
        """Test calculating statistical metrics."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'Value': 10},
                {'Value': 20},
                {'Value': 30},
                {'Value': 40},
                {'Value': 50}
            ]
        }
        
        # Execute
        stats = self.manager.calculate_statistics(capability_id, component_id, 'latency')
        
        # Verify
        assert stats['mean'] == 30
        assert stats['min'] == 10
        assert stats['max'] == 50
        assert 'stddev' in stats
    
    # ==================== Health Score Tests ====================
    
    def test_calculate_component_health_score(self, mock_dynamodb_table):
        """Test calculating health score from metrics."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock - return good metrics
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'MetricType': 'availability', 'Value': 99.9},
                {'MetricType': 'error_rate', 'Value': 0.1},
                {'MetricType': 'latency', 'Value': 50}
            ]
        }
        
        # Execute
        health_score = self.manager.calculate_health_score(capability_id, component_id)
        
        # Verify
        assert health_score >= 0
        assert health_score <= 100
        assert health_score > 90  # Good metrics should give high score
    
    def test_get_health_status(self, mock_dynamodb_table):
        """Test determining health status from metrics."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'MetricType': 'availability', 'Value': 99.95},
                {'MetricType': 'error_rate', 'Value': 0.05}
            ]
        }
        
        # Execute
        status = self.manager.get_health_status(capability_id, component_id)
        
        # Verify
        assert status in ['healthy', 'degraded', 'unhealthy']
        assert status == 'healthy'  # Good metrics
    
    # ==================== Trend Analysis Tests ====================
    
    def test_analyze_metric_trend(self, mock_dynamodb_table):
        """Test analyzing metric trends."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock - increasing trend
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'Value': 10, 'Timestamp': '2024-01-01T00:00:00Z'},
                {'Value': 20, 'Timestamp': '2024-01-01T01:00:00Z'},
                {'Value': 30, 'Timestamp': '2024-01-01T02:00:00Z'},
                {'Value': 40, 'Timestamp': '2024-01-01T03:00:00Z'}
            ]
        }
        
        # Execute
        trend = self.manager.analyze_trend(capability_id, component_id, 'cpu')
        
        # Verify
        assert trend is not None
        assert trend['direction'] == 'increasing'
        assert 'rate' in trend
    
    def test_detect_anomalies(self, mock_dynamodb_table):
        """Test detecting anomalies in metrics."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        
        # Setup mock - normal values with one anomaly
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'Value': 45, 'Timestamp': '2024-01-01T00:00:00Z'},
                {'Value': 46, 'Timestamp': '2024-01-01T00:01:00Z'},
                {'Value': 200, 'Timestamp': '2024-01-01T00:02:00Z'},  # Anomaly
                {'Value': 44, 'Timestamp': '2024-01-01T00:03:00Z'},
                {'Value': 45, 'Timestamp': '2024-01-01T00:04:00Z'}
            ]
        }
        
        # Execute
        anomalies = self.manager.detect_anomalies(capability_id, component_id, 'latency')
        
        # Verify
        assert anomalies is not None
        assert len(anomalies) > 0
        assert any(a['Value'] == 200 for a in anomalies)
    
    # ==================== Archival Tests ====================
    
    def test_archive_old_metrics(self, mock_dynamodb_table, mock_s3_client):
        """Test archiving old metrics to S3."""
        capability_id = 'CAP-001'
        days_old = 30
        
        # Setup mock - return old metrics
        old_date = datetime.now(timezone.utc) - timedelta(days=days_old + 1)
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {
                    'SK': f'METRIC#COMP-001#latency#{old_date.isoformat()}',
                    'Value': 45,
                    'Timestamp': old_date.isoformat()
                }
            ]
        }
        
        # Setup S3 mock
        mock_s3_client.put_object.return_value = {'ETag': '"test-etag"'}
        
        # Setup batch writer mock for deletion
        batch_writer = MagicMock()
        mock_dynamodb_table.batch_writer.return_value.__enter__ = Mock(return_value=batch_writer)
        mock_dynamodb_table.batch_writer.return_value.__exit__ = Mock()
        
        # Execute
        archived_count = self.manager.archive_old_metrics(capability_id, days_old)
        
        # Verify
        assert archived_count > 0
        mock_s3_client.put_object.assert_called()
        batch_writer.delete_item.assert_called()
    
    def test_restore_archived_metrics(self, mock_s3_client, mock_dynamodb_table):
        """Test restoring metrics from S3 archive."""
        capability_id = 'CAP-001'
        archive_date = '2024-01-01'
        
        # Setup S3 mock
        archived_data = {
            'metrics': [
                {'SK': 'METRIC#COMP-001#latency#2024-01-01T00:00:00Z', 'Value': 45}
            ]
        }
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(archived_data).encode())
        }
        
        # Setup batch writer mock
        batch_writer = MagicMock()
        mock_dynamodb_table.batch_writer.return_value.__enter__ = Mock(return_value=batch_writer)
        mock_dynamodb_table.batch_writer.return_value.__exit__ = Mock()
        
        # Execute
        restored_count = self.manager.restore_archived_metrics(capability_id, archive_date)
        
        # Verify
        assert restored_count > 0
        batch_writer.put_item.assert_called()
    
    # ==================== Alert Tests ====================
    
    def test_check_threshold_alerts(self, mock_dynamodb_table):
        """Test checking metrics against thresholds."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        thresholds = {
            'latency': {'max': 100},
            'error_rate': {'max': 0.01}
        }
        
        # Setup mock - latency exceeds threshold
        mock_dynamodb_table.query.return_value = {
            'Items': [
                {'MetricType': 'latency', 'Value': 150},
                {'MetricType': 'error_rate', 'Value': 0.005}
            ]
        }
        
        # Execute
        alerts = self.manager.check_thresholds(capability_id, component_id, thresholds)
        
        # Verify
        assert len(alerts) == 1
        assert alerts[0]['metric'] == 'latency'
        assert alerts[0]['threshold_exceeded'] is True
    
    # ==================== Error Handling Tests ====================
    
    def test_record_metric_with_invalid_data(self, mock_dynamodb_table):
        """Test recording metric with invalid data."""
        capability_id = 'CAP-001'
        component_id = 'COMP-001'
        invalid_data = {
            # Missing required 'value' field
            'unit': 'ms'
        }
        
        # Execute
        result = self.manager.record_metric(
            capability_id, component_id, 'latency', invalid_data
        )
        
        # Verify
        assert result is False
    
    def test_get_metrics_for_non_existent_component(self, mock_dynamodb_table):
        """Test getting metrics for non-existent component."""
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        metrics = self.manager.get_metrics('CAP-001', 'NON-EXISTENT', 'latency')
        
        assert metrics == []
    
    def test_handle_dynamodb_exception(self, mock_dynamodb_table):
        """Test handling DynamoDB exceptions."""
        # Setup mock to raise exception
        mock_dynamodb_table.put_item.side_effect = Exception("DynamoDB error")
        
        # Execute
        result = self.manager.record_metric(
            'CAP-001', 'COMP-001', 'latency', {'value': 45}
        )
        
        # Verify
        assert result is False
    
    def test_calculate_health_with_no_metrics(self, mock_dynamodb_table):
        """Test health calculation when no metrics available."""
        mock_dynamodb_table.query.return_value = {'Items': []}
        
        health_score = self.manager.calculate_health_score('CAP-001', 'COMP-001')
        
        # Should return neutral score or None
        assert health_score is None or health_score == 50
