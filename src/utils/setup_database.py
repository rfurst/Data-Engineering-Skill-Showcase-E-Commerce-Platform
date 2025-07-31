#!/usr/bin/env python3
"""
Database Setup Utility
Sets up PostgreSQL database and initializes tables for e-commerce analytics pipeline
"""

import psycopg2
import logging
import yaml
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseSetup:
    """Database setup utility for e-commerce analytics"""
    
    def __init__(self, config_path: str = "config/database-config.yml"):
        """Initialize database setup"""
        self.config = self._load_config(config_path)
        self.connection = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load database configuration"""
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
                }
            }
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            db_config = self.config['database']
            self.connection = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            self.connection.autocommit = True
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def create_extensions(self):
        """Create necessary PostgreSQL extensions"""
        try:
            cursor = self.connection.cursor()
            
            # Create UUID extension
            cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
            
            logger.info("PostgreSQL extensions created successfully")
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to create extensions: {e}")
            raise
    
    def create_tables(self):
        """Create all necessary tables"""
        try:
            cursor = self.connection.cursor()
            
            # Read and execute the initialization SQL
            init_sql_path = Path(__file__).parent.parent / "utils" / "init.sql"
            
            if init_sql_path.exists():
                with open(init_sql_path, 'r') as file:
                    sql_content = file.read()
                
                # Execute the entire SQL content as one statement
                cursor.execute(sql_content)
                
                logger.info("Database tables created successfully")
            else:
                logger.error(f"SQL initialization file not found: {init_sql_path}")
                raise FileNotFoundError(f"SQL file not found: {init_sql_path}")
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def insert_sample_data(self):
        """Insert sample data for testing"""
        try:
            cursor = self.connection.cursor()
            
            # Insert sample product analytics data
            sample_products = [
                ('PROD001', 'Electronics', 'Smartphone X', 799.99),
                ('PROD002', 'Electronics', 'Laptop Pro', 1299.99),
                ('PROD003', 'Clothing', 'T-Shirt', 29.99),
                ('PROD004', 'Books', 'Data Science Guide', 49.99),
                ('PROD005', 'Home', 'Coffee Maker', 89.99),
                ('PROD006', 'Electronics', 'Wireless Headphones', 199.99),
                ('PROD007', 'Clothing', 'Denim Jeans', 79.99),
                ('PROD008', 'Sports', 'Yoga Mat', 24.99),
                ('PROD009', 'Books', 'Python Programming', 39.99),
                ('PROD010', 'Home', 'Blender', 69.99)
            ]
            
            insert_query = """
            INSERT INTO product_analytics (product_id, category, name, price) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (product_id) DO NOTHING
            """
            
            for product in sample_products:
                cursor.execute(insert_query, product)
            
            logger.info("Sample data inserted successfully")
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to insert sample data: {e}")
            raise
    
    def verify_setup(self):
        """Verify that all tables were created correctly"""
        try:
            cursor = self.connection.cursor()
            
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
            
            missing_tables = [table for table in expected_tables if table not in existing_tables]
            
            if missing_tables:
                logger.error(f"Missing tables: {missing_tables}")
                raise Exception(f"Database setup incomplete. Missing tables: {missing_tables}")
            
            logger.info("Database setup verification completed successfully")
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to verify setup: {e}")
            raise
    
    def setup_database(self):
        """Complete database setup process"""
        logger.info("Starting database setup...")
        
        try:
            # Connect to database
            self.connect()
            
            # Create extensions
            self.create_extensions()
            
            # Create tables
            self.create_tables()
            
            # Insert sample data
            self.insert_sample_data()
            
            # Verify setup
            self.verify_setup()
            
            logger.info("Database setup completed successfully!")
            
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            raise
        finally:
            if self.connection:
                self.connection.close()
                logger.info("Database connection closed")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Setup Utility')
    parser.add_argument('--config', type=str, default='config/database-config.yml',
                       help='Path to database configuration file')
    parser.add_argument('--skip-sample-data', action='store_true',
                       help='Skip inserting sample data')
    
    args = parser.parse_args()
    
    # Create and run database setup
    setup = DatabaseSetup(args.config)
    setup.setup_database()

if __name__ == "__main__":
    main() 