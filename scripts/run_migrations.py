#!/usr/bin/env python3
"""
Database Migration Runner for Enhanced ODK MCP System
Handles database schema creation, updates, and data migrations
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sqlite3
from pathlib import Path

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MigrationRunner:
    """Handles database migrations for the ODK MCP System"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize migration runner with database configuration"""
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
                self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                logger.info("Connected to PostgreSQL database")
                
            elif self.db_type == 'sqlite':
                db_path = self.config.get('path', 'odk_mcp_system.db')
                self.connection = sqlite3.connect(db_path)
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
    
    def create_migration_table(self):
        """Create migrations tracking table"""
        if self.db_type == 'postgresql':
            sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checksum VARCHAR(64)
            );
            """
        else:  # SQLite
            sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checksum TEXT
            );
            """
        
        cursor = self.connection.cursor()
        cursor.execute(sql)
        logger.info("Migration tracking table created/verified")
    
    def run_core_migrations(self):
        """Run core database migrations"""
        logger.info("Starting core database migrations...")
        
        migrations = [
            {
                'version': '001_create_organizations',
                'description': 'Create organizations table',
                'sql': self._get_organizations_schema()
            },
            {
                'version': '002_create_users',
                'description': 'Create users table',
                'sql': self._get_users_schema()
            },
            {
                'version': '003_create_projects',
                'description': 'Create projects table',
                'sql': self._get_projects_schema()
            },
            {
                'version': '004_create_forms',
                'description': 'Create forms table',
                'sql': self._get_forms_schema()
            },
            {
                'version': '005_create_submissions',
                'description': 'Create submissions table',
                'sql': self._get_submissions_schema()
            },
            {
                'version': '006_create_analytics',
                'description': 'Create analytics tables',
                'sql': self._get_analytics_schema()
            },
            {
                'version': '007_create_subscriptions',
                'description': 'Create subscription tables',
                'sql': self._get_subscriptions_schema()
            },
            {
                'version': '008_create_audit_logs',
                'description': 'Create audit logging tables',
                'sql': self._get_audit_schema()
            },
            {
                'version': '009_create_indexes',
                'description': 'Create performance indexes',
                'sql': self._get_indexes_schema()
            },
            {
                'version': '010_create_security',
                'description': 'Create security and encryption tables',
                'sql': self._get_security_schema()
            }
        ]
        
        for migration in migrations:
            self._apply_migration(migration)
        
        logger.info("Core database migrations completed successfully")
    
    def _apply_migration(self, migration: Dict[str, str]):
        """Apply a single migration"""
        version = migration['version']
        
        # Check if migration already applied
        if self._is_migration_applied(version):
            logger.info(f"Migration {version} already applied, skipping")
            return
        
        try:
            cursor = self.connection.cursor()
            
            # Execute migration SQL
            cursor.execute(migration['sql'])
            
            # Record migration
            if self.db_type == 'postgresql':
                cursor.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (%s, %s)",
                    (version, migration['description'])
                )
            else:  # SQLite
                cursor.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                    (version, migration['description'])
                )
            
            logger.info(f"Applied migration: {version} - {migration['description']}")
            
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {str(e)}")
            raise
    
    def _is_migration_applied(self, version: str) -> bool:
        """Check if a migration has been applied"""
        cursor = self.connection.cursor()
        
        if self.db_type == 'postgresql':
            cursor.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (version,))
        else:  # SQLite
            cursor.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,))
        
        return cursor.fetchone() is not None
    
    def _get_organizations_schema(self) -> str:
        """Get organizations table schema"""
        if self.db_type == 'postgresql':
            return """
            CREATE TABLE IF NOT EXISTS organizations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL CHECK (type IN ('ngo', 'academic', 'government', 'corporate', 'startup')),
                description TEXT,
                contact_email VARCHAR(255),
                contact_phone VARCHAR(50),
                address JSONB,
                settings JSONB DEFAULT '{}',
                subscription_tier VARCHAR(50) DEFAULT 'free',
                storage_quota BIGINT DEFAULT 1073741824, -- 1GB
                api_quota INTEGER DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT true
            );
            """
        else:  # SQLite
            return """
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('ngo', 'academic', 'government', 'corporate', 'startup')),
                description TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                address TEXT,
                settings TEXT DEFAULT '{}',
                subscription_tier TEXT DEFAULT 'free',
                storage_quota INTEGER DEFAULT 1073741824,
                api_quota INTEGER DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            );
            """
    
    def _get_users_schema(self) -> str:
        """Get users table schema"""
        if self.db_type == 'postgresql':
            return """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('admin', 'manager', 'analyst', 'user', 'readonly')),
                permissions JSONB DEFAULT '{}',
                last_login TIMESTAMP,
                login_attempts INTEGER DEFAULT 0,
                account_locked_until TIMESTAMP,
                mfa_enabled BOOLEAN DEFAULT false,
                mfa_secret VARCHAR(255),
                api_key VARCHAR(255) UNIQUE,
                preferences JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT true
            );
            """
        else:  # SQLite
            return """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'manager', 'analyst', 'user', 'readonly')),
                permissions TEXT DEFAULT '{}',
                last_login TIMESTAMP,
                login_attempts INTEGER DEFAULT 0,
                account_locked_until TIMESTAMP,
                mfa_enabled BOOLEAN DEFAULT 0,
                mfa_secret TEXT,
                api_key TEXT UNIQUE,
                preferences TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            );
            """
    
    def _get_projects_schema(self) -> str:
        """Get projects table schema"""
        if self.db_type == 'postgresql':
            return """
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
                start_date DATE,
                end_date DATE,
                budget DECIMAL(15,2),
                target_beneficiaries INTEGER,
                location JSONB,
                tags TEXT[],
                settings JSONB DEFAULT '{}',
                created_by UUID REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        else:  # SQLite
            return """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
                start_date DATE,
                end_date DATE,
                budget REAL,
                target_beneficiaries INTEGER,
                location TEXT,
                tags TEXT,
                settings TEXT DEFAULT '{}',
                created_by TEXT REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
    
    def _get_forms_schema(self) -> str:
        """Get forms table schema"""
        if self.db_type == 'postgresql':
            return """
            CREATE TABLE IF NOT EXISTS forms (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                version INTEGER DEFAULT 1,
                xlsform_content JSONB,
                xml_content TEXT,
                status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'archived')),
                submission_count INTEGER DEFAULT 0,
                settings JSONB DEFAULT '{}',
                created_by UUID REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        else:  # SQLite
            return """
            CREATE TABLE IF NOT EXISTS forms (
                id TEXT PRIMARY KEY,
                project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                version INTEGER DEFAULT 1,
                xlsform_content TEXT,
                xml_content TEXT,
                status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'archived')),
                submission_count INTEGER DEFAULT 0,
                settings TEXT DEFAULT '{}',
                created_by TEXT REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
    
    def _get_submissions_schema(self) -> str:
        """Get submissions table schema"""
        if self.db_type == 'postgresql':
            return """
            CREATE TABLE IF NOT EXISTS submissions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                form_id UUID REFERENCES forms(id) ON DELETE CASCADE,
                data JSONB NOT NULL,
                metadata JSONB DEFAULT '{}',
                location POINT,
                submitted_by UUID REFERENCES users(id),
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                device_info JSONB,
                sync_status VARCHAR(50) DEFAULT 'synced' CHECK (sync_status IN ('pending', 'synced', 'conflict')),
                validation_status VARCHAR(50) DEFAULT 'valid' CHECK (validation_status IN ('valid', 'invalid', 'pending')),
                validation_errors JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        else:  # SQLite
            return """
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                form_id TEXT REFERENCES forms(id) ON DELETE CASCADE,
                data TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                location TEXT,
                submitted_by TEXT REFERENCES users(id),
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                device_info TEXT,
                sync_status TEXT DEFAULT 'synced' CHECK (sync_status IN ('pending', 'synced', 'conflict')),
                validation_status TEXT DEFAULT 'valid' CHECK (validation_status IN ('valid', 'invalid', 'pending')),
                validation_errors TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
    
    def _get_analytics_schema(self) -> str:
        """Get analytics tables schema"""
        if self.db_type == 'postgresql':
            return """
            CREATE TABLE IF NOT EXISTS analytics_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                project_ids UUID[],
                report_type VARCHAR(100) NOT NULL,
                parameters JSONB DEFAULT '{}',
                results JSONB,
                status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
                created_by UUID REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS analytics_cache (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                cache_key VARCHAR(255) UNIQUE NOT NULL,
                data JSONB NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        else:  # SQLite
            return """
            CREATE TABLE IF NOT EXISTS analytics_reports (
                id TEXT PRIMARY KEY,
                organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
                project_ids TEXT,
                report_type TEXT NOT NULL,
                parameters TEXT DEFAULT '{}',
                results TEXT,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
                created_by TEXT REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS analytics_cache (
                id TEXT PRIMARY KEY,
                cache_key TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
    
    def _get_subscriptions_schema(self) -> str:
        """Get subscription tables schema"""
        if self.db_type == 'postgresql':
            return """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                plan_name VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired', 'suspended')),
                billing_cycle VARCHAR(20) DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly', 'yearly')),
                amount DECIMAL(10,2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD',
                payment_method JSONB,
                next_billing_date DATE,
                trial_ends_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS usage_tracking (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                metric_name VARCHAR(100) NOT NULL,
                metric_value INTEGER NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        else:  # SQLite
            return """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
                plan_name TEXT NOT NULL,
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired', 'suspended')),
                billing_cycle TEXT DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly', 'yearly')),
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                payment_method TEXT,
                next_billing_date DATE,
                trial_ends_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS usage_tracking (
                id TEXT PRIMARY KEY,
                organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
                metric_name TEXT NOT NULL,
                metric_value INTEGER NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
    
    def _get_audit_schema(self) -> str:
        """Get audit logging tables schema"""
        if self.db_type == 'postgresql':
            return """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(100),
                resource_id UUID,
                old_values JSONB,
                new_values JSONB,
                ip_address INET,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        else:  # SQLite
            return """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
                user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                old_values TEXT,
                new_values TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
    
    def _get_indexes_schema(self) -> str:
        """Get performance indexes"""
        if self.db_type == 'postgresql':
            return """
            -- User indexes
            CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);
            
            -- Project indexes
            CREATE INDEX IF NOT EXISTS idx_projects_organization_id ON projects(organization_id);
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
            
            -- Form indexes
            CREATE INDEX IF NOT EXISTS idx_forms_project_id ON forms(project_id);
            CREATE INDEX IF NOT EXISTS idx_forms_status ON forms(status);
            
            -- Submission indexes
            CREATE INDEX IF NOT EXISTS idx_submissions_form_id ON submissions(form_id);
            CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at ON submissions(submitted_at);
            CREATE INDEX IF NOT EXISTS idx_submissions_location ON submissions USING GIST(location);
            
            -- Analytics indexes
            CREATE INDEX IF NOT EXISTS idx_analytics_reports_organization_id ON analytics_reports(organization_id);
            CREATE INDEX IF NOT EXISTS idx_analytics_cache_key ON analytics_cache(cache_key);
            CREATE INDEX IF NOT EXISTS idx_analytics_cache_expires ON analytics_cache(expires_at);
            
            -- Audit indexes
            CREATE INDEX IF NOT EXISTS idx_audit_logs_organization_id ON audit_logs(organization_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
            """
        else:  # SQLite
            return """
            -- User indexes
            CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);
            
            -- Project indexes
            CREATE INDEX IF NOT EXISTS idx_projects_organization_id ON projects(organization_id);
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
            
            -- Form indexes
            CREATE INDEX IF NOT EXISTS idx_forms_project_id ON forms(project_id);
            CREATE INDEX IF NOT EXISTS idx_forms_status ON forms(status);
            
            -- Submission indexes
            CREATE INDEX IF NOT EXISTS idx_submissions_form_id ON submissions(form_id);
            CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at ON submissions(submitted_at);
            
            -- Analytics indexes
            CREATE INDEX IF NOT EXISTS idx_analytics_reports_organization_id ON analytics_reports(organization_id);
            CREATE INDEX IF NOT EXISTS idx_analytics_cache_key ON analytics_cache(cache_key);
            CREATE INDEX IF NOT EXISTS idx_analytics_cache_expires ON analytics_cache(expires_at);
            
            -- Audit indexes
            CREATE INDEX IF NOT EXISTS idx_audit_logs_organization_id ON audit_logs(organization_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
            """
    
    def _get_security_schema(self) -> str:
        """Get security and encryption tables schema"""
        if self.db_type == 'postgresql':
            return """
            CREATE TABLE IF NOT EXISTS encryption_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                key_name VARCHAR(100) NOT NULL,
                key_value TEXT NOT NULL,
                algorithm VARCHAR(50) DEFAULT 'AES-256',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                UNIQUE(organization_id, key_name)
            );
            
            CREATE TABLE IF NOT EXISTS security_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                ip_address INET,
                user_agent TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        else:  # SQLite
            return """
            CREATE TABLE IF NOT EXISTS encryption_keys (
                id TEXT PRIMARY KEY,
                organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
                key_name TEXT NOT NULL,
                key_value TEXT NOT NULL,
                algorithm TEXT DEFAULT 'AES-256',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(organization_id, key_name)
            );
            
            CREATE TABLE IF NOT EXISTS security_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                session_token TEXT UNIQUE NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """

def main():
    """Main migration runner function"""
    parser = argparse.ArgumentParser(description='Run database migrations for ODK MCP System')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without applying')
    parser.add_argument('--force', action='store_true', help='Force migration even if already applied')
    
    args = parser.parse_args()
    
    try:
        # Initialize migration runner
        runner = MigrationRunner()
        
        # Connect to database
        runner.connect()
        
        # Create migration tracking table
        runner.create_migration_table()
        
        # Run core migrations
        if args.dry_run:
            logger.info("DRY RUN: Would apply core database migrations")
        else:
            runner.run_core_migrations()
            logger.info("All migrations completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)
    
    finally:
        if 'runner' in locals():
            runner.disconnect()

if __name__ == "__main__":
    main()

