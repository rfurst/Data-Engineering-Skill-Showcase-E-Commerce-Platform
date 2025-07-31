#!/usr/bin/env python3
"""
Performance tests for the E-commerce Analytics Pipeline
"""

import pytest
import time
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from kafka import KafkaProducer
from src.event_simulator.main import EcommerceEventSimulator
from src.spark_jobs.streaming_job import EcommerceStreamingJob

class TestPerformance:
    """Performance tests for the pipeline"""
    
    def test_event_simulator_throughput(self):
        """Test event simulator can generate expected throughput"""
        start_time = time.time()
        
        # Generate 1000 events at 100 events/sec
        simulator = EcommerceEventSimulator()
        events_generated = 0
        
        for _ in range(1000):
            event = simulator._generate_event()
            events_generated += 1
            
            # Simulate processing time
            time.sleep(0.01)
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = events_generated / duration
        
        assert throughput >= 50  # Should handle at least 50 events/sec
        assert events_generated == 1000
    
    def test_kafka_producer_performance(self):
        """Test Kafka producer performance"""
        producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        start_time = time.time()
        futures = []
        
        # Send 1000 messages
        for i in range(1000):
            future = producer.send('ecommerce-events', value={'test': f'message_{i}'})
            futures.append(future)
        
        # Wait for all messages to be sent
        for future in futures:
            future.get(timeout=10)
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = 1000 / duration
        
        producer.close()
        
        assert throughput >= 100  # Should handle at least 100 messages/sec
    
    def test_streaming_job_performance(self):
        """Test streaming job processing performance"""
        # This test would require a running streaming job
        # For now, we'll test the processing logic
        job = EcommerceStreamingJob()
        
        # Create test events
        test_events = []
        for i in range(1000):
            test_events.append({
                'event_id': f'test-{i}',
                'user_id': f'user-{i % 100}',
                'session_id': f'session-{i % 50}',
                'event_type': 'page_view',
                'event_timestamp': '2023-01-01T12:00:00',
                'price': 100.0
            })
        
        start_time = time.time()
        
        # Process events
        processed_events = []
        for event in test_events:
            processed_event = job._process_event(event)
            processed_events.append(processed_event)
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = len(processed_events) / duration
        
        assert throughput >= 1000  # Should process at least 1000 events/sec
        assert len(processed_events) == 1000
    
    def test_concurrent_event_generation(self):
        """Test concurrent event generation"""
        def generate_events(thread_id, num_events):
            simulator = EcommerceEventSimulator()
            events = []
            for i in range(num_events):
                event = simulator._generate_event()
                events.append(event)
            return len(events)
        
        start_time = time.time()
        
        # Generate events using multiple threads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(4):
                future = executor.submit(generate_events, i, 250)
                futures.append(future)
            
            total_events = 0
            for future in as_completed(futures):
                total_events += future.result()
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = total_events / duration
        
        assert total_events == 1000
        assert throughput >= 500  # Should handle at least 500 events/sec with concurrency
    
    def test_database_write_performance(self):
        """Test database write performance"""
        import psycopg2
        
        connection = psycopg2.connect(
            host='localhost',
            port=5432,
            database='ecommerce_analytics',
            user='analytics_user',
            password='analytics_password'
        )
        
        cursor = connection.cursor()
        
        start_time = time.time()
        
        # Insert 1000 test records
        for i in range(1000):
            cursor.execute("""
                INSERT INTO raw_events (
                    event_id, user_id, session_id, event_type, event_timestamp,
                    product_id, category, price, quantity, page_url,
                    user_agent, ip_address, raw_data, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                f'perf-test-{i}',
                f'user-{i}',
                f'session-{i}',
                'page_view',
                '2023-01-01T12:00:00',
                f'PROD{i:03d}',
                'Electronics',
                100.0,
                1,
                'https://example.com',
                'Mozilla/5.0',
                '192.168.1.1',
                json.dumps({'test': True}),
                '2023-01-01T12:00:00'
            ))
        
        connection.commit()
        end_time = time.time()
        duration = end_time - start_time
        throughput = 1000 / duration
        
        cursor.close()
        connection.close()
        
        assert throughput >= 50  # Should handle at least 50 writes/sec
    
    def test_metrics_calculation_performance(self):
        """Test metrics calculation performance"""
        job = EcommerceStreamingJob()
        
        # Create large dataset
        test_events = []
        for i in range(10000):
            test_events.append({
                'event_id': f'test-{i}',
                'user_id': f'user-{i % 1000}',
                'session_id': f'session-{i % 500}',
                'event_type': 'page_view' if i % 3 == 0 else 'purchase',
                'event_timestamp': '2023-01-01T12:00:00',
                'price': 100.0 if i % 3 != 0 else 0.0
            })
        
        start_time = time.time()
        
        # Calculate metrics
        metrics = job._calculate_realtime_metrics(test_events)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 1.0  # Should calculate metrics in under 1 second
        assert metrics['total_events'] == 10000
        assert metrics['unique_users'] == 1000

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 