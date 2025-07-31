#!/usr/bin/env python3
"""
Quick Start Script for E-commerce Analytics Pipeline
Automates the setup and running of the complete pipeline
"""

import subprocess
import time
import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QuickStart:
    """Quick start utility for the e-commerce analytics pipeline"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.services_started = False
    
    def check_prerequisites(self):
        """Check if required tools are installed"""
        logger.info("Checking prerequisites...")
        
        required_tools = ['docker', 'docker-compose', 'python3']
        
        for tool in required_tools:
            try:
                subprocess.run([tool, '--version'], capture_output=True, check=True)
                logger.info(f"✓ {tool} is installed")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error(f"✗ {tool} is not installed or not in PATH")
                return False
        
        return True
    
    def start_infrastructure(self):
        """Start the infrastructure services using Docker Compose"""
        logger.info("Starting infrastructure services...")
        
        try:
            # Start services in background
            subprocess.run([
                'docker-compose', 'up', '-d'
            ], cwd=self.project_root, check=True)
            
            logger.info("✓ Infrastructure services started")
            self.services_started = True
            
            # Wait for services to be ready
            logger.info("Waiting for services to be ready...")
            time.sleep(30)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start infrastructure: {e}")
            return False
        
        return True
    
    def install_dependencies(self):
        """Install Python dependencies"""
        logger.info("Installing Python dependencies...")
        
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements-minimal.txt'
            ], cwd=self.project_root, check=True)
            
            logger.info("✓ Python dependencies installed")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
    
    def setup_database(self):
        """Setup the database schema and sample data"""
        logger.info("Setting up database...")
        
        try:
            subprocess.run([
                sys.executable, 'src/utils/setup_database.py'
            ], cwd=self.project_root, check=True)
            
            logger.info("✓ Database setup completed")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup database: {e}")
            return False
    
    def start_event_simulator(self):
        """Start the event simulator in background"""
        logger.info("Starting event simulator...")
        
        try:
            # Start simulator in background
            process = subprocess.Popen([
                sys.executable, 'src/event_simulator/main.py',
                '--events-per-second', '5',
                '--duration', '10'  # Run for 10 minutes
            ], cwd=self.project_root)
            
            logger.info("✓ Event simulator started (PID: {})".format(process.pid))
            return process
            
        except Exception as e:
            logger.error(f"Failed to start event simulator: {e}")
            return None
    
    def start_spark_streaming(self):
        """Start the Spark streaming job in background"""
        logger.info("Starting Spark streaming job...")
        
        try:
            # Start streaming job in background
            process = subprocess.Popen([
                sys.executable, 'src/spark_jobs/streaming_job.py',
                '--mode', 'streaming'
            ], cwd=self.project_root)
            
            logger.info("✓ Spark streaming job started (PID: {})".format(process.pid))
            return process
            
        except Exception as e:
            logger.error(f"Failed to start Spark streaming: {e}")
            return None
    
    def start_dashboard(self):
        """Start the real-time dashboard in background"""
        logger.info("Starting real-time dashboard...")
        
        try:
            # Start dashboard in background
            process = subprocess.Popen([
                sys.executable, 'src/dashboard/realtime_dashboard.py',
                '--port', '5000'
            ], cwd=self.project_root)
            
            logger.info("✓ Real-time dashboard started (PID: {})".format(process.pid))
            return process
            
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
            return None
    
    def run_data_quality_checks(self):
        """Run data quality validations"""
        logger.info("Running data quality checks...")
        
        try:
            subprocess.run([
                sys.executable, 'src/data_quality/validations.py',
                '--table', 'all'
            ], cwd=self.project_root, check=True)
            
            logger.info("✓ Data quality checks completed")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Data quality checks failed: {e}")
            return False
    
    def show_status(self):
        """Show the status of all services"""
        logger.info("\n" + "="*50)
        logger.info("E-COMMERCE ANALYTICS PIPELINE STATUS")
        logger.info("="*50)
        
        # Check Docker services
        try:
            result = subprocess.run([
                'docker-compose', 'ps'
            ], cwd=self.project_root, capture_output=True, text=True, check=True)
            
            logger.info("\nDocker Services:")
            logger.info(result.stdout)
            
        except subprocess.CalledProcessError:
            logger.error("Failed to check Docker services")
        
        # Show access URLs
        logger.info("\nAccess URLs:")
        logger.info("• Airflow UI: http://localhost:8080 (admin/admin)")
        logger.info("• Kafka UI: http://localhost:9000")
        logger.info("• Real-time Dashboard: http://localhost:5000")
        logger.info("• PostgreSQL: localhost:5432")
        
        logger.info("\n" + "="*50)
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")
        
        if self.services_started:
            try:
                subprocess.run([
                    'docker-compose', 'down'
                ], cwd=self.project_root, check=True)
                
                logger.info("✓ Infrastructure services stopped")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to stop services: {e}")
    
    def run_demo(self):
        """Run a complete demo of the pipeline"""
        logger.info("Starting E-commerce Analytics Pipeline Demo")
        logger.info("="*50)
        
        try:
            # Check prerequisites
            if not self.check_prerequisites():
                logger.error("Prerequisites check failed. Please install required tools.")
                return False
            
            # Start infrastructure
            if not self.start_infrastructure():
                logger.error("Failed to start infrastructure")
                return False
            
            # Install dependencies
            if not self.install_dependencies():
                logger.error("Failed to install dependencies")
                return False
            
            # Setup database
            if not self.setup_database():
                logger.error("Failed to setup database")
                return False
            
            # Show initial status
            self.show_status()
            
            # Start event simulator
            simulator_process = self.start_event_simulator()
            if not simulator_process:
                logger.error("Failed to start event simulator")
                return False
            
            # Start Spark streaming
            spark_process = self.start_spark_streaming()
            if not spark_process:
                logger.error("Failed to start Spark streaming")
                return False
            
            # Start real-time dashboard
            dashboard_process = self.start_dashboard()
            if not dashboard_process:
                logger.error("Failed to start dashboard")
                return False
            
            # Wait for some data to be generated
            logger.info("Waiting for data generation and processing...")
            time.sleep(60)
            
            # Run data quality checks
            self.run_data_quality_checks()
            
            # Show final status
            self.show_status()
            
            logger.info("\nDemo completed successfully!")
            logger.info("The pipeline is now running. You can:")
            logger.info("1. View real-time data in the Kafka UI")
            logger.info("2. Monitor the pipeline in Airflow")
            logger.info("3. Query analytics data in PostgreSQL")
            logger.info("4. Check data quality reports")
            
            # Keep running for a while
            logger.info("\nPipeline will continue running. Press Ctrl+C to stop...")
            
            try:
                while True:
                    time.sleep(10)
            except KeyboardInterrupt:
                logger.info("\nStopping pipeline...")
            
            return True
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            return False
        
        finally:
            # Cleanup
            self.cleanup()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='E-commerce Analytics Pipeline Quick Start')
    parser.add_argument('--demo', action='store_true',
                       help='Run complete demo')
    parser.add_argument('--start-services', action='store_true',
                       help='Start infrastructure services only')
    parser.add_argument('--stop-services', action='store_true',
                       help='Stop infrastructure services')
    parser.add_argument('--status', action='store_true',
                       help='Show service status')
    
    args = parser.parse_args()
    
    quick_start = QuickStart()
    
    try:
        if args.demo:
            quick_start.run_demo()
        elif args.start_services:
            if quick_start.check_prerequisites() and quick_start.start_infrastructure():
                quick_start.show_status()
        elif args.stop_services:
            quick_start.cleanup()
        elif args.status:
            quick_start.show_status()
        else:
            # Default: run demo
            quick_start.run_demo()
    
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        quick_start.cleanup()
    except Exception as e:
        logger.error(f"Error: {e}")
        quick_start.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main() 