#!/usr/bin/env python3
"""
Data Quality Validations using Great Expectations (Portfolio Version)
Validates data quality at various stages of the e-commerce analytics pipeline
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import yaml
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EcommerceDataQualityValidator:
    """Data quality validator for e-commerce analytics pipeline (Portfolio Version)"""
    
    def __init__(self, config_path: str = "config/data-quality-config.yml"):
        """Initialize the data quality validator"""
        self.config = self._load_config(config_path)
        self.db_connection = self._setup_database_connection()
        
        logger.info("E-commerce Data Quality Validator initialized (Portfolio Version)")
    
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
                'validations': {
                    'raw_events': {
                        'enabled': True,
                        'checks': ['completeness', 'uniqueness', 'format']
                    },
                    'processed_events': {
                        'enabled': True,
                        'checks': ['completeness', 'uniqueness', 'format', 'business_rules']
                    },
                    'daily_aggregations': {
                        'enabled': True,
                        'checks': ['completeness', 'accuracy', 'consistency']
                    }
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
            logger.info("Database connection established")
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def _fetch_data_from_table(self, table_name: str, date_filter: str = None) -> pd.DataFrame:
        """Fetch data from PostgreSQL table"""
        try:
            query = f"SELECT * FROM {table_name}"
            if date_filter:
                query += f" WHERE DATE(created_at) = '{date_filter}'"
            
            # Use SQLAlchemy engine for pandas compatibility
            from sqlalchemy import create_engine
            engine = create_engine(
                f"postgresql://{self.config['database']['user']}:{self.config['database']['password']}@"
                f"{self.config['database']['host']}:{self.config['database']['port']}/{self.config['database']['database']}"
            )
            
            df = pd.read_sql_query(query, engine)
            logger.info(f"Fetched {len(df)} records from {table_name}")
            return df
        except Exception as e:
            logger.error(f"Error fetching data from {table_name}: {e}")
            return pd.DataFrame()
    
    def _validate_completeness(self, df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Validate data completeness"""
        results = {
            'check': 'completeness',
            'passed': True,
            'details': {}
        }
        
        if df.empty:
            results['passed'] = False
            results['details']['error'] = 'No data found'
            return results
        
        # Check for null values in critical columns
        critical_columns = {
            'raw_events': ['event_id', 'event_type', 'event_timestamp'],
            'processed_events': ['event_id', 'event_type', 'event_timestamp'],
            'daily_aggregations': ['date', 'event_type']
        }
        
        columns_to_check = critical_columns.get(table_name, df.columns)
        null_counts = {}
        
        for col in columns_to_check:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                null_percentage = (null_count / len(df)) * 100
                null_counts[col] = {
                    'null_count': int(null_count),
                    'null_percentage': float(null_percentage),
                    'acceptable': null_percentage < 5.0  # Less than 5% nulls
                }
                
                if null_percentage >= 5.0:
                    results['passed'] = False
        
        results['details']['null_analysis'] = null_counts
        return results
    
    def _validate_uniqueness(self, df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Validate data uniqueness"""
        results = {
            'check': 'uniqueness',
            'passed': True,
            'details': {}
        }
        
        if df.empty:
            results['passed'] = False
            results['details']['error'] = 'No data found'
            return results
        
        # Check for duplicate event IDs
        if 'event_id' in df.columns:
            duplicate_count = df['event_id'].duplicated().sum()
            duplicate_percentage = (duplicate_count / len(df)) * 100
            
            results['details']['event_id_duplicates'] = {
                'duplicate_count': int(duplicate_count),
                'duplicate_percentage': float(duplicate_percentage),
                'acceptable': duplicate_count == 0
            }
            
            if duplicate_count > 0:
                results['passed'] = False
        
        # Check for duplicate timestamps (within reasonable tolerance)
        if 'event_timestamp' in df.columns:
            df['timestamp_rounded'] = pd.to_datetime(df['event_timestamp']).dt.round('1s')
            timestamp_duplicates = df['timestamp_rounded'].duplicated().sum()
            
            results['details']['timestamp_duplicates'] = {
                'duplicate_count': int(timestamp_duplicates),
                'duplicate_percentage': float((timestamp_duplicates / len(df)) * 100),
                'acceptable': timestamp_duplicates < len(df) * 0.1  # Less than 10%
            }
        
        return results
    
    def _validate_format(self, df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Validate data format"""
        results = {
            'check': 'format',
            'passed': True,
            'details': {}
        }
        
        if df.empty:
            results['passed'] = False
            results['details']['error'] = 'No data found'
            return results
        
        format_issues = {}
        
        # Validate timestamp format
        if 'event_timestamp' in df.columns:
            try:
                pd.to_datetime(df['event_timestamp'])
                format_issues['timestamp'] = {'valid': True}
            except:
                format_issues['timestamp'] = {'valid': False, 'error': 'Invalid timestamp format'}
                results['passed'] = False
        
        # Validate price format (if exists)
        if 'price' in df.columns:
            try:
                prices = pd.to_numeric(df['price'], errors='coerce')
                invalid_prices = prices.isnull().sum()
                negative_prices = (prices < 0).sum()
                
                format_issues['price'] = {
                    'valid': invalid_prices == 0 and negative_prices == 0,
                    'invalid_count': int(invalid_prices),
                    'negative_count': int(negative_prices)
                }
                
                if invalid_prices > 0 or negative_prices > 0:
                    results['passed'] = False
            except:
                format_issues['price'] = {'valid': False, 'error': 'Invalid price format'}
                results['passed'] = False
        
        results['details']['format_analysis'] = format_issues
        return results
    
    def _validate_business_rules(self, df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Validate business rules"""
        results = {
            'check': 'business_rules',
            'passed': True,
            'details': {}
        }
        
        if df.empty:
            results['passed'] = False
            results['details']['error'] = 'No data found'
            return results
        
        rule_violations = {}
        
        # Rule 1: Purchase events should have positive prices
        if 'event_type' in df.columns and 'price' in df.columns:
            purchase_events = df[df['event_type'] == 'purchase']
            if not purchase_events.empty:
                invalid_purchases = purchase_events[purchase_events['price'] <= 0]
                rule_violations['purchase_price_positive'] = {
                    'violations': len(invalid_purchases),
                    'acceptable': len(invalid_purchases) == 0
                }
                
                if len(invalid_purchases) > 0:
                    results['passed'] = False
        
        # Rule 2: Event timestamps should be recent (within last 30 days)
        if 'event_timestamp' in df.columns:
            try:
                timestamps = pd.to_datetime(df['event_timestamp'])
                cutoff_date = datetime.now() - timedelta(days=30)
                old_events = timestamps[timestamps < cutoff_date]
                
                rule_violations['recent_timestamps'] = {
                    'old_events': len(old_events),
                    'acceptable': len(old_events) == 0
                }
                
                if len(old_events) > 0:
                    results['passed'] = False
            except:
                rule_violations['recent_timestamps'] = {'error': 'Invalid timestamp format'}
        
        results['details']['business_rules'] = rule_violations
        return results
    
    def validate_raw_events(self, date_filter: str = None) -> Dict[str, Any]:
        """Validate raw events data"""
        logger.info("Validating raw events data...")
        
        df = self._fetch_data_from_table('raw_events', date_filter)
        
        validation_results = {
            'table': 'raw_events',
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }
        
        # Run completeness check
        completeness_result = self._validate_completeness(df, 'raw_events')
        validation_results['checks'].append(completeness_result)
        
        # Run uniqueness check
        uniqueness_result = self._validate_uniqueness(df, 'raw_events')
        validation_results['checks'].append(uniqueness_result)
        
        # Run format check
        format_result = self._validate_format(df, 'raw_events')
        validation_results['checks'].append(format_result)
        
        # Overall validation result
        validation_results['overall_passed'] = all(check['passed'] for check in validation_results['checks'])
        
        logger.info(f"Raw events validation: {'PASSED' if validation_results['overall_passed'] else 'FAILED'}")
        return validation_results
    
    def validate_processed_events(self, date_filter: str = None) -> Dict[str, Any]:
        """Validate processed events data"""
        logger.info("Validating processed events data...")
        
        df = self._fetch_data_from_table('processed_events', date_filter)
        
        validation_results = {
            'table': 'processed_events',
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }
        
        # Run all checks
        validation_results['checks'].append(self._validate_completeness(df, 'processed_events'))
        validation_results['checks'].append(self._validate_uniqueness(df, 'processed_events'))
        validation_results['checks'].append(self._validate_format(df, 'processed_events'))
        validation_results['checks'].append(self._validate_business_rules(df, 'processed_events'))
        
        # Overall validation result
        validation_results['overall_passed'] = all(check['passed'] for check in validation_results['checks'])
        
        logger.info(f"Processed events validation: {'PASSED' if validation_results['overall_passed'] else 'FAILED'}")
        return validation_results
    
    def validate_daily_aggregations(self, date_filter: str = None) -> Dict[str, Any]:
        """Validate daily aggregations data"""
        logger.info("Validating daily aggregations data...")
        
        df = self._fetch_data_from_table('daily_aggregations', date_filter)
        
        validation_results = {
            'table': 'daily_aggregations',
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }
        
        # Run checks
        validation_results['checks'].append(self._validate_completeness(df, 'daily_aggregations'))
        validation_results['checks'].append(self._validate_uniqueness(df, 'daily_aggregations'))
        validation_results['checks'].append(self._validate_format(df, 'daily_aggregations'))
        
        # Overall validation result
        validation_results['overall_passed'] = all(check['passed'] for check in validation_results['checks'])
        
        logger.info(f"Daily aggregations validation: {'PASSED' if validation_results['overall_passed'] else 'FAILED'}")
        return validation_results
    
    def log_validation_result(self, table_name: str, validation_result: Dict[str, Any]):
        """Log validation results to database"""
        try:
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                INSERT INTO data_quality_logs (
                    validation_name, table_name, validation_result, 
                    error_message, records_checked, records_failed, 
                    validation_timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                f"comprehensive_validation_{table_name}",
                table_name,
                validation_result['overall_passed'],
                str(validation_result) if not validation_result['overall_passed'] else None,
                0,  # records_checked - would need to be calculated
                0,  # records_failed - would need to be calculated
                datetime.now()
            ))
            
            self.db_connection.commit()
            logger.info(f"Validation results logged for {table_name}")
            
        except Exception as e:
            logger.error(f"Error logging validation results: {e}")
            self.db_connection.rollback()
    
    def run_all_validations(self, date_filter: str = None) -> Dict[str, Any]:
        """Run all data quality validations"""
        logger.info("Running comprehensive data quality validations...")
        
        all_results = {
            'timestamp': datetime.now().isoformat(),
            'validations': {}
        }
        
        # Validate each table
        tables_to_validate = ['raw_events', 'processed_events', 'daily_aggregations']
        
        for table in tables_to_validate:
            try:
                if table == 'raw_events':
                    result = self.validate_raw_events(date_filter)
                elif table == 'processed_events':
                    result = self.validate_processed_events(date_filter)
                elif table == 'daily_aggregations':
                    result = self.validate_daily_aggregations(date_filter)
                
                all_results['validations'][table] = result
                self.log_validation_result(table, result)
                
            except Exception as e:
                logger.error(f"Error validating {table}: {e}")
                all_results['validations'][table] = {
                    'error': str(e),
                    'overall_passed': False
                }
        
        # Overall pipeline health
        all_passed = all(
            result.get('overall_passed', False) 
            for result in all_results['validations'].values()
            if 'overall_passed' in result
        )
        
        all_results['pipeline_healthy'] = all_passed
        
        logger.info(f"Data quality validation completed. Pipeline healthy: {all_passed}")
        return all_results
    
    def close(self):
        """Close database connection"""
        if self.db_connection:
            self.db_connection.close()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='E-commerce Data Quality Validations')
    parser.add_argument('--table', choices=['raw_events', 'processed_events', 'daily_aggregations', 'all'],
                       default='all', help='Table to validate')
    parser.add_argument('--date', help='Date filter (YYYY-MM-DD)')
    parser.add_argument('--config', default='config/data-quality-config.yml',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    validator = EcommerceDataQualityValidator(args.config)
    
    try:
        if args.table == 'all':
            results = validator.run_all_validations(args.date)
        elif args.table == 'raw_events':
            results = validator.validate_raw_events(args.date)
        elif args.table == 'processed_events':
            results = validator.validate_processed_events(args.date)
        elif args.table == 'daily_aggregations':
            results = validator.validate_daily_aggregations(args.date)
        
        print(f"\nValidation Results:")
        print(f"Pipeline Healthy: {results.get('pipeline_healthy', results.get('overall_passed', False))}")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
    finally:
        validator.close()

if __name__ == "__main__":
    main() 