#!/usr/bin/env python3
"""
E-commerce Event Simulator
Generates realistic e-commerce events and publishes them to Kafka
"""

import json
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
from dataclasses import dataclass, asdict
import yaml
from kafka import KafkaProducer
from faker import Faker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class EcommerceEvent:
    """Data class for e-commerce events"""
    event_id: str
    user_id: str
    session_id: str
    event_type: str
    event_timestamp: str
    product_id: str = None
    category: str = None
    price: float = None
    quantity: int = None
    page_url: str = None
    user_agent: str = None
    ip_address: str = None
    raw_data: Dict[str, Any] = None

class EcommerceEventSimulator:
    """Simulates realistic e-commerce events"""
    
    def __init__(self, config_path: str = "config/kafka-config.yml"):
        """Initialize the event simulator"""
        self.fake = Faker()
        self.config = self._load_config(config_path)
        self.producer = self._setup_kafka_producer()
        
        # Product catalog
        self.products = self._generate_product_catalog()
        
        # User sessions
        self.active_sessions = {}
        
        # Event probabilities
        self.event_probabilities = {
            'page_view': 0.6,
            'add_to_cart': 0.2,
            'purchase': 0.1,
            'remove_from_cart': 0.05,
            'wishlist_add': 0.05
        }
        
        # Categories with weights
        self.categories = {
            'Electronics': 0.3,
            'Clothing': 0.25,
            'Books': 0.2,
            'Home': 0.15,
            'Sports': 0.1
        }
        
        logger.info("E-commerce Event Simulator initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {
                'kafka': {
                    'bootstrap_servers': 'localhost:9092',
                    'topics': {'ecommerce_events': 'ecommerce-events'}
                }
            }
    
    def _setup_kafka_producer(self) -> KafkaProducer:
        """Setup Kafka producer"""
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.config['kafka']['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3
            )
            logger.info("Kafka producer setup successful")
            return producer
        except Exception as e:
            logger.error(f"Failed to setup Kafka producer: {e}")
            raise
    
    def _generate_product_catalog(self) -> List[Dict]:
        """Generate a realistic product catalog"""
        products = []
        
        # Electronics
        electronics_products = [
            {'id': 'PROD001', 'name': 'Smartphone X', 'price': 799.99, 'category': 'Electronics'},
            {'id': 'PROD002', 'name': 'Laptop Pro', 'price': 1299.99, 'category': 'Electronics'},
            {'id': 'PROD003', 'name': 'Wireless Headphones', 'price': 199.99, 'category': 'Electronics'},
            {'id': 'PROD004', 'name': 'Smart Watch', 'price': 299.99, 'category': 'Electronics'},
            {'id': 'PROD005', 'name': 'Tablet Air', 'price': 599.99, 'category': 'Electronics'},
        ]
        
        # Clothing
        clothing_products = [
            {'id': 'PROD006', 'name': 'Premium T-Shirt', 'price': 29.99, 'category': 'Clothing'},
            {'id': 'PROD007', 'name': 'Denim Jeans', 'price': 79.99, 'category': 'Clothing'},
            {'id': 'PROD008', 'name': 'Running Shoes', 'price': 119.99, 'category': 'Clothing'},
            {'id': 'PROD009', 'name': 'Winter Jacket', 'price': 149.99, 'category': 'Clothing'},
            {'id': 'PROD010', 'name': 'Summer Dress', 'price': 59.99, 'category': 'Clothing'},
        ]
        
        # Books
        books_products = [
            {'id': 'PROD011', 'name': 'Data Science Guide', 'price': 49.99, 'category': 'Books'},
            {'id': 'PROD012', 'name': 'Python Programming', 'price': 39.99, 'category': 'Books'},
            {'id': 'PROD013', 'name': 'Machine Learning Basics', 'price': 44.99, 'category': 'Books'},
            {'id': 'PROD014', 'name': 'Business Strategy', 'price': 34.99, 'category': 'Books'},
            {'id': 'PROD015', 'name': 'Fiction Novel', 'price': 19.99, 'category': 'Books'},
        ]
        
        # Home
        home_products = [
            {'id': 'PROD016', 'name': 'Coffee Maker', 'price': 89.99, 'category': 'Home'},
            {'id': 'PROD017', 'name': 'Blender', 'price': 69.99, 'category': 'Home'},
            {'id': 'PROD018', 'name': 'Toaster', 'price': 49.99, 'category': 'Home'},
            {'id': 'PROD019', 'name': 'Microwave', 'price': 129.99, 'category': 'Home'},
            {'id': 'PROD020', 'name': 'Air Purifier', 'price': 199.99, 'category': 'Home'},
        ]
        
        # Sports
        sports_products = [
            {'id': 'PROD021', 'name': 'Yoga Mat', 'price': 24.99, 'category': 'Sports'},
            {'id': 'PROD022', 'name': 'Dumbbells Set', 'price': 89.99, 'category': 'Sports'},
            {'id': 'PROD023', 'name': 'Basketball', 'price': 34.99, 'category': 'Sports'},
            {'id': 'PROD024', 'name': 'Tennis Racket', 'price': 79.99, 'category': 'Sports'},
            {'id': 'PROD025', 'name': 'Fitness Tracker', 'price': 149.99, 'category': 'Sports'},
        ]
        
        products.extend(electronics_products + clothing_products + books_products + 
                       home_products + sports_products)
        
        return products
    
    def _generate_user_id(self) -> str:
        """Generate a realistic user ID"""
        return f"user_{self.fake.uuid4()[:8]}"
    
    def _generate_session_id(self) -> str:
        """Generate a session ID"""
        return f"session_{self.fake.uuid4()[:8]}"
    
    def _get_random_product(self) -> Dict:
        """Get a random product from the catalog"""
        return random.choice(self.products)
    
    def _get_random_category(self) -> str:
        """Get a random category based on weights"""
        return random.choices(
            list(self.categories.keys()),
            weights=list(self.categories.values())
        )[0]
    
    def _generate_page_url(self, event_type: str, product: Dict = None) -> str:
        """Generate realistic page URLs"""
        base_url = "https://ecommerce-store.com"
        
        if event_type == 'page_view':
            if product:
                return f"{base_url}/product/{product['id']}"
            else:
                category = self._get_random_category()
                return f"{base_url}/category/{category.lower()}"
        elif event_type == 'add_to_cart':
            return f"{base_url}/cart"
        elif event_type == 'purchase':
            return f"{base_url}/checkout"
        else:
            return f"{base_url}/home"
    
    def _generate_event(self) -> EcommerceEvent:
        """Generate a single e-commerce event"""
        # Determine event type based on probabilities
        event_type = random.choices(
            list(self.event_probabilities.keys()),
            weights=list(self.event_probabilities.values())
        )[0]
        
        # Generate or reuse user and session
        if random.random() < 0.7 and self.active_sessions:  # 70% chance to reuse existing session
            session_id = random.choice(list(self.active_sessions.keys()))
            user_id = self.active_sessions[session_id]['user_id']
        else:
            user_id = self._generate_user_id()
            session_id = self._generate_session_id()
            self.active_sessions[session_id] = {
                'user_id': user_id,
                'start_time': datetime.now(),
                'events': []
            }
        
        # Get product for relevant events
        product = None
        if event_type in ['page_view', 'add_to_cart', 'purchase', 'remove_from_cart', 'wishlist_add']:
            product = self._get_random_product()
        
        # Generate event data with guaranteed required fields
        event = EcommerceEvent(
            event_id=str(uuid.uuid4()),  # Always generate a unique event ID
            user_id=user_id,  # Always present
            session_id=session_id,  # Always present
            event_type=event_type,  # Always present
            event_timestamp=datetime.now().isoformat(),  # Always present
            product_id=product['id'] if product else None,
            category=product['category'] if product else None,
            price=product['price'] if product else None,
            quantity=random.randint(1, 3) if event_type in ['add_to_cart', 'purchase'] else None,
            page_url=self._generate_page_url(event_type, product),
            user_agent=self.fake.user_agent(),
            ip_address=self.fake.ipv4(),
            raw_data={
                'referrer': self.fake.url() if random.random() < 0.3 else None,
                'device_type': random.choice(['desktop', 'mobile', 'tablet']),
                'browser': random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
                'os': random.choice(['Windows', 'macOS', 'Linux', 'iOS', 'Android'])
            }
        )
        
        # Update session tracking
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['events'].append(event_type)
        
        return event
    
    def _cleanup_old_sessions(self, max_age_hours: int = 2):
        """Clean up old sessions"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_sessions = [
            session_id for session_id, session_data in self.active_sessions.items()
            if session_data['start_time'] < cutoff_time
        ]
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
    
    def publish_event(self, event: EcommerceEvent) -> bool:
        """Publish event to Kafka"""
        try:
            # Validate event has required fields
            if not event.event_id or not event.user_id or not event.session_id or not event.event_type:
                logger.error(f"Invalid event missing required fields: {event}")
                return False
            
            topic = self.config['kafka']['topics']['ecommerce_events']
            key = event.user_id
            value = asdict(event)
            
            # Ensure all required fields are present in the serialized data
            if not value.get('event_id'):
                value['event_id'] = event.event_id
            if not value.get('user_id'):
                value['user_id'] = event.user_id
            if not value.get('session_id'):
                value['session_id'] = event.session_id
            if not value.get('event_type'):
                value['event_type'] = event.event_type
            if not value.get('event_timestamp'):
                value['event_timestamp'] = event.event_timestamp
            
            future = self.producer.send(topic, key=key, value=value)
            record_metadata = future.get(timeout=10)
            
            logger.debug(f"Event published to {record_metadata.topic} "
                        f"partition {record_metadata.partition} "
                        f"offset {record_metadata.offset}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    def run(self, events_per_second: int = 10, duration_minutes: int = None):
        """Run the event simulator"""
        logger.info(f"Starting event simulator: {events_per_second} events/sec")
        
        start_time = datetime.now()
        event_count = 0
        
        try:
            while True:
                # Check if we should stop (check at the beginning of each iteration)
                if duration_minutes and (datetime.now() - start_time).total_seconds() > duration_minutes * 60:
                    logger.info("Simulation duration reached, stopping...")
                    break
                
                # Generate and publish events
                for _ in range(events_per_second):
                    # Check duration again before each event
                    if duration_minutes and (datetime.now() - start_time).total_seconds() > duration_minutes * 60:
                        logger.info("Simulation duration reached, stopping...")
                        break
                    
                    event = self._generate_event()
                    if self.publish_event(event):
                        event_count += 1
                    
                    # Add some randomness to event timing
                    time.sleep(random.uniform(0.05, 0.15))
                
                # Cleanup old sessions periodically
                if event_count % 100 == 0:
                    self._cleanup_old_sessions()
                
                # Log progress
                if event_count % 100 == 0:
                    logger.info(f"Published {event_count} events, "
                              f"Active sessions: {len(self.active_sessions)}")
                
                # Wait for next batch (but check duration first)
                if duration_minutes and (datetime.now() - start_time).total_seconds() > duration_minutes * 60:
                    logger.info("Simulation duration reached, stopping...")
                    break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        except Exception as e:
            logger.error(f"Simulation error: {e}")
        finally:
            self.producer.close()
            logger.info(f"Simulation completed. Total events: {event_count}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='E-commerce Event Simulator')
    parser.add_argument('--events-per-second', type=int, default=10,
                       help='Number of events to generate per second')
    parser.add_argument('--duration', type=int, default=None,
                       help='Duration in minutes (None for infinite)')
    parser.add_argument('--config', type=str, default='config/kafka-config.yml',
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Create and run simulator
    simulator = EcommerceEventSimulator(args.config)
    simulator.run(args.events_per_second, args.duration)

if __name__ == "__main__":
    main() 