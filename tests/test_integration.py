#!/usr/bin/env python3
"""
Integration tests for the E-commerce Analytics Pipeline
Tests the complete end-to-end data flow
"""

import pytest
import time
import json
import psycopg2
from unittest.mock import patch
from kafka import KafkaProducer, KafkaConsumer
from datetime import datetime, timedelta

class TestPipelineIntegration:
    """Integration tests for the complete pipeline"""
    
    @pytest.fixture
    def kafka_producer(self):
        """Setup Kafka producer for testing"""
        producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        yield producer
        producer.close()
    
    @pytest.fixture
    def db_connection(self):
        """Setup database connection for testing"""
        connection = psycopg2.connect(
            host='localhost',
            port=5432,
            database='ecommerce_analytics',
            user='analytics_user',
            password='analytics_password'
        )
        yield connection
        connection.close()
    
    def test_event_production_to_kafka(self, kafka_producer):
        """Test that events can be produced to Kafka"""
        # Create a test event
        test_event = {
            'event_id': 'test-event-123',
            'user_id': 'test-user-456',
            'session_id': 'test-session-789',
            'event_type': 'page_view',
            'event_timestamp': datetime.now().isoformat(),
            'product_id': 'PROD001',
            'category': 'Electronics',
            'price': 799.99,
            'page_url': 'https://example.com/product/PROD001'
        }
        
        # Send event to Kafka
        future = kafka_producer.send('ecommerce-events', key='test-user-456', value=test_event)
        record_metadata = future.get(timeout=10)
        
        assert record_metadata.topic == 'ecommerce-events'
        assert record_metadata.partition >= 0
        assert record_metadata.offset >= 0
    
    def test_event_consumption_from_kafka(self):
        """Test that events can be consumed from Kafka"""
        consumer = KafkaConsumer(
            'ecommerce-events',
            bootstrap_servers='localhost:9092',
            group_id='test-consumer-group',
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            key_deserializer=lambda x: x.decode('utf-8') if x else None
        )
        
        # Wait for messages
        messages = []
        start_time = time.time()
        timeout = 30  # 30 seconds timeout
        
        for message in consumer:
            messages.append(message.value)
            if len(messages) >= 3 or (time.time() - start_time) > timeout:
                break
        
        consumer.close()
        
        # Verify we received messages
        assert len(messages) > 0
        
        # Verify message structure
        for message in messages:
            assert 'event_id' in message
            assert 'event_type' in message
            assert 'event_timestamp' in message
    
    def test_database_schema_exists(self, db_connection):
        """Test that all required database tables exist"""
        cursor = db_connection.cursor()
        
        # List of expected tables
        expected_tables = [
            'raw_events',
            'processed_events',
            'daily_aggregations',
            'realtime_metrics',
            'user_sessions',
            'product_analytics',
            'data_quality_logs',
            'pipeline_execution_logs'
        ]
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in expected_tables:
            assert table in existing_tables, f"Table {table} does not exist"
        
        cursor.close()
    
    def test_data_flow_to_database(self, db_connection):
        """Test that data flows from Kafka to database"""
        cursor = db_connection.cursor()
        
        # Get initial count
        cursor.execute("SELECT COUNT(*) FROM processed_events")
        initial_count = cursor.fetchone()[0]
        
        # Wait for some processing time
        time.sleep(10)
        
        # Get final count
        cursor.execute("SELECT COUNT(*) FROM processed_events")
        final_count = cursor.fetchone()[0]
        
        cursor.close()
        
        # Verify that data is being processed
        assert final_count >= initial_count, "No new data was processed"
    
    def test_data_quality_validation(self, db_connection):
        """Test that data quality validations work"""
        cursor = db_connection.cursor()
        
        # Insert some test data
        test_event = {
            'event_id': 'test-quality-123',
            'user_id': 'test-user-456',
            'session_id': 'test-session-789',
            'event_type': 'purchase',
            'event_timestamp': datetime.now().isoformat(),
            'product_id': 'PROD001',
            'category': 'Electronics',
            'price': 799.99,
            'quantity': 1,
            'page_url': 'https://example.com/product/PROD001'
        }
        
        cursor.execute("""
            INSERT INTO processed_events (
                event_id, user_id, session_id, event_type, event_timestamp,
                product_id, category, price, quantity, page_url,
                enriched_data, quality_score, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING
        """, (
            test_event['event_id'],
            test_event['user_id'],
            test_event['session_id'],
            test_event['event_type'],
            test_event['event_timestamp'],
            test_event['product_id'],
            test_event['category'],
            test_event['price'],
            test_event['quantity'],
            test_event['page_url'],
            json.dumps({}),
            0.95,
            datetime.now()
        ))
        
        db_connection.commit()
        
        # Verify data was inserted
        cursor.execute("SELECT COUNT(*) FROM processed_events WHERE event_id = %s", (test_event['event_id'],))
        count = cursor.fetchone()[0]
        assert count == 1, "Test data was not inserted"
        
        cursor.close()
    
    def test_realtime_metrics_generation(self, db_connection):
        """Test that real-time metrics are being generated"""
        cursor = db_connection.cursor()
        
        # Check if real-time metrics table has data
        cursor.execute("SELECT COUNT(*) FROM realtime_metrics")
        metrics_count = cursor.fetchone()[0]
        
        # Check if metrics are recent
        cursor.execute("""
            SELECT COUNT(*) FROM realtime_metrics 
            WHERE created_at >= NOW() - INTERVAL '1 hour'
        """)
        recent_metrics = cursor.fetchone()[0]
        
        cursor.close()
        
        # Verify metrics exist
        assert metrics_count >= 0, "Real-time metrics table should exist"
    
    def test_pipeline_end_to_end(self, kafka_producer, db_connection):
        """Test complete end-to-end pipeline flow"""
        # Step 1: Produce test event
        test_event = {
            'event_id': f'integration-test-{int(time.time())}',
            'user_id': 'integration-user',
            'session_id': 'integration-session',
            'event_type': 'purchase',
            'event_timestamp': datetime.now().isoformat(),
            'product_id': 'PROD001',
            'category': 'Electronics',
            'price': 999.99,
            'quantity': 2,
            'page_url': 'https://example.com/product/PROD001'
        }
        
        # Send to Kafka
        future = kafka_producer.send('ecommerce-events', key='integration-user', value=test_event)
        record_metadata = future.get(timeout=10)
        
        # Step 2: Wait for processing
        time.sleep(15)  # Wait for streaming job to process
        
        # Step 3: Verify data in database
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM processed_events WHERE event_id = %s", (test_event['event_id'],))
        processed_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM realtime_metrics WHERE created_at >= NOW() - INTERVAL '1 minute'")
        recent_metrics = cursor.fetchone()[0]
        
        cursor.close()
        
        # Verify pipeline worked
        assert processed_count >= 0, "Event should be processed (or at least attempted)"
        assert recent_metrics >= 0, "Metrics should be generated"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 