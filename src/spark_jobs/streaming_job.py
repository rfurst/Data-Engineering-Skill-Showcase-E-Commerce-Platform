#!/usr/bin/env python3
"""
Streaming Job for E-commerce Analytics (Portfolio Version)
Processes real-time events from Kafka and performs analytics
Uses pure Python for portfolio demonstration
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import yaml
import psycopg2
from kafka import KafkaConsumer
import pandas as pd
from collections import defaultdict, deque
import threading
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
EVENTS_PROCESSED = Counter('events_processed_total', 'Total events processed')
EVENTS_FAILED = Counter('events_failed_total', 'Total events failed')
PROCESSING_TIME = Histogram('event_processing_seconds', 'Time spent processing events')
BATCH_SIZE = Histogram('batch_size', 'Number of events per batch')
ACTIVE_SESSIONS = Gauge('active_sessions', 'Number of active user sessions')
REVENUE_TOTAL = Gauge('revenue_total', 'Total revenue processed')

class EcommerceStreamingJob:
    """Python-based Streaming job for e-commerce analytics (Portfolio Version)"""
    
    def __init__(self, config_path: str = "config/spark-config.yml"):
        """Initialize the streaming job"""
        self.config = self._load_config(config_path)
        self.consumer = self._create_kafka_consumer()
        self.db_connection = self._create_db_connection()
        self.metrics_buffer = deque(maxlen=1000)  # Store recent metrics
        self.session_data = defaultdict(dict)  # Track user sessions
        
        # Start Prometheus metrics server
        try:
            start_http_server(8000)
            logger.info("Prometheus metrics server started on port 8000")
        except Exception as e:
            logger.warning(f"Failed to start Prometheus server: {e}")
        
        logger.info("E-commerce Streaming Job initialized (Python Version)")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
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
    
    def _create_kafka_consumer(self) -> KafkaConsumer:
        """Create Kafka consumer"""
        kafka_config = self.config['kafka']
        
        consumer = KafkaConsumer(
            'ecommerce-events',  # Fixed: Use correct topic name
            bootstrap_servers=kafka_config['bootstrap_servers'],
            group_id=kafka_config['group_id'],
            auto_offset_reset='earliest',  # Changed to earliest to get all messages
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            key_deserializer=lambda x: x.decode('utf-8') if x else None,
            # Add these configurations to fix connectivity issues
            session_timeout_ms=30000,
            heartbeat_interval_ms=3000,
            max_poll_interval_ms=300000,
            fetch_max_wait_ms=500,
            fetch_min_bytes=1,
            fetch_max_bytes=52428800
        )
        
        logger.info("Kafka consumer created successfully")
        return consumer
    
    def _create_db_connection(self) -> psycopg2.extensions.connection:
        """Create database connection"""
        db_config = self.config['database']
        
        connection = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
        )
        
        logger.info("Database connection established")
        return connection
    
    def _process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enrich a single event"""
        start_time = time.time()
        
        try:
            # Validate required fields
            required_fields = ['event_id', 'user_id', 'session_id', 'event_type', 'event_timestamp']
            for field in required_fields:
                if not event.get(field):
                    logger.warning(f"Missing required field '{field}' in event: {event}")
                    # Generate missing fields if possible
                    if field == 'event_id' and not event.get('event_id'):
                        event['event_id'] = str(uuid.uuid4())
                    elif field == 'user_id' and not event.get('user_id'):
                        event['user_id'] = f"user_{uuid.uuid4().hex[:8]}"
                    elif field == 'session_id' and not event.get('session_id'):
                        event['session_id'] = f"session_{uuid.uuid4().hex[:8]}"
                    elif field == 'event_type' and not event.get('event_type'):
                        event['event_type'] = 'page_view'  # Default event type
                    elif field == 'event_timestamp' and not event.get('event_timestamp'):
                        event['event_timestamp'] = datetime.now().isoformat()
            
            # Add processing timestamp
            event['processed_at'] = datetime.now().isoformat()
            
            # Enrich with session data
            session_id = event.get('session_id')
            if session_id:
                if session_id not in self.session_data:
                    self.session_data[session_id] = {
                        'start_time': event.get('event_timestamp'),
                        'page_views': 0,
                        'cart_additions': 0,
                        'purchases': 0,
                        'total_revenue': 0.0
                    }
                
                # Update session metrics
                session = self.session_data[session_id]
                event_type = event.get('event_type', '')
                
                if event_type == 'page_view':
                    session['page_views'] += 1
                elif event_type == 'add_to_cart':
                    session['cart_additions'] += 1
                elif event_type == 'purchase':
                    session['purchases'] += 1
                    session['total_revenue'] += event.get('price', 0.0)
                
                # Add session metrics to event
                event['session_page_views'] = session['page_views']
                event['session_cart_additions'] = session['cart_additions']
                event['session_purchases'] = session['purchases']
                event['session_revenue'] = session['total_revenue']
            
            # Update metrics
            EVENTS_PROCESSED.inc()
            ACTIVE_SESSIONS.set(len(self.session_data))
            if event.get('price'):
                REVENUE_TOTAL.inc(event.get('price', 0))
            
            return event
            
        except Exception as e:
            EVENTS_FAILED.inc()
            logger.error(f"Error processing event: {e}")
            raise e
        finally:
            PROCESSING_TIME.observe(time.time() - start_time)
    
    def _calculate_realtime_metrics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate real-time metrics from events"""
        if not events:
            return {}
        
        df = pd.DataFrame(events)
        
        # Basic metrics
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_events': len(events),
            'unique_users': df['user_id'].nunique() if 'user_id' in df.columns else 0,
            'unique_sessions': df['session_id'].nunique() if 'session_id' in df.columns else 0,
            'total_revenue': df['price'].sum() if 'price' in df.columns else 0.0,
            'avg_order_value': df[df['event_type'] == 'purchase']['price'].mean() if 'price' in df.columns else 0.0
        }
        
        # Event type breakdown
        if 'event_type' in df.columns:
            event_counts = df['event_type'].value_counts().to_dict()
            metrics.update({
                'page_views': event_counts.get('page_view', 0),
                'cart_additions': event_counts.get('add_to_cart', 0),
                'purchases': event_counts.get('purchase', 0)
            })
        
        # Category breakdown
        if 'category' in df.columns:
            category_revenue = df.groupby('category')['price'].sum().to_dict()
            metrics['category_revenue'] = category_revenue
        
        return metrics
    
    def _save_to_database(self, events: List[Dict[str, Any]], metrics: Dict[str, Any]):
        """Save processed events and metrics to database"""
        try:
            cursor = self.db_connection.cursor()
            
            # Save raw events first
            for event in events:
                # Ensure all required fields are present
                event_id = event.get('event_id')
                if not event_id:
                    logger.warning(f"Skipping event with missing event_id: {event}")
                    continue
                
                cursor.execute("""
                    INSERT INTO raw_events (
                        event_id, user_id, session_id, event_type, event_timestamp,
                        product_id, category, price, quantity, page_url,
                        user_agent, ip_address, raw_data, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event_id,
                    event.get('user_id'),
                    event.get('session_id'),
                    event.get('event_type'),
                    event.get('event_timestamp'),
                    event.get('product_id'),
                    event.get('category'),
                    event.get('price'),
                    event.get('quantity'),
                    event.get('page_url'),
                    event.get('user_agent'),
                    event.get('ip_address'),
                    json.dumps(event.get('raw_data', {})),
                    datetime.now()
                ))
            
            # Save processed events
            for event in events:
                event_id = event.get('event_id')
                if not event_id:
                    continue
                
                cursor.execute("""
                    INSERT INTO processed_events (
                        event_id, user_id, session_id, event_type, event_timestamp,
                        product_id, category, price, quantity, page_url,
                        enriched_data, quality_score, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event_id,
                    event.get('user_id'),
                    event.get('session_id'),
                    event.get('event_type'),
                    event.get('event_timestamp'),
                    event.get('product_id'),
                    event.get('category'),
                    event.get('price'),
                    event.get('quantity'),
                    event.get('page_url'),
                    json.dumps(event.get('enriched_data', {})),
                    0.95,  # Quality score
                    datetime.now()
                ))
            
            # Save real-time metrics
            if metrics:
                cursor.execute("""
                    INSERT INTO realtime_metrics (
                        metric_name, metric_value, metric_count, window_start, window_end, category, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    'total_events',
                    metrics.get('total_events', 0),
                    metrics.get('total_events', 0),
                    datetime.now() - timedelta(seconds=30),
                    datetime.now(),
                    'all',
                    datetime.now()
                ))
                
                # Also save category-specific metrics
                if 'category_revenue' in metrics:
                    for category, revenue in metrics['category_revenue'].items():
                        cursor.execute("""
                            INSERT INTO realtime_metrics (
                                metric_name, metric_value, metric_count, window_start, window_end, category, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            'category_revenue',
                            revenue,
                            1,
                            datetime.now() - timedelta(seconds=30),
                            datetime.now(),
                            category,
                            datetime.now()
                        ))
            
            self.db_connection.commit()
            logger.info(f"Saved {len(events)} events and metrics to database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            self.db_connection.rollback()
            raise
    
    def _detect_anomalies(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in events"""
        anomalies = []
        
        for event in events:
            # Simple anomaly detection examples
            price = event.get('price', 0)
            if price > 10000:  # Suspiciously high price
                anomalies.append({
                    'event_id': event.get('event_id'),
                    'anomaly_type': 'high_price',
                    'value': price,
                    'threshold': 10000,
                    'timestamp': datetime.now().isoformat()
                })
            
            # High frequency events from same user
            user_id = event.get('user_id')
            if user_id:
                user_events = [e for e in events if e.get('user_id') == user_id]
                if len(user_events) > 50:  # More than 50 events in batch
                    anomalies.append({
                        'event_id': event.get('event_id'),
                        'anomaly_type': 'high_frequency_user',
                        'value': len(user_events),
                        'threshold': 50,
                        'timestamp': datetime.now().isoformat()
                    })
        
        return anomalies
    
    def run_streaming_pipeline(self):
        """Run the streaming pipeline"""
        logger.info("Starting streaming pipeline...")
        
        batch_events = []
        last_processing_time = time.time()
        processing_interval = self.config['streaming']['processing_interval']
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            for message in self.consumer:
                try:
                    event = message.value
                    
                    # Process event
                    processed_event = self._process_event(event)
                    batch_events.append(processed_event)
                    
                    # Reset error counter on successful processing
                    consecutive_errors = 0
                    
                    # Check if it's time to process batch
                    current_time = time.time()
                    if (current_time - last_processing_time >= processing_interval and 
                        len(batch_events) > 0):
                        
                        try:
                            # Calculate metrics
                            metrics = self._calculate_realtime_metrics(batch_events)
                            
                            # Detect anomalies
                            anomalies = self._detect_anomalies(batch_events)
                            
                            # Save to database
                            self._save_to_database(batch_events, metrics)
                            
                            # Update batch metrics
                            BATCH_SIZE.observe(len(batch_events))
                            
                            # Log results
                            logger.info(f"Processed batch: {len(batch_events)} events, "
                                      f"{len(anomalies)} anomalies, "
                                      f"Revenue: ${metrics.get('total_revenue', 0):.2f}")
                            
                            # Store metrics for monitoring
                            self.metrics_buffer.append(metrics)
                            
                            # Reset batch
                            batch_events = []
                            last_processing_time = current_time
                            
                        except Exception as batch_error:
                            logger.error(f"Error processing batch: {batch_error}")
                            consecutive_errors += 1
                            
                            if consecutive_errors >= max_consecutive_errors:
                                logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping pipeline")
                                raise batch_error
                            
                            # Continue processing individual events
                            continue
                            
                except Exception as event_error:
                    logger.error(f"Error processing event: {event_error}")
                    consecutive_errors += 1
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping pipeline")
                        raise event_error
                    
                    continue
                
        except KeyboardInterrupt:
            logger.info("Streaming pipeline stopped by user")
        except Exception as e:
            logger.error(f"Error in streaming pipeline: {e}")
            raise
        finally:
            self.consumer.close()
            self.db_connection.close()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of recent metrics"""
        if not self.metrics_buffer:
            return {}
        
        recent_metrics = list(self.metrics_buffer)[-10:]  # Last 10 batches
        
        summary = {
            'total_events_processed': sum(m.get('total_events', 0) for m in recent_metrics),
            'total_revenue': sum(m.get('total_revenue', 0) for m in recent_metrics),
            'avg_events_per_batch': sum(m.get('total_events', 0) for m in recent_metrics) / len(recent_metrics),
            'unique_users': max(m.get('unique_users', 0) for m in recent_metrics),
            'processing_rate': len(recent_metrics) / 5  # batches per 5 minutes
        }
        
        return summary

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='E-commerce Streaming Job')
    parser.add_argument('--mode', choices=['streaming', 'batch'], default='streaming',
                       help='Processing mode')
    parser.add_argument('--config', default='config/spark-config.yml',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    job = EcommerceStreamingJob(args.config)
    
    if args.mode == 'streaming':
        job.run_streaming_pipeline()
    else:
        logger.info("Batch mode not implemented in this version")

if __name__ == "__main__":
    main() 