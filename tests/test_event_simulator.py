#!/usr/bin/env python3
"""
Unit tests for the E-commerce Event Simulator
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.event_simulator.main import EcommerceEventSimulator, EcommerceEvent

class TestEcommerceEvent:
    """Test the EcommerceEvent data class"""
    
    def test_event_creation(self):
        """Test creating an e-commerce event"""
        event = EcommerceEvent(
            event_id="test-123",
            user_id="user-456",
            session_id="session-789",
            event_type="page_view",
            event_timestamp="2023-01-01T12:00:00",
            product_id="PROD001",
            category="Electronics",
            price=799.99,
            quantity=1,
            page_url="https://example.com/product/PROD001",
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1"
        )
        
        assert event.event_id == "test-123"
        assert event.user_id == "user-456"
        assert event.event_type == "page_view"
        assert event.price == 799.99

class TestEcommerceEventSimulator:
    """Test the EcommerceEventSimulator class"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        return {
            'kafka': {
                'bootstrap_servers': 'localhost:9092',
                'topics': {'ecommerce_events': 'ecommerce-events'}
            }
        }
    
    @pytest.fixture
    def mock_producer(self):
        """Mock Kafka producer"""
        producer = Mock()
        producer.send.return_value.get.return_value = Mock(
            topic='ecommerce-events',
            partition=0,
            offset=123
        )
        return producer
    
    @patch('src.event_simulator.main.yaml.safe_load')
    @patch('src.event_simulator.main.KafkaProducer')
    def test_initialization(self, mock_kafka_producer, mock_yaml_load, mock_config):
        """Test simulator initialization"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_producer.return_value = Mock()
        
        simulator = EcommerceEventSimulator()
        
        assert simulator.config == mock_config
        assert len(simulator.products) > 0
        assert 'page_view' in simulator.event_probabilities
        assert 'Electronics' in simulator.categories
    
    @patch('src.event_simulator.main.yaml.safe_load')
    @patch('src.event_simulator.main.KafkaProducer')
    def test_generate_product_catalog(self, mock_kafka_producer, mock_yaml_load, mock_config):
        """Test product catalog generation"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_producer.return_value = Mock()
        
        simulator = EcommerceEventSimulator()
        products = simulator._generate_product_catalog()
        
        assert len(products) > 0
        
        # Check that products have required fields
        for product in products:
            assert 'id' in product
            assert 'name' in product
            assert 'price' in product
            assert 'category' in product
        
        # Check categories
        categories = set(product['category'] for product in products)
        expected_categories = {'Electronics', 'Clothing', 'Books', 'Home', 'Sports'}
        assert categories == expected_categories
    
    @patch('src.event_simulator.main.yaml.safe_load')
    @patch('src.event_simulator.main.KafkaProducer')
    def test_generate_event(self, mock_kafka_producer, mock_yaml_load, mock_config):
        """Test event generation"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_producer.return_value = Mock()
        
        simulator = EcommerceEventSimulator()
        event = simulator._generate_event()
        
        assert isinstance(event, EcommerceEvent)
        assert event.event_id is not None
        assert event.user_id is not None
        assert event.session_id is not None
        assert event.event_type in simulator.event_probabilities.keys()
        assert event.event_timestamp is not None
    
    @patch('src.event_simulator.main.yaml.safe_load')
    @patch('src.event_simulator.main.KafkaProducer')
    def test_publish_event(self, mock_kafka_producer, mock_yaml_load, mock_config, mock_producer):
        """Test event publishing"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_producer.return_value = mock_producer
        
        simulator = EcommerceEventSimulator()
        event = simulator._generate_event()
        
        result = simulator.publish_event(event)
        
        assert result is True
        mock_producer.send.assert_called_once()
    
    @patch('src.event_simulator.main.yaml.safe_load')
    @patch('src.event_simulator.main.KafkaProducer')
    def test_publish_event_failure(self, mock_kafka_producer, mock_yaml_load, mock_config):
        """Test event publishing failure"""
        mock_yaml_load.return_value = mock_config
        mock_producer = Mock()
        mock_producer.send.side_effect = Exception("Kafka error")
        mock_kafka_producer.return_value = mock_producer
        
        simulator = EcommerceEventSimulator()
        event = simulator._generate_event()
        
        result = simulator.publish_event(event)
        
        assert result is False
    
    @patch('src.event_simulator.main.yaml.safe_load')
    @patch('src.event_simulator.main.KafkaProducer')
    def test_cleanup_old_sessions(self, mock_kafka_producer, mock_yaml_load, mock_config):
        """Test session cleanup"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_producer.return_value = Mock()
        
        simulator = EcommerceEventSimulator()
        
        # Add some test sessions
        simulator.active_sessions = {
            'session1': {
                'user_id': 'user1',
                'start_time': datetime.now(),
                'events': []
            },
            'session2': {
                'user_id': 'user2',
                'start_time': datetime.now(),
                'events': []
            }
        }
        
        initial_count = len(simulator.active_sessions)
        simulator._cleanup_old_sessions(max_age_hours=0)  # Force cleanup
        
        # Sessions should be cleaned up
        assert len(simulator.active_sessions) < initial_count
    
    @patch('src.event_simulator.main.yaml.safe_load')
    @patch('src.event_simulator.main.KafkaProducer')
    def test_generate_page_url(self, mock_kafka_producer, mock_yaml_load, mock_config):
        """Test page URL generation"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_producer.return_value = Mock()
        
        simulator = EcommerceEventSimulator()
        
        # Test different event types
        product = {'id': 'PROD001', 'category': 'Electronics'}
        
        page_view_url = simulator._generate_page_url('page_view', product)
        assert '/product/PROD001' in page_view_url
        
        cart_url = simulator._generate_page_url('add_to_cart')
        assert '/cart' in cart_url
        
        checkout_url = simulator._generate_page_url('purchase')
        assert '/checkout' in checkout_url
    
    @patch('src.event_simulator.main.yaml.safe_load')
    @patch('src.event_simulator.main.KafkaProducer')
    def test_event_probabilities(self, mock_kafka_producer, mock_yaml_load, mock_config):
        """Test event probability distribution"""
        mock_yaml_load.return_value = mock_config
        mock_kafka_producer.return_value = Mock()
        
        simulator = EcommerceEventSimulator()
        
        # Generate many events and check distribution
        event_types = []
        for _ in range(1000):
            event = simulator._generate_event()
            event_types.append(event.event_type)
        
        # Check that all expected event types are present
        unique_types = set(event_types)
        expected_types = set(simulator.event_probabilities.keys())
        assert unique_types == expected_types
        
        # Check that page_view is most common (highest probability)
        page_view_count = event_types.count('page_view')
        assert page_view_count > len(event_types) * 0.5  # Should be >50% due to 0.6 probability

if __name__ == "__main__":
    pytest.main([__file__]) 