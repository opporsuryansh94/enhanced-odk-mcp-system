"""
Production PostgreSQL Setup and Configuration
Enterprise-grade database setup with security, performance, and scalability
"""

import os
import sys
import logging
import psycopg2
import hashlib
import secrets
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import subprocess
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionPostgreSQLSetup:
    """
    Enterprise-grade PostgreSQL setup with security and performance optimizations
    """
    
    def __init__(self, config=None):
        self.config = config or self.load_default_config()
        self.encryption_key = self.generate_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
    def load_default_config(self):
        """Load default production configuration"""
        return {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'odk_mcp_production'),
            'username': os.getenv('POSTGRES_USER', 'odk_admin'),
            'password': os.getenv('POSTGRES_PASSWORD', self.generate_secure_password()),
            'ssl_mode': 'require',
            'connection_pool_size': 20,
            'max_overflow': 30,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'enable_row_level_security': True,
            'enable_audit_logging': True,
            'backup_retention_days': 30,
            'encryption_enabled': True
        }
    
    def generate_secure_password(self, length=32):
        """Generate cryptographically secure password"""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_encryption_key(self):
        """Generate encryption key for field-level encryption"""
        key_file = os.getenv('ENCRYPTION_KEY_PATH', '/home/ubuntu/enterprise-system/config/encryption.key')
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Read-only for owner
            return key
    
    def create_database_structure(self):
        """Create production database structure with security"""
        
        # Database creation script
        db_script = f"""
        -- Create production database
        CREATE DATABASE {self.config['database']} 
        WITH 
            ENCODING = 'UTF8'
            LC_COLLATE = 'en_US.UTF-8'
            LC_CTYPE = 'en_US.UTF-8'
            TEMPLATE = template0;
        
        -- Connect to the new database
        \\c {self.config['database']};
        
        -- Enable required extensions
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
        CREATE EXTENSION IF NOT EXISTS "pg_trgm";
        CREATE EXTENSION IF NOT EXISTS "btree_gin";
        CREATE EXTENSION IF NOT EXISTS "btree_gist";
        
        -- Create schemas for multi-tenancy
        CREATE SCHEMA IF NOT EXISTS tenant_data;
        CREATE SCHEMA IF NOT EXISTS system_data;
        CREATE SCHEMA IF NOT EXISTS audit_logs;
        CREATE SCHEMA IF NOT EXISTS analytics;
        
        -- Create roles and users
        CREATE ROLE odk_admin_role;
        CREATE ROLE odk_user_role;
        CREATE ROLE odk_readonly_role;
        CREATE ROLE odk_analytics_role;
        
        -- Grant schema permissions
        GRANT ALL PRIVILEGES ON SCHEMA tenant_data TO odk_admin_role;
        GRANT USAGE, CREATE ON SCHEMA tenant_data TO odk_user_role;
        GRANT USAGE ON SCHEMA tenant_data TO odk_readonly_role;
        GRANT USAGE ON SCHEMA analytics TO odk_analytics_role;
        
        -- Create admin user
        CREATE USER {self.config['username']} WITH 
            PASSWORD '{self.config['password']}'
            CREATEDB
            CREATEROLE
            REPLICATION;
        
        GRANT odk_admin_role TO {self.config['username']};
        
        -- Enable row level security globally
        ALTER DATABASE {self.config['database']} SET row_security = on;
        """
        
        return db_script
    
    def create_tenant_isolation_tables(self):
        """Create tables for tenant isolation and security"""
        
        tables_script = """
        -- Organizations table (tenant management)
        CREATE TABLE IF NOT EXISTS system_data.organizations (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            domain VARCHAR(255),
            subscription_plan VARCHAR(50) DEFAULT 'free',
            status VARCHAR(20) DEFAULT 'active',
            encryption_key TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            settings JSONB DEFAULT '{}'::jsonb
        );
        
        -- Enable RLS on organizations
        ALTER TABLE system_data.organizations ENABLE ROW LEVEL SECURITY;
        
        -- Users table with tenant isolation
        CREATE TABLE IF NOT EXISTS system_data.users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            organization_id UUID NOT NULL REFERENCES system_data.organizations(id) ON DELETE CASCADE,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            role VARCHAR(50) DEFAULT 'user',
            status VARCHAR(20) DEFAULT 'active',
            last_login TIMESTAMP WITH TIME ZONE,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP WITH TIME ZONE,
            two_factor_secret VARCHAR(32),
            two_factor_enabled BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'::jsonb
        );
        
        -- Enable RLS on users
        ALTER TABLE system_data.users ENABLE ROW LEVEL SECURITY;
        
        -- Projects table with tenant isolation
        CREATE TABLE IF NOT EXISTS tenant_data.projects (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            organization_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(20) DEFAULT 'active',
            created_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            settings JSONB DEFAULT '{}'::jsonb
        );
        
        -- Enable RLS on projects
        ALTER TABLE tenant_data.projects ENABLE ROW LEVEL SECURITY;
        
        -- Forms table with tenant isolation
        CREATE TABLE IF NOT EXISTS tenant_data.forms (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            organization_id UUID NOT NULL,
            project_id UUID REFERENCES tenant_data.projects(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            version VARCHAR(20) DEFAULT '1.0',
            status VARCHAR(20) DEFAULT 'draft',
            schema JSONB NOT NULL,
            settings JSONB DEFAULT '{}'::jsonb,
            created_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Enable RLS on forms
        ALTER TABLE tenant_data.forms ENABLE ROW LEVEL SECURITY;
        
        -- Submissions table with encryption
        CREATE TABLE IF NOT EXISTS tenant_data.submissions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            organization_id UUID NOT NULL,
            form_id UUID NOT NULL REFERENCES tenant_data.forms(id) ON DELETE CASCADE,
            data JSONB NOT NULL,
            encrypted_data TEXT, -- For sensitive fields
            status VARCHAR(20) DEFAULT 'submitted',
            submitted_by UUID,
            submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'::jsonb
        );
        
        -- Enable RLS on submissions
        ALTER TABLE tenant_data.submissions ENABLE ROW LEVEL SECURITY;
        
        -- Audit log table
        CREATE TABLE IF NOT EXISTS audit_logs.activity_log (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            organization_id UUID,
            user_id UUID,
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50),
            resource_id UUID,
            details JSONB,
            ip_address INET,
            user_agent TEXT,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Session management table
        CREATE TABLE IF NOT EXISTS system_data.user_sessions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES system_data.users(id) ON DELETE CASCADE,
            session_token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        return tables_script
    
    def create_row_level_security_policies(self):
        """Create RLS policies for tenant isolation"""
        
        rls_script = """
        -- RLS Policy for organizations (admin only)
        CREATE POLICY org_admin_policy ON system_data.organizations
            FOR ALL TO odk_admin_role
            USING (true);
        
        -- RLS Policy for users (organization isolation)
        CREATE POLICY user_org_policy ON system_data.users
            FOR ALL TO odk_user_role
            USING (organization_id = current_setting('app.current_organization_id')::UUID);
        
        CREATE POLICY user_admin_policy ON system_data.users
            FOR ALL TO odk_admin_role
            USING (true);
        
        -- RLS Policy for projects (organization isolation)
        CREATE POLICY project_org_policy ON tenant_data.projects
            FOR ALL TO odk_user_role
            USING (organization_id = current_setting('app.current_organization_id')::UUID);
        
        CREATE POLICY project_admin_policy ON tenant_data.projects
            FOR ALL TO odk_admin_role
            USING (true);
        
        -- RLS Policy for forms (organization isolation)
        CREATE POLICY form_org_policy ON tenant_data.forms
            FOR ALL TO odk_user_role
            USING (organization_id = current_setting('app.current_organization_id')::UUID);
        
        CREATE POLICY form_admin_policy ON tenant_data.forms
            FOR ALL TO odk_admin_role
            USING (true);
        
        -- RLS Policy for submissions (organization isolation)
        CREATE POLICY submission_org_policy ON tenant_data.submissions
            FOR ALL TO odk_user_role
            USING (organization_id = current_setting('app.current_organization_id')::UUID);
        
        CREATE POLICY submission_admin_policy ON tenant_data.submissions
            FOR ALL TO odk_admin_role
            USING (true);
        """
        
        return rls_script
    
    def create_indexes_and_optimizations(self):
        """Create indexes for performance optimization"""
        
        indexes_script = """
        -- Performance indexes
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_organization_id 
            ON system_data.users(organization_id);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email 
            ON system_data.users(email);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_status 
            ON system_data.users(status);
        
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_organization_id 
            ON tenant_data.projects(organization_id);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_status 
            ON tenant_data.projects(status);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_created_by 
            ON tenant_data.projects(created_by);
        
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_forms_organization_id 
            ON tenant_data.forms(organization_id);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_forms_project_id 
            ON tenant_data.forms(project_id);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_forms_status 
            ON tenant_data.forms(status);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_forms_created_by 
            ON tenant_data.forms(created_by);
        
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_submissions_organization_id 
            ON tenant_data.submissions(organization_id);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_submissions_form_id 
            ON tenant_data.submissions(form_id);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_submissions_status 
            ON tenant_data.submissions(status);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_submissions_submitted_at 
            ON tenant_data.submissions(submitted_at);
        
        -- GIN indexes for JSONB columns
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_forms_schema_gin 
            ON tenant_data.forms USING GIN(schema);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_submissions_data_gin 
            ON tenant_data.submissions USING GIN(data);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_submissions_metadata_gin 
            ON tenant_data.submissions USING GIN(metadata);
        
        -- Audit log indexes
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_organization_id 
            ON audit_logs.activity_log(organization_id);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_user_id 
            ON audit_logs.activity_log(user_id);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_timestamp 
            ON audit_logs.activity_log(timestamp);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_action 
            ON audit_logs.activity_log(action);
        """
        
        return indexes_script
    
    def create_security_functions(self):
        """Create security and encryption functions"""
        
        functions_script = """
        -- Function to encrypt sensitive data
        CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT, org_key TEXT)
        RETURNS TEXT AS $$
        BEGIN
            RETURN encode(pgp_sym_encrypt(data, org_key), 'base64');
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Function to decrypt sensitive data
        CREATE OR REPLACE FUNCTION decrypt_sensitive_data(encrypted_data TEXT, org_key TEXT)
        RETURNS TEXT AS $$
        BEGIN
            RETURN pgp_sym_decrypt(decode(encrypted_data, 'base64'), org_key);
        EXCEPTION
            WHEN OTHERS THEN
                RETURN NULL;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Function to hash passwords
        CREATE OR REPLACE FUNCTION hash_password(password TEXT)
        RETURNS TEXT AS $$
        BEGIN
            RETURN crypt(password, gen_salt('bf', 12));
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Function to verify passwords
        CREATE OR REPLACE FUNCTION verify_password(password TEXT, hash TEXT)
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN hash = crypt(password, hash);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Function to set organization context
        CREATE OR REPLACE FUNCTION set_organization_context(org_id UUID)
        RETURNS VOID AS $$
        BEGIN
            PERFORM set_config('app.current_organization_id', org_id::TEXT, true);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Function to log audit events
        CREATE OR REPLACE FUNCTION log_audit_event(
            p_organization_id UUID,
            p_user_id UUID,
            p_action VARCHAR(100),
            p_resource_type VARCHAR(50),
            p_resource_id UUID,
            p_details JSONB,
            p_ip_address INET,
            p_user_agent TEXT
        )
        RETURNS VOID AS $$
        BEGIN
            INSERT INTO audit_logs.activity_log (
                organization_id, user_id, action, resource_type, 
                resource_id, details, ip_address, user_agent
            ) VALUES (
                p_organization_id, p_user_id, p_action, p_resource_type,
                p_resource_id, p_details, p_ip_address, p_user_agent
            );
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        
        return functions_script
    
    def create_triggers_and_automation(self):
        """Create triggers for automation and security"""
        
        triggers_script = """
        -- Trigger function for updated_at timestamps
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Apply updated_at triggers
        CREATE TRIGGER update_organizations_updated_at 
            BEFORE UPDATE ON system_data.organizations
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_users_updated_at 
            BEFORE UPDATE ON system_data.users
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_projects_updated_at 
            BEFORE UPDATE ON tenant_data.projects
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_forms_updated_at 
            BEFORE UPDATE ON tenant_data.forms
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_submissions_updated_at 
            BEFORE UPDATE ON tenant_data.submissions
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        -- Audit trigger function
        CREATE OR REPLACE FUNCTION audit_trigger_function()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                PERFORM log_audit_event(
                    NEW.organization_id,
                    current_setting('app.current_user_id', true)::UUID,
                    TG_OP,
                    TG_TABLE_NAME,
                    NEW.id,
                    to_jsonb(NEW),
                    current_setting('app.current_ip_address', true)::INET,
                    current_setting('app.current_user_agent', true)
                );
                RETURN NEW;
            ELSIF TG_OP = 'UPDATE' THEN
                PERFORM log_audit_event(
                    NEW.organization_id,
                    current_setting('app.current_user_id', true)::UUID,
                    TG_OP,
                    TG_TABLE_NAME,
                    NEW.id,
                    jsonb_build_object('old', to_jsonb(OLD), 'new', to_jsonb(NEW)),
                    current_setting('app.current_ip_address', true)::INET,
                    current_setting('app.current_user_agent', true)
                );
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                PERFORM log_audit_event(
                    OLD.organization_id,
                    current_setting('app.current_user_id', true)::UUID,
                    TG_OP,
                    TG_TABLE_NAME,
                    OLD.id,
                    to_jsonb(OLD),
                    current_setting('app.current_ip_address', true)::INET,
                    current_setting('app.current_user_agent', true)
                );
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Apply audit triggers
        CREATE TRIGGER audit_projects_trigger
            AFTER INSERT OR UPDATE OR DELETE ON tenant_data.projects
            FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
        
        CREATE TRIGGER audit_forms_trigger
            AFTER INSERT OR UPDATE OR DELETE ON tenant_data.forms
            FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
        
        CREATE TRIGGER audit_submissions_trigger
            AFTER INSERT OR UPDATE OR DELETE ON tenant_data.submissions
            FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
        """
        
        return triggers_script
    
    def setup_backup_and_recovery(self):
        """Setup automated backup and recovery"""
        
        backup_script = f"""
        #!/bin/bash
        
        # PostgreSQL Backup Script for ODK MCP System
        
        # Configuration
        DB_NAME="{self.config['database']}"
        DB_USER="{self.config['username']}"
        DB_HOST="{self.config['host']}"
        DB_PORT="{self.config['port']}"
        BACKUP_DIR="/var/backups/odk-mcp"
        RETENTION_DAYS="{self.config['backup_retention_days']}"
        
        # Create backup directory
        mkdir -p $BACKUP_DIR
        
        # Generate backup filename with timestamp
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        BACKUP_FILE="$BACKUP_DIR/odk_mcp_backup_$TIMESTAMP.sql"
        
        # Perform backup
        pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \\
            --verbose --clean --no-owner --no-privileges \\
            --format=custom --compress=9 \\
            --file="$BACKUP_FILE.custom"
        
        # Also create plain SQL backup for easier restoration
        pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \\
            --verbose --clean --no-owner --no-privileges \\
            --format=plain \\
            --file="$BACKUP_FILE"
        
        # Compress plain SQL backup
        gzip "$BACKUP_FILE"
        
        # Remove old backups
        find $BACKUP_DIR -name "odk_mcp_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
        find $BACKUP_DIR -name "odk_mcp_backup_*.custom" -mtime +$RETENTION_DAYS -delete
        
        # Log backup completion
        echo "$(date): Backup completed successfully - $BACKUP_FILE.gz" >> /var/log/odk-mcp-backup.log
        """
        
        return backup_script
    
    def create_monitoring_views(self):
        """Create monitoring and analytics views"""
        
        views_script = """
        -- Organization statistics view
        CREATE OR REPLACE VIEW analytics.organization_stats AS
        SELECT 
            o.id,
            o.name,
            o.subscription_plan,
            COUNT(DISTINCT u.id) as user_count,
            COUNT(DISTINCT p.id) as project_count,
            COUNT(DISTINCT f.id) as form_count,
            COUNT(DISTINCT s.id) as submission_count,
            o.created_at
        FROM system_data.organizations o
        LEFT JOIN system_data.users u ON o.id = u.organization_id AND u.status = 'active'
        LEFT JOIN tenant_data.projects p ON o.id = p.organization_id AND p.status = 'active'
        LEFT JOIN tenant_data.forms f ON o.id = f.organization_id
        LEFT JOIN tenant_data.submissions s ON o.id = s.organization_id
        GROUP BY o.id, o.name, o.subscription_plan, o.created_at;
        
        -- Daily activity view
        CREATE OR REPLACE VIEW analytics.daily_activity AS
        SELECT 
            DATE(timestamp) as activity_date,
            organization_id,
            action,
            COUNT(*) as action_count
        FROM audit_logs.activity_log
        WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY DATE(timestamp), organization_id, action
        ORDER BY activity_date DESC;
        
        -- Form performance view
        CREATE OR REPLACE VIEW analytics.form_performance AS
        SELECT 
            f.id,
            f.title,
            f.organization_id,
            COUNT(s.id) as submission_count,
            AVG(EXTRACT(EPOCH FROM (s.submitted_at - s.created_at))) as avg_completion_time,
            COUNT(DISTINCT s.submitted_by) as unique_submitters,
            MAX(s.submitted_at) as last_submission
        FROM tenant_data.forms f
        LEFT JOIN tenant_data.submissions s ON f.id = s.form_id
        GROUP BY f.id, f.title, f.organization_id;
        
        -- System health view
        CREATE OR REPLACE VIEW analytics.system_health AS
        SELECT 
            'database_size' as metric,
            pg_size_pretty(pg_database_size(current_database())) as value,
            NOW() as measured_at
        UNION ALL
        SELECT 
            'active_connections' as metric,
            COUNT(*)::TEXT as value,
            NOW() as measured_at
        FROM pg_stat_activity
        WHERE state = 'active'
        UNION ALL
        SELECT 
            'total_organizations' as metric,
            COUNT(*)::TEXT as value,
            NOW() as measured_at
        FROM system_data.organizations
        WHERE status = 'active';
        """
        
        return views_script
    
    def execute_setup(self):
        """Execute the complete PostgreSQL setup"""
        try:
            logger.info("Starting production PostgreSQL setup...")
            
            # Create setup scripts
            scripts = {
                'database_structure.sql': self.create_database_structure(),
                'tenant_tables.sql': self.create_tenant_isolation_tables(),
                'rls_policies.sql': self.create_row_level_security_policies(),
                'indexes.sql': self.create_indexes_and_optimizations(),
                'functions.sql': self.create_security_functions(),
                'triggers.sql': self.create_triggers_and_automation(),
                'views.sql': self.create_monitoring_views(),
                'backup.sh': self.setup_backup_and_recovery()
            }
            
            # Create scripts directory
            scripts_dir = '/tmp/odk_mcp_setup'
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write all scripts
            for filename, content in scripts.items():
                script_path = os.path.join(scripts_dir, filename)
                with open(script_path, 'w') as f:
                    f.write(content)
                
                if filename.endswith('.sh'):
                    os.chmod(script_path, 0o755)
            
            logger.info(f"Setup scripts created in {scripts_dir}")
            
            # Create configuration file
            config_file = os.path.join(scripts_dir, 'production_config.json')
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2, default=str)
            
            # Create environment file
            env_file = os.path.join(scripts_dir, '.env.production')
            with open(env_file, 'w') as f:
                f.write(f"""# Production PostgreSQL Configuration
POSTGRES_HOST={self.config['host']}
POSTGRES_PORT={self.config['port']}
POSTGRES_DB={self.config['database']}
POSTGRES_USER={self.config['username']}
POSTGRES_PASSWORD={self.config['password']}
DATABASE_URL=postgresql://{self.config['username']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}?sslmode={self.config['ssl_mode']}

# Security
ENCRYPTION_KEY={self.encryption_key.decode()}
ROW_LEVEL_SECURITY=true
AUDIT_LOGGING=true

# Performance
CONNECTION_POOL_SIZE={self.config['connection_pool_size']}
MAX_OVERFLOW={self.config['max_overflow']}
POOL_TIMEOUT={self.config['pool_timeout']}
POOL_RECYCLE={self.config['pool_recycle']}

# Backup
BACKUP_RETENTION_DAYS={self.config['backup_retention_days']}
""")
            
            logger.info("Production PostgreSQL setup completed successfully!")
            logger.info(f"Configuration saved to: {config_file}")
            logger.info(f"Environment variables saved to: {env_file}")
            
            return {
                'success': True,
                'scripts_directory': scripts_dir,
                'config_file': config_file,
                'env_file': env_file,
                'database_url': f"postgresql://{self.config['username']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}",
                'encryption_key': self.encryption_key.decode()
            }
            
        except Exception as e:
            logger.error(f"PostgreSQL setup failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

if __name__ == '__main__':
    setup = ProductionPostgreSQLSetup()
    result = setup.execute_setup()
    
    if result['success']:
        print("✅ Production PostgreSQL setup completed successfully!")
        print(f"📁 Scripts directory: {result['scripts_directory']}")
        print(f"⚙️ Configuration file: {result['config_file']}")
        print(f"🔐 Environment file: {result['env_file']}")
        print("\n🚀 Next steps:")
        print("1. Review the generated scripts")
        print("2. Execute database_structure.sql on your PostgreSQL server")
        print("3. Run the remaining scripts in order")
        print("4. Set up the backup cron job using backup.sh")
        print("5. Configure your application with the environment variables")
    else:
        print(f"❌ Setup failed: {result['error']}")

