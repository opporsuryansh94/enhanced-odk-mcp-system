#!/usr/bin/env python3
"""
Migration Status Checker for Enhanced ODK MCP System
Checks the status of database migrations and provides detailed reports
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import psycopg2
import sqlite3
from pathlib import Path
from tabulate import tabulate

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from shared.database_config import DatabaseConfig
except ImportError:
    print("Warning: Could not import DatabaseConfig. Using fallback configuration.")
    DatabaseConfig = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationStatusChecker:
    """Checks and reports database migration status"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize status checker with database configuration"""
        self.config = config or self._get_default_config()
        self.db_type = self.config.get('type', 'postgresql')
        self.connection = None
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default database configuration"""
        if DatabaseConfig:
            db_config = DatabaseConfig()
            return {
                'type': db_config.database_type,
                **db_config.config
            }
        else:
            # Fallback configuration
            return {
                'type': os.getenv('DATABASE_TYPE', 'postgresql'),
                'host': os.getenv('DATABASE_HOST', 'localhost'),
                'port': int(os.getenv('DATABASE_PORT', '5432')),
                'database': os.getenv('DATABASE_NAME', 'odk_mcp_system'),
                'username': os.getenv('DATABASE_USER', 'odk_user'),
                'password': os.getenv('DATABASE_PASSWORD', 'odk_password')
            }
    
    def connect(self):
        """Establish database connection"""
        try:
            if self.db_type == 'postgresql':
                self.connection = psycopg2.connect(
                    host=self.config['host'],
                    port=self.config['port'],
                    database=self.config['database'],
                    user=self.config['username'],
                    password=self.config['password']
                )
                logger.info("Connected to PostgreSQL database")
                
            elif self.db_type == 'sqlite':
                db_path = self.config.get('path', 'odk_mcp_system.db')
                self.connection = sqlite3.connect(db_path)
                self.connection.row_factory = sqlite3.Row
                logger.info(f"Connected to SQLite database: {db_path}")
                
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
                
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def check_migration_table_exists(self) -> bool:
        """Check if migration tracking table exists"""
        cursor = self.connection.cursor()
        
        try:
            if self.db_type == 'postgresql':
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'schema_migrations'
                    );
                """)
            else:  # SQLite
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='schema_migrations';
                """)
            
            result = cursor.fetchone()
            return bool(result[0]) if self.db_type == 'postgresql' else bool(result)
            
        except Exception as e:
            logger.error(f"Error checking migration table: {str(e)}")
            return False
    
    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """Get list of applied migrations"""
        if not self.check_migration_table_exists():
            return []
        
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("""
                SELECT version, description, applied_at, checksum
                FROM schema_migrations
                ORDER BY applied_at
            """)
            
            migrations = []
            for row in cursor.fetchall():
                if self.db_type == 'postgresql':
                    migrations.append({
                        'version': row[0],
                        'description': row[1],
                        'applied_at': row[2],
                        'checksum': row[3]
                    })
                else:  # SQLite
                    migrations.append({
                        'version': row['version'],
                        'description': row['description'],
                        'applied_at': row['applied_at'],
                        'checksum': row['checksum']
                    })
            
            return migrations
            
        except Exception as e:
            logger.error(f"Error getting applied migrations: {str(e)}")
            return []
    
    def get_expected_migrations(self) -> List[Dict[str, str]]:
        """Get list of expected migrations"""
        return [
            {'version': '001_create_organizations', 'description': 'Create organizations table'},
            {'version': '002_create_users', 'description': 'Create users table'},
            {'version': '003_create_projects', 'description': 'Create projects table'},
            {'version': '004_create_forms', 'description': 'Create forms table'},
            {'version': '005_create_submissions', 'description': 'Create submissions table'},
            {'version': '006_create_analytics', 'description': 'Create analytics tables'},
            {'version': '007_create_subscriptions', 'description': 'Create subscription tables'},
            {'version': '008_create_audit_logs', 'description': 'Create audit logging tables'},
            {'version': '009_create_indexes', 'description': 'Create performance indexes'},
            {'version': '010_create_security', 'description': 'Create security and encryption tables'}
        ]
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a specific table exists"""
        cursor = self.connection.cursor()
        
        try:
            if self.db_type == 'postgresql':
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table_name,))
            else:  # SQLite
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?;
                """, (table_name,))
            
            result = cursor.fetchone()
            return bool(result[0]) if self.db_type == 'postgresql' else bool(result)
            
        except Exception as e:
            logger.error(f"Error checking table {table_name}: {str(e)}")
            return False
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get detailed information about a table"""
        if not self.check_table_exists(table_name):
            return {'exists': False}
        
        cursor = self.connection.cursor()
        
        try:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get column information
            if self.db_type == 'postgresql':
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
            else:  # SQLite
                cursor.execute(f"PRAGMA table_info({table_name})")
            
            columns = cursor.fetchall()
            
            return {
                'exists': True,
                'row_count': row_count,
                'column_count': len(columns),
                'columns': columns
            }
            
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {str(e)}")
            return {'exists': True, 'error': str(e)}
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get general database information"""
        cursor = self.connection.cursor()
        
        try:
            if self.db_type == 'postgresql':
                # Get database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size
                """)
                db_size = cursor.fetchone()[0]
                
                # Get table count
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public'
                """)
                table_count = cursor.fetchone()[0]
                
                # Get PostgreSQL version
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                
            else:  # SQLite
                # Get database size
                db_path = self.config.get('path', 'odk_mcp_system.db')
                db_size = f"{os.path.getsize(db_path) / 1024 / 1024:.2f} MB" if os.path.exists(db_path) else "Unknown"
                
                # Get table count
                cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master WHERE type='table'
                """)
                table_count = cursor.fetchone()[0]
                
                # Get SQLite version
                cursor.execute("SELECT sqlite_version()")
                version = f"SQLite {cursor.fetchone()[0]}"
            
            return {
                'type': self.db_type,
                'version': version,
                'size': db_size,
                'table_count': table_count
            }
            
        except Exception as e:
            logger.error(f"Error getting database info: {str(e)}")
            return {'error': str(e)}
    
    def generate_status_report(self, detailed: bool = False) -> str:
        """Generate comprehensive migration status report"""
        report = []
        report.append("=" * 80)
        report.append("ODK MCP SYSTEM - DATABASE MIGRATION STATUS REPORT")
        report.append("=" * 80)
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Database Information
        db_info = self.get_database_info()
        report.append("DATABASE INFORMATION:")
        report.append("-" * 40)
        report.append(f"Type: {db_info.get('type', 'Unknown')}")
        report.append(f"Version: {db_info.get('version', 'Unknown')}")
        report.append(f"Size: {db_info.get('size', 'Unknown')}")
        report.append(f"Tables: {db_info.get('table_count', 'Unknown')}")
        report.append("")
        
        # Migration Status
        report.append("MIGRATION STATUS:")
        report.append("-" * 40)
        
        if not self.check_migration_table_exists():
            report.append("❌ Migration tracking table does not exist")
            report.append("   Run 'python scripts/run_migrations.py' to initialize")
            report.append("")
            return "\n".join(report)
        
        applied_migrations = self.get_applied_migrations()
        expected_migrations = self.get_expected_migrations()
        
        applied_versions = {m['version'] for m in applied_migrations}
        expected_versions = {m['version'] for m in expected_migrations}
        
        # Check migration status
        missing_migrations = expected_versions - applied_versions
        extra_migrations = applied_versions - expected_versions
        
        if not missing_migrations:
            report.append("✅ All expected migrations have been applied")
        else:
            report.append(f"❌ {len(missing_migrations)} migrations are missing:")
            for version in sorted(missing_migrations):
                expected = next(m for m in expected_migrations if m['version'] == version)
                report.append(f"   - {version}: {expected['description']}")
        
        if extra_migrations:
            report.append(f"⚠️  {len(extra_migrations)} unexpected migrations found:")
            for version in sorted(extra_migrations):
                report.append(f"   - {version}")
        
        report.append("")
        
        # Applied Migrations Table
        if applied_migrations:
            report.append("APPLIED MIGRATIONS:")
            report.append("-" * 40)
            
            table_data = []
            for migration in applied_migrations:
                table_data.append([
                    migration['version'],
                    migration['description'][:50] + "..." if len(migration['description']) > 50 else migration['description'],
                    migration['applied_at'].strftime('%Y-%m-%d %H:%M:%S') if migration['applied_at'] else 'Unknown'
                ])
            
            table = tabulate(
                table_data,
                headers=['Version', 'Description', 'Applied At'],
                tablefmt='grid'
            )
            report.append(table)
            report.append("")
        
        # Table Status
        if detailed:
            report.append("TABLE STATUS:")
            report.append("-" * 40)
            
            core_tables = [
                'organizations', 'users', 'projects', 'forms', 'submissions',
                'analytics_reports', 'analytics_cache', 'subscriptions',
                'usage_tracking', 'audit_logs', 'encryption_keys', 'security_sessions'
            ]
            
            table_data = []
            for table_name in core_tables:
                table_info = self.get_table_info(table_name)
                if table_info['exists']:
                    status = "✅ Exists"
                    row_count = table_info.get('row_count', 'Unknown')
                    columns = table_info.get('column_count', 'Unknown')
                else:
                    status = "❌ Missing"
                    row_count = "-"
                    columns = "-"
                
                table_data.append([table_name, status, row_count, columns])
            
            table = tabulate(
                table_data,
                headers=['Table Name', 'Status', 'Rows', 'Columns'],
                tablefmt='grid'
            )
            report.append(table)
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 40)
        
        if missing_migrations:
            report.append("• Run 'python scripts/run_migrations.py' to apply missing migrations")
        
        if not applied_migrations:
            report.append("• Initialize the database by running migrations")
        
        if len(applied_migrations) < len(expected_migrations):
            report.append("• Some core tables may be missing - check table status above")
        
        report.append("• Run 'python scripts/seed_development_data.py' to populate with sample data")
        report.append("• Ensure regular database backups are configured")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)

def main():
    """Main status checker function"""
    parser = argparse.ArgumentParser(description='Check database migration status for ODK MCP System')
    parser.add_argument('--detailed', action='store_true', help='Show detailed table information')
    parser.add_argument('--output', help='Output file for the report')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    try:
        # Initialize status checker
        checker = MigrationStatusChecker()
        
        # Connect to database
        checker.connect()
        
        # Generate status report
        if args.format == 'text':
            report = checker.generate_status_report(detailed=args.detailed)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                logger.info(f"Report saved to: {args.output}")
            else:
                print(report)
        
        elif args.format == 'json':
            import json
            
            # Generate JSON report
            applied_migrations = checker.get_applied_migrations()
            expected_migrations = checker.get_expected_migrations()
            db_info = checker.get_database_info()
            
            json_report = {
                'timestamp': datetime.now().isoformat(),
                'database_info': db_info,
                'migration_table_exists': checker.check_migration_table_exists(),
                'applied_migrations': applied_migrations,
                'expected_migrations': expected_migrations,
                'missing_migrations': list(set(m['version'] for m in expected_migrations) - 
                                          set(m['version'] for m in applied_migrations))
            }
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(json_report, f, indent=2, default=str)
                logger.info(f"JSON report saved to: {args.output}")
            else:
                print(json.dumps(json_report, indent=2, default=str))
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        sys.exit(1)
    
    finally:
        if 'checker' in locals():
            checker.disconnect()

if __name__ == "__main__":
    main()

