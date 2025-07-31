#!/usr/bin/env python3
"""
Real-time Dashboard for E-commerce Analytics Pipeline
Provides live metrics and visualizations
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import yaml
import psycopg2
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ecommerce-analytics-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

class RealtimeDashboard:
    """Real-time dashboard for e-commerce analytics"""
    
    def __init__(self, config_path: str = "config/dashboard-config.yml"):
        """Initialize the dashboard"""
        self.config = self._load_config(config_path)
        self.db_connection = self._setup_database_connection()
        self.metrics_cache = {}
        self.update_interval = 5  # seconds
        
        logger.info("Real-time Dashboard initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
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
    
    def _setup_database_connection(self):
        """Setup database connection"""
        try:
            db_config = self.config['database']
            connection = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            logger.info("Database connection established for dashboard")
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def get_realtime_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics from database"""
        try:
            cursor = self.db_connection.cursor()
            
            # Get recent events count
            cursor.execute("""
                SELECT COUNT(*) FROM processed_events 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
            """)
            recent_events = cursor.fetchone()[0]
            
            # Get total revenue in last hour
            cursor.execute("""
                SELECT COALESCE(SUM(price), 0) FROM processed_events 
                WHERE event_type = 'purchase' 
                AND created_at >= NOW() - INTERVAL '1 hour'
            """)
            recent_revenue = cursor.fetchone()[0]
            
            # Get unique users in last hour
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) FROM processed_events 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
            """)
            unique_users = cursor.fetchone()[0]
            
            # Get event type breakdown
            cursor.execute("""
                SELECT event_type, COUNT(*) FROM processed_events 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                GROUP BY event_type
            """)
            event_breakdown = dict(cursor.fetchall())
            
            # Get category performance
            cursor.execute("""
                SELECT category, COUNT(*) as events, COALESCE(SUM(price), 0) as revenue
                FROM processed_events 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                GROUP BY category
                ORDER BY revenue DESC
                LIMIT 5
            """)
            category_performance = []
            for row in cursor.fetchall():
                category_performance.append({
                    'category': row[0],
                    'events': row[1],
                    'revenue': float(row[2])
                })
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'recent_events': recent_events,
                'recent_revenue': float(recent_revenue),
                'unique_users': unique_users,
                'event_breakdown': event_breakdown,
                'category_performance': category_performance,
                'conversion_rate': self._calculate_conversion_rate(event_breakdown)
            }
            
            cursor.close()
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return {}
    
    def _calculate_conversion_rate(self, event_breakdown: Dict[str, int]) -> float:
        """Calculate conversion rate"""
        page_views = event_breakdown.get('page_view', 0)
        purchases = event_breakdown.get('purchase', 0)
        
        if page_views > 0:
            return (purchases / page_views) * 100
        return 0.0
    
    def get_historical_data(self, hours: int = 24) -> Dict[str, Any]:
        """Get historical data for charts"""
        try:
            cursor = self.db_connection.cursor()
            
            # Get hourly metrics for the last N hours
            cursor.execute("""
                SELECT 
                    DATE_TRUNC('hour', created_at) as hour,
                    COUNT(*) as events,
                    COUNT(DISTINCT user_id) as users,
                    COALESCE(SUM(CASE WHEN event_type = 'purchase' THEN price ELSE 0 END), 0) as revenue
                FROM processed_events 
                WHERE created_at >= NOW() - INTERVAL '%s hours'
                GROUP BY DATE_TRUNC('hour', created_at)
                ORDER BY hour
            """, (hours,))
            
            historical_data = []
            for row in cursor.fetchall():
                historical_data.append({
                    'hour': row[0].isoformat(),
                    'events': row[1],
                    'users': row[2],
                    'revenue': float(row[3])
                })
            
            cursor.close()
            return {'historical_data': historical_data}
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return {'historical_data': []}
    
    def start_metrics_updater(self):
        """Start background thread to update metrics"""
        def update_metrics():
            while True:
                try:
                    metrics = self.get_realtime_metrics()
                    self.metrics_cache = metrics
                    socketio.emit('metrics_update', metrics)
                    time.sleep(self.update_interval)
                except Exception as e:
                    logger.error(f"Error updating metrics: {e}")
                    time.sleep(self.update_interval)
        
        thread = threading.Thread(target=update_metrics, daemon=True)
        thread.start()
        logger.info("Metrics updater thread started")

# Create dashboard instance
dashboard = RealtimeDashboard()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/metrics')
def get_metrics():
    """API endpoint for metrics"""
    return jsonify(dashboard.get_realtime_metrics())

@app.route('/api/historical')
def get_historical():
    """API endpoint for historical data"""
    hours = request.args.get('hours', 24, type=int)
    return jsonify(dashboard.get_historical_data(hours))

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info("Client connected to dashboard")
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info("Client disconnected from dashboard")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time E-commerce Analytics Dashboard')
    parser.add_argument('--port', type=int, default=5000, help='Port to run dashboard on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run dashboard on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Start metrics updater
    dashboard.start_metrics_updater()
    
    # Run the dashboard
    logger.info(f"Starting dashboard on {args.host}:{args.port}")
    socketio.run(app, host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main() 