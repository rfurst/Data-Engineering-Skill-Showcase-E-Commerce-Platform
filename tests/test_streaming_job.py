#!/usr/bin/env python3
"""
Unit tests for the E-commerce Streaming Job
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.spark_jobs.streaming_job import EcommerceStreamingJob

class TestEcommerceStreamingJob:
    """Test the EcommerceStreamingJob class"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        return {
            'kafka': {
                'bootstrap_servers': 'localhost:9092',
                'topic': 'ecommerce_events',
                'group_id': 'analytics_consumer'
            },
            'database': {
                'host': 'localhost',
                'port': 5432,
                'database': 'ecommerce_analytics',
                'user': 'analytics_user',
                'password': 'analytics_password'
            },
            'streaming': {
                'batch_size': 100,
                'processing_interval': 30
            }
        }
    
    @pytest.fixture
    def mock_consumer(self):
        """Mock Kafka consumer"""
        consumer = Mock()
        consumer.__iter__ = lambda self: iter([])
        return consumer
    
    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection"""
        connection = Mock()
        cursor = Mock()
        connection.cursor.return_value = cursor
        return connection
    
    @patch('src.spark_jobs.streaming_job.yaml.safe_load')
    @patch('src.spark_jobs.streaming_job.KafkaConsumer')
    @patch('src.spark_jobs.streaming_job.psycopg2.connect')
    def test_initialization(self, mock_psycopg2, mock_kafka_consumer, mock_yaml_load, mock_config):
        """Test streaming job initialization"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_consumer.return_value = Mock()
        mock_psycopg2.return_value = Mock()
        
        job = EcommerceStreamingJob()
        
        assert job.config == mock_config
        assert job.metrics_buffer is not None
        assert job.session_data is not None
    
    @patch('src.spark_jobs.streaming_job.yaml.safe_load')
    @patch('src.spark_jobs.streaming_job.KafkaConsumer')
    @patch('src.spark_jobs.streaming_job.psycopg2.connect')
    def test_process_event(self, mock_psycopg2, mock_kafka_consumer, mock_yaml_load, mock_config):
        """Test event processing"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_consumer.return_value = Mock()
        mock_psycopg2.return_value = Mock()
        
        job = EcommerceStreamingJob()
        
        # Test event
        test_event = {
            'event_id': 'test-123',
            'user_id': 'user-456',
            'session_id': 'session-789',
            'event_type': 'page_view',
            'event_timestamp': '2023-01-01T12:00:00',
            'product_id': 'PROD001',
            'category': 'Electronics',
            'price': 799.99
        }
        
        processed_event = job._process_event(test_event)
        
        assert processed_event['processed_at'] is not None
        assert processed_event['session_page_views'] == 1
        assert processed_event['session_cart_additions'] == 0
        assert processed_event['session_purchases'] == 0
    
    @patch('src.spark_jobs.streaming_job.yaml.safe_load')
    @patch('src.spark_jobs.streaming_job.KafkaConsumer')
    @patch('src.spark_jobs.streaming_job.psycopg2.connect')
    def test_process_purchase_event(self, mock_psycopg2, mock_kafka_consumer, mock_yaml_load, mock_config):
        """Test purchase event processing"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_consumer.return_value = Mock()
        mock_psycopg2.return_value = Mock()
        
        job = EcommerceStreamingJob()
        
        # Test purchase event
        test_event = {
            'event_id': 'test-123',
            'user_id': 'user-456',
            'session_id': 'session-789',
            'event_type': 'purchase',
            'event_timestamp': '2023-01-01T12:00:00',
            'product_id': 'PROD001',
            'category': 'Electronics',
            'price': 799.99
        }
        
        processed_event = job._process_event(test_event)
        
        assert processed_event['session_purchases'] == 1
        assert processed_event['session_revenue'] == 799.99
    
    @patch('src.spark_jobs.streaming_job.yaml.safe_load')
    @patch('src.spark_jobs.streaming_job.KafkaConsumer')
    @patch('src.spark_jobs.streaming_job.psycopg2.connect')
    def test_calculate_realtime_metrics(self, mock_psycopg2, mock_kafka_consumer, mock_yaml_load, mock_config):
        """Test real-time metrics calculation"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_consumer.return_value = Mock()
        mock_psycopg2.return_value = Mock()
        
        job = EcommerceStreamingJob()
        
        # Test events
        test_events = [
            {
                'event_id': 'test-1',
                'user_id': 'user-1',
                'session_id': 'session-1',
                'event_type': 'page_view',
                'price': 0
            },
            {
                'event_id': 'test-2',
                'user_id': 'user-2',
                'session_id': 'session-2',
                'event_type': 'purchase',
                'price': 100.0
            }
        ]
        
        metrics = job._calculate_realtime_metrics(test_events)
        
        assert metrics['total_events'] == 2
        assert metrics['unique_users'] == 2
        assert metrics['total_revenue'] == 100.0
        assert metrics['page_views'] == 1
        assert metrics['purchases'] == 1
    
    @patch('src.spark_jobs.streaming_job.yaml.safe_load')
    @patch('src.spark_jobs.streaming_job.KafkaConsumer')
    @patch('src.spark_jobs.streaming_job.psycopg2.connect')
    def test_detect_anomalies(self, mock_psycopg2, mock_kafka_consumer, mock_yaml_load, mock_config):
        """Test anomaly detection"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_consumer.return_value = Mock()
        mock_psycopg2.return_value = Mock()
        
        job = EcommerceStreamingJob()
        
        # Test normal event
        normal_events = [{
            'event_id': 'test-1',
            'user_id': 'user-1',
            'price': 100.0
        }]
        
        anomalies = job._detect_anomalies(normal_events)
        assert len(anomalies) == 0
        
        # Test high price anomaly
        high_price_events = [{
            'event_id': 'test-2',
            'user_id': 'user-2',
            'price': 15000.0  # Above threshold
        }]
        
        anomalies = job._detect_anomalies(high_price_events)
        assert len(anomalies) > 0
        assert any(a['anomaly_type'] == 'high_price' for a in anomalies)
    
    @patch('src.spark_jobs.streaming_job.yaml.safe_load')
    @patch('src.spark_jobs.streaming_job.KafkaConsumer')
    @patch('src.spark_jobs.streaming_job.psycopg2.connect')
    def test_save_to_database(self, mock_psycopg2, mock_kafka_consumer, mock_yaml_load, mock_config):
        """Test database saving"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_consumer.return_value = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_psycopg2.return_value = mock_connection
        
        job = EcommerceStreamingJob()
        
        # Test events
        test_events = [{
            'event_id': 'test-1',
            'user_id': 'user-1',
            'session_id': 'session-1',
            'event_type': 'page_view',
            'event_timestamp': '2023-01-01T12:00:00',
            'product_id': 'PROD001',
            'category': 'Electronics',
            'price': 100.0,
            'quantity': 1,
            'page_url': 'https://example.com',
            'user_agent': 'Mozilla/5.0',
            'ip_address': '192.168.1.1'
        }]
        
        test_metrics = {
            'total_events': 1,
            'total_revenue': 100.0
        }
        
        # Should not raise an exception
        job._save_to_database(test_events, test_metrics)
        
        # Verify database calls were made
        assert mock_cursor.execute.call_count > 0
        mock_connection.commit.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__]) 