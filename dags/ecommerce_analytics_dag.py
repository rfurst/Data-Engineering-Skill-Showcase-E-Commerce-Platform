"""
E-commerce Analytics DAG
Daily ETL pipeline for e-commerce analytics using Apache Airflow
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago
import logging
import pandas as pd
import json
from typing import Dict, Any

# Default arguments for the DAG
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'ecommerce_analytics_pipeline',
    default_args=default_args,
    description='Daily ETL pipeline for e-commerce analytics',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    catchup=False,
    tags=['ecommerce', 'analytics', 'etl'],
)

def extract_events_from_kafka(**context):
    """Extract events from Kafka for the previous day"""
    execution_date = context['execution_date']
    target_date = (execution_date - timedelta(days=1)).strftime('%Y-%m-%d')
    
    logging.info(f"Extracting events for date: {target_date}")
    
    # This would typically use Kafka consumer to extract data
    # For now, we'll simulate the extraction
    logging.info("Event extraction completed")
    
    return target_date

def transform_events(**context):
    """Transform and clean the extracted events"""
    target_date = context['task_instance'].xcom_pull(task_ids='extract_events')
    
    logging.info(f"Transforming events for date: {target_date}")
    
    # Simulate data transformation
    # In a real implementation, this would use Spark or pandas for transformation
    
    # Sample transformation logic
    transformed_data = {
        'date': target_date,
        'total_events': 1000,
        'total_revenue': 50000.0,
        'unique_users': 500,
        'unique_sessions': 750
    }
    
    logging.info("Event transformation completed")
    return transformed_data

def load_to_data_warehouse(**context):
    """Load transformed data to PostgreSQL data warehouse"""
    transformed_data = context['task_instance'].xcom_pull(task_ids='transform_events')
    
    logging.info("Loading data to data warehouse")
    
    # Connect to PostgreSQL
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Insert daily aggregations
    insert_query = """
    INSERT INTO daily_aggregations (
        date, event_type, total_events, total_revenue, 
        unique_users, unique_sessions, created_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, NOW()
    )
    ON CONFLICT (date, category, event_type) 
    DO UPDATE SET 
        total_events = EXCLUDED.total_events,
        total_revenue = EXCLUDED.total_revenue,
        unique_users = EXCLUDED.unique_users,
        unique_sessions = EXCLUDED.unique_sessions,
        updated_at = NOW()
    """
    
    # Insert sample data for different event types
    event_types = ['page_view', 'add_to_cart', 'purchase']
    for event_type in event_types:
        pg_hook.run(insert_query, parameters=(
            transformed_data['date'],
            event_type,
            transformed_data['total_events'] // 3,  # Distribute across event types
            transformed_data['total_revenue'] if event_type == 'purchase' else 0,
            transformed_data['unique_users'],
            transformed_data['unique_sessions']
        ))
    
    logging.info("Data loading completed")

def run_data_quality_checks(**context):
    """Run data quality checks using Great Expectations"""
    target_date = context['task_instance'].xcom_pull(task_ids='extract_events')
    
    logging.info(f"Running data quality checks for date: {target_date}")
    
    # Connect to PostgreSQL
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Sample data quality checks
    checks = [
        {
            'name': 'check_daily_aggregations_not_empty',
            'query': "SELECT COUNT(*) FROM daily_aggregations WHERE date = %s",
            'expected_min': 1
        },
        {
            'name': 'check_revenue_not_negative',
            'query': "SELECT COUNT(*) FROM daily_aggregations WHERE date = %s AND total_revenue < 0",
            'expected_max': 0
        },
        {
            'name': 'check_unique_users_positive',
            'query': "SELECT COUNT(*) FROM daily_aggregations WHERE date = %s AND unique_users <= 0",
            'expected_max': 0
        }
    ]
    
    failed_checks = []
    
    for check in checks:
        result = pg_hook.get_first(check['query'], parameters=(target_date,))
        count = result[0] if result else 0
        
        if 'expected_min' in check and count < check['expected_min']:
            failed_checks.append(f"{check['name']}: Expected min {check['expected_min']}, got {count}")
        elif 'expected_max' in check and count > check['expected_max']:
            failed_checks.append(f"{check['name']}: Expected max {check['expected_max']}, got {count}")
    
    if failed_checks:
        raise Exception(f"Data quality checks failed: {', '.join(failed_checks)}")
    
    logging.info("Data quality checks passed")

def generate_analytics_report(**context):
    """Generate daily analytics report"""
    target_date = context['task_instance'].xcom_pull(task_ids='extract_events')
    
    logging.info(f"Generating analytics report for date: {target_date}")
    
    # Connect to PostgreSQL
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Generate daily summary
    summary_query = """
    SELECT 
        date,
        SUM(CASE WHEN event_type = 'page_view' THEN total_events ELSE 0 END) as page_views,
        SUM(CASE WHEN event_type = 'add_to_cart' THEN total_events ELSE 0 END) as cart_additions,
        SUM(CASE WHEN event_type = 'purchase' THEN total_events ELSE 0 END) as purchases,
        SUM(total_revenue) as total_revenue,
        SUM(unique_users) as unique_users,
        SUM(unique_sessions) as unique_sessions
    FROM daily_aggregations 
    WHERE date = %s
    GROUP BY date
    """
    
    result = pg_hook.get_first(summary_query, parameters=(target_date,))
    
    if result:
        report = {
            'date': result[0],
            'page_views': result[1],
            'cart_additions': result[2],
            'purchases': result[3],
            'total_revenue': float(result[4]) if result[4] else 0,
            'unique_users': result[5],
            'unique_sessions': result[6],
            'conversion_rate': (result[3] / result[1] * 100) if result[1] > 0 else 0
        }
        
        logging.info(f"Daily Report: {json.dumps(report, indent=2)}")
    
    logging.info("Analytics report generated")

def cleanup_old_data(**context):
    """Clean up old data to maintain storage efficiency"""
    logging.info("Cleaning up old data")
    
    # Connect to PostgreSQL
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Delete data older than 90 days
    cleanup_query = """
    DELETE FROM daily_aggregations 
    WHERE date < CURRENT_DATE - INTERVAL '90 days'
    """
    
    pg_hook.run(cleanup_query)
    
    logging.info("Data cleanup completed")

# Define tasks
extract_task = PythonOperator(
    task_id='extract_events',
    python_callable=extract_events_from_kafka,
    dag=dag,
)

transform_task = PythonOperator(
    task_id='transform_events',
    python_callable=transform_events,
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_to_data_warehouse',
    python_callable=load_to_data_warehouse,
    dag=dag,
)

quality_check_task = PythonOperator(
    task_id='run_data_quality_checks',
    python_callable=run_data_quality_checks,
    dag=dag,
)

report_task = PythonOperator(
    task_id='generate_analytics_report',
    python_callable=generate_analytics_report,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_old_data',
    python_callable=cleanup_old_data,
    dag=dag,
)

# Define task dependencies
extract_task >> transform_task >> load_task >> quality_check_task >> report_task
load_task >> cleanup_task

# Additional tasks for specific analytics

def calculate_category_metrics(**context):
    """Calculate category-specific metrics"""
    target_date = context['task_instance'].xcom_pull(task_ids='extract_events')
    
    logging.info(f"Calculating category metrics for date: {target_date}")
    
    # This would typically aggregate data by category
    # For now, we'll simulate the calculation
    
    logging.info("Category metrics calculated")

category_metrics_task = PythonOperator(
    task_id='calculate_category_metrics',
    python_callable=calculate_category_metrics,
    dag=dag,
)

def calculate_user_metrics(**context):
    """Calculate user-specific metrics"""
    target_date = context['task_instance'].xcom_pull(task_ids='extract_events')
    
    logging.info(f"Calculating user metrics for date: {target_date}")
    
    # This would typically calculate user behavior metrics
    # For now, we'll simulate the calculation
    
    logging.info("User metrics calculated")

user_metrics_task = PythonOperator(
    task_id='calculate_user_metrics',
    python_callable=calculate_user_metrics,
    dag=dag,
)

# Add parallel tasks
load_task >> [category_metrics_task, user_metrics_task] >> quality_check_task

# Create tables if they don't exist
create_tables_task = PostgresOperator(
    task_id='create_tables',
    postgres_conn_id='postgres_default',
    sql="""
    -- This would create the necessary tables if they don't exist
    -- For now, we'll assume they're already created
    SELECT 1;
    """,
    dag=dag,
)

# Add table creation as a dependency
create_tables_task >> extract_task 