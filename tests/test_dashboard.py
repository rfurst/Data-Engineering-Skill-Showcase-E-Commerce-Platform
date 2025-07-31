#!/usr/bin/env python3
"""
Unit tests for the E-commerce Analytics Dashboard
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.dashboard.realtime_dashboard import RealtimeDashboard

class TestRealtimeDashboard:
    """Test the RealtimeDashboard class"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        return {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'database': 'ecommerce_analytics',
                'user': 'analytics_user',
                'password': 'analytics_password'
            },
            'dashboard': {
                'port': 5000,
                'host': '0.0.0.0',
                'debug': True
            }
        }
    
    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection"""
        connection = Mock()
        cursor = Mock()
        connection.cursor.return_value = cursor
        return connection
    
    @patch('src.dashboard.realtime_dashboard.yaml.safe_load')
    @patch('src.dashboard.realtime_dashboard.psycopg2.connect')
    def test_initialization(self, mock_psycopg2, mock_yaml_load, mock_config):
        """Test dashboard initialization"""
        mock_yaml_load.return_value = mock_config
        mock_psycopg2.return_value = Mock()
        
        dashboard = RealtimeDashboard()
        
        assert dashboard.config == mock_config
        assert dashboard.metrics_cache is not None
        assert dashboard.update_interval == 5
    
    @patch('src.dashboard.realtime_dashboard.yaml.safe_load')
    @patch('src.dashboard.realtime_dashboard.psycopg2.connect')
    def test_get_realtime_metrics(self, mock_psycopg2, mock_yaml_load, mock_config):
        """Test real-time metrics retrieval"""
        mock_yaml_load.return_value = mock_config
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock database query results
        mock_cursor.fetchone.side_effect = [
            (100,),  # recent_events
            (5000.0,),  # recent_revenue
            (50,),  # unique_users
            [('page_view', 60), ('purchase', 10), ('add_to_cart', 30)],  # event_breakdown
            [('Electronics', 100, 3000.0), ('Clothing', 50, 2000.0)]  # category_performance
        ]
        
        mock_psycopg2.return_value = mock_connection
        
        dashboard = RealtimeDashboard()
        metrics = dashboard.get_realtime_metrics()
        
        assert metrics['recent_events'] == 100
        assert metrics['recent_revenue'] == 5000.0
        assert metrics['unique_users'] == 50
        assert 'page_view' in metrics['event_breakdown']
        assert len(metrics['category_performance']) == 2
    
    @patch('src.dashboard.realtime_dashboard.yaml.safe_load')
    @patch('src.dashboard.realtime_dashboard.psycopg2.connect')
    def test_calculate_conversion_rate(self, mock_psycopg2, mock_yaml_load, mock_config):
        """Test conversion rate calculation"""
        mock_yaml_load.return_value = mock_config
        mock_psycopg2.return_value = Mock()
        
        dashboard = RealtimeDashboard()
        
        # Test with page views and purchases
        event_breakdown = {'page_view': 100, 'purchase': 10}
        conversion_rate = dashboard._calculate_conversion_rate(event_breakdown)
        assert conversion_rate == 10.0  # 10%
        
        # Test with no page views
        event_breakdown = {'purchase': 10}
        conversion_rate = dashboard._calculate_conversion_rate(event_breakdown)
        assert conversion_rate == 0.0
    
    @patch('src.dashboard.realtime_dashboard.yaml.safe_load')
    @patch('src.dashboard.realtime_dashboard.psycopg2.connect')
    def test_get_historical_data(self, mock_psycopg2, mock_yaml_load, mock_config):
        """Test historical data retrieval"""
        mock_yaml_load.return_value = mock_config
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock historical data
        mock_cursor.fetchall.return_value = [
            (datetime(2023, 1, 1, 12, 0), 100, 50, 1000.0),
            (datetime(2023, 1, 1, 13, 0), 150, 75, 1500.0)
        ]
        
        mock_psycopg2.return_value = mock_connection
        
        dashboard = RealtimeDashboard()
        historical_data = dashboard.get_historical_data(hours=24)
        
        assert 'historical_data' in historical_data
        assert len(historical_data['historical_data']) == 2
        assert historical_data['historical_data'][0]['events'] == 100
        assert historical_data['historical_data'][0]['revenue'] == 1000.0
    
    @patch('src.dashboard.realtime_dashboard.yaml.safe_load')
    @patch('src.dashboard.realtime_dashboard.psycopg2.connect')
    def test_error_handling(self, mock_psycopg2, mock_yaml_load, mock_config):
        """Test error handling in dashboard"""
        mock_yaml_load.return_value = mock_config
        mock_psycopg2.side_effect = Exception("Database connection failed")
        
        # Should handle database connection errors gracefully
        with pytest.raises(Exception):
            dashboard = RealtimeDashboard()
    
    @patch('src.dashboard.realtime_dashboard.yaml.safe_load')
    @patch('src.dashboard.realtime_dashboard.psycopg2.connect')
    def test_metrics_cache(self, mock_psycopg2, mock_yaml_load, mock_config):
        """Test metrics caching functionality"""
        mock_yaml_load.return_value = mock_config
        mock_psycopg2.return_value = Mock()
        
        dashboard = RealtimeDashboard()
        
        # Test initial cache state
        assert dashboard.metrics_cache == {}
        
        # Test cache update
        test_metrics = {'recent_events': 100, 'recent_revenue': 5000.0}
        dashboard.metrics_cache = test_metrics
        
        assert dashboard.metrics_cache == test_metrics

if __name__ == "__main__":
    pytest.main([__file__]) 