"""
Redis-like Multi-tenancy and Data Isolation System
Enterprise-grade tenant isolation with Redis-style performance and security
"""

import os
import json
import hashlib
import secrets
import asyncio
import redis
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TenantIsolationLevel(Enum):
    """Tenant isolation levels"""
    BASIC = "basic"           # Schema-level isolation
    ENHANCED = "enhanced"     # RLS + encryption
    ENTERPRISE = "enterprise" # Full isolation + audit

@dataclass
class TenantConfig:
    """Tenant configuration"""
    id: str
    name: str
    slug: str
    isolation_level: TenantIsolationLevel
    encryption_key: str
    database_schema: str
    redis_namespace: str
    max_connections: int = 10
    storage_quota_gb: int = 10
    api_rate_limit: int = 1000
    features: List[str] = None
    metadata: Dict[str, Any] = None

class TenantManager:
    """
    Redis-like multi-tenant manager with PostgreSQL backend
    Provides fast, secure, and isolated data access for multiple clients
    """
    
    def __init__(self, postgres_config: Dict, redis_config: Dict = None):
        self.postgres_config = postgres_config
        self.redis_config = redis_config or {}
        self.redis_client = None
        self.tenant_cache = {}
        self.connection_pools = {}
        
        # Initialize Redis if configured
        if self.redis_config:
            self.redis_client = redis.Redis(
                host=self.redis_config.get('host', 'localhost'),
                port=self.redis_config.get('port', 6379),
                db=self.redis_config.get('db', 0),
                password=self.redis_config.get('password'),
                decode_responses=True
            )
    
    def generate_tenant_id(self) -> str:
        """Generate unique tenant ID"""
        return str(uuid.uuid4())
    
    def generate_encryption_key(self) -> str:
        """Generate tenant-specific encryption key"""
        return secrets.token_urlsafe(32)
    
    def create_tenant_schema(self, tenant_id: str) -> str:
        """Create tenant-specific database schema"""
        schema_name = f"tenant_{tenant_id.replace('-', '_')}"
        return schema_name
    
    def create_redis_namespace(self, tenant_slug: str) -> str:
        """Create Redis namespace for tenant"""
        return f"odk:tenant:{tenant_slug}"
    
    @contextmanager
    def get_tenant_connection(self, tenant_id: str):
        """Get tenant-specific database connection with context"""
        try:
            # Get tenant config
            tenant = self.get_tenant_config(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            # Create connection
            conn = psycopg2.connect(
                host=self.postgres_config['host'],
                port=self.postgres_config['port'],
                database=self.postgres_config['database'],
                user=self.postgres_config['user'],
                password=self.postgres_config['password'],
                cursor_factory=RealDictCursor
            )
            
            # Set tenant context
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_organization_id', %s, true)",
                    (tenant_id,)
                )
                cursor.execute(
                    f"SET search_path TO {tenant.database_schema}, public"
                )
            
            yield conn
            
        except Exception as e:
            logger.error(f"Database connection error for tenant {tenant_id}: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()
    
    def create_tenant(self, name: str, slug: str, 
                     isolation_level: TenantIsolationLevel = TenantIsolationLevel.ENHANCED,
                     **kwargs) -> TenantConfig:
        """Create new tenant with complete isolation"""
        
        try:
            # Generate tenant configuration
            tenant_id = self.generate_tenant_id()
            encryption_key = self.generate_encryption_key()
            database_schema = self.create_tenant_schema(tenant_id)
            redis_namespace = self.create_redis_namespace(slug)
            
            tenant_config = TenantConfig(
                id=tenant_id,
                name=name,
                slug=slug,
                isolation_level=isolation_level,
                encryption_key=encryption_key,
                database_schema=database_schema,
                redis_namespace=redis_namespace,
                max_connections=kwargs.get('max_connections', 10),
                storage_quota_gb=kwargs.get('storage_quota_gb', 10),
                api_rate_limit=kwargs.get('api_rate_limit', 1000),
                features=kwargs.get('features', []),
                metadata=kwargs.get('metadata', {})
            )
            
            # Create database schema and tables
            self._create_tenant_database_structure(tenant_config)
            
            # Store tenant configuration
            self._store_tenant_config(tenant_config)
            
            # Initialize Redis namespace
            if self.redis_client:
                self._initialize_redis_namespace(tenant_config)
            
            # Cache tenant config
            self.tenant_cache[tenant_id] = tenant_config
            
            logger.info(f"Created tenant: {name} ({tenant_id})")
            return tenant_config
            
        except Exception as e:
            logger.error(f"Failed to create tenant {name}: {e}")
            raise
    
    def _create_tenant_database_structure(self, tenant: TenantConfig):
        """Create tenant-specific database structure"""
        
        schema_sql = f"""
        -- Create tenant schema
        CREATE SCHEMA IF NOT EXISTS {tenant.database_schema};
        
        -- Set schema permissions
        GRANT USAGE ON SCHEMA {tenant.database_schema} TO odk_user_role;
        GRANT CREATE ON SCHEMA {tenant.database_schema} TO odk_user_role;
        
        -- Create tenant-specific tables
        CREATE TABLE IF NOT EXISTS {tenant.database_schema}.projects (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(20) DEFAULT 'active',
            created_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            settings JSONB DEFAULT '{{}}'::jsonb
        );
        
        CREATE TABLE IF NOT EXISTS {tenant.database_schema}.forms (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            project_id UUID REFERENCES {tenant.database_schema}.projects(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            version VARCHAR(20) DEFAULT '1.0',
            status VARCHAR(20) DEFAULT 'draft',
            schema JSONB NOT NULL,
            settings JSONB DEFAULT '{{}}'::jsonb,
            created_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS {tenant.database_schema}.submissions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            form_id UUID NOT NULL REFERENCES {tenant.database_schema}.forms(id) ON DELETE CASCADE,
            data JSONB NOT NULL,
            encrypted_data TEXT,
            status VARCHAR(20) DEFAULT 'submitted',
            submitted_by UUID,
            submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{{}}'::jsonb
        );
        
        CREATE TABLE IF NOT EXISTS {tenant.database_schema}.analytics_cache (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            cache_key VARCHAR(255) UNIQUE NOT NULL,
            data JSONB NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_projects_status 
            ON {tenant.database_schema}.projects(status);
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_projects_created_by 
            ON {tenant.database_schema}.projects(created_by);
        
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_forms_project_id 
            ON {tenant.database_schema}.forms(project_id);
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_forms_status 
            ON {tenant.database_schema}.forms(status);
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_forms_schema_gin 
            ON {tenant.database_schema}.forms USING GIN(schema);
        
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_submissions_form_id 
            ON {tenant.database_schema}.submissions(form_id);
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_submissions_status 
            ON {tenant.database_schema}.submissions(status);
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_submissions_submitted_at 
            ON {tenant.database_schema}.submissions(submitted_at);
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_submissions_data_gin 
            ON {tenant.database_schema}.submissions USING GIN(data);
        
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_analytics_cache_key 
            ON {tenant.database_schema}.analytics_cache(cache_key);
        CREATE INDEX IF NOT EXISTS idx_{tenant.database_schema}_analytics_expires_at 
            ON {tenant.database_schema}.analytics_cache(expires_at);
        
        -- Create tenant-specific functions
        CREATE OR REPLACE FUNCTION {tenant.database_schema}.encrypt_field(data TEXT)
        RETURNS TEXT AS $$
        BEGIN
            RETURN encode(pgp_sym_encrypt(data, '{tenant.encryption_key}'), 'base64');
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        CREATE OR REPLACE FUNCTION {tenant.database_schema}.decrypt_field(encrypted_data TEXT)
        RETURNS TEXT AS $$
        BEGIN
            RETURN pgp_sym_decrypt(decode(encrypted_data, 'base64'), '{tenant.encryption_key}');
        EXCEPTION
            WHEN OTHERS THEN
                RETURN NULL;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Create triggers for updated_at
        CREATE OR REPLACE FUNCTION {tenant.database_schema}.update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER update_projects_updated_at 
            BEFORE UPDATE ON {tenant.database_schema}.projects
            FOR EACH ROW EXECUTE FUNCTION {tenant.database_schema}.update_updated_at_column();
        
        CREATE TRIGGER update_forms_updated_at 
            BEFORE UPDATE ON {tenant.database_schema}.forms
            FOR EACH ROW EXECUTE FUNCTION {tenant.database_schema}.update_updated_at_column();
        
        CREATE TRIGGER update_submissions_updated_at 
            BEFORE UPDATE ON {tenant.database_schema}.submissions
            FOR EACH ROW EXECUTE FUNCTION {tenant.database_schema}.update_updated_at_column();
        """
        
        # Execute schema creation
        conn = psycopg2.connect(
            host=self.postgres_config['host'],
            port=self.postgres_config['port'],
            database=self.postgres_config['database'],
            user=self.postgres_config['user'],
            password=self.postgres_config['password']
        )
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
            conn.commit()
            logger.info(f"Created database structure for tenant {tenant.id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create database structure for tenant {tenant.id}: {e}")
            raise
        finally:
            conn.close()
    
    def _store_tenant_config(self, tenant: TenantConfig):
        """Store tenant configuration in database"""
        
        insert_sql = """
        INSERT INTO system_data.organizations (
            id, name, slug, subscription_plan, status, encryption_key, 
            created_at, updated_at, settings
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        settings = {
            'isolation_level': tenant.isolation_level.value,
            'database_schema': tenant.database_schema,
            'redis_namespace': tenant.redis_namespace,
            'max_connections': tenant.max_connections,
            'storage_quota_gb': tenant.storage_quota_gb,
            'api_rate_limit': tenant.api_rate_limit,
            'features': tenant.features,
            'metadata': tenant.metadata
        }
        
        conn = psycopg2.connect(
            host=self.postgres_config['host'],
            port=self.postgres_config['port'],
            database=self.postgres_config['database'],
            user=self.postgres_config['user'],
            password=self.postgres_config['password']
        )
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(insert_sql, (
                    tenant.id,
                    tenant.name,
                    tenant.slug,
                    'free',  # Default subscription plan
                    'active',
                    tenant.encryption_key,
                    datetime.now(),
                    datetime.now(),
                    json.dumps(settings)
                ))
            conn.commit()
            logger.info(f"Stored configuration for tenant {tenant.id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to store configuration for tenant {tenant.id}: {e}")
            raise
        finally:
            conn.close()
    
    def _initialize_redis_namespace(self, tenant: TenantConfig):
        """Initialize Redis namespace for tenant"""
        if not self.redis_client:
            return
        
        try:
            # Set tenant metadata in Redis
            tenant_key = f"{tenant.redis_namespace}:config"
            self.redis_client.hset(tenant_key, mapping={
                'id': tenant.id,
                'name': tenant.name,
                'slug': tenant.slug,
                'isolation_level': tenant.isolation_level.value,
                'database_schema': tenant.database_schema,
                'created_at': datetime.now().isoformat()
            })
            
            # Set expiration for config (24 hours)
            self.redis_client.expire(tenant_key, 86400)
            
            # Initialize rate limiting
            rate_limit_key = f"{tenant.redis_namespace}:rate_limit"
            self.redis_client.set(rate_limit_key, 0, ex=3600)  # Reset hourly
            
            logger.info(f"Initialized Redis namespace for tenant {tenant.id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis namespace for tenant {tenant.id}: {e}")
    
    def get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant configuration"""
        
        # Check cache first
        if tenant_id in self.tenant_cache:
            return self.tenant_cache[tenant_id]
        
        # Check Redis cache
        if self.redis_client:
            redis_key = f"odk:tenant_config:{tenant_id}"
            cached_config = self.redis_client.get(redis_key)
            if cached_config:
                config_data = json.loads(cached_config)
                tenant = TenantConfig(**config_data)
                self.tenant_cache[tenant_id] = tenant
                return tenant
        
        # Load from database
        select_sql = """
        SELECT id, name, slug, encryption_key, settings
        FROM system_data.organizations
        WHERE id = %s AND status = 'active'
        """
        
        conn = psycopg2.connect(
            host=self.postgres_config['host'],
            port=self.postgres_config['port'],
            database=self.postgres_config['database'],
            user=self.postgres_config['user'],
            password=self.postgres_config['password'],
            cursor_factory=RealDictCursor
        )
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(select_sql, (tenant_id,))
                row = cursor.fetchone()
                
                if row:
                    settings = json.loads(row['settings']) if row['settings'] else {}
                    
                    tenant = TenantConfig(
                        id=row['id'],
                        name=row['name'],
                        slug=row['slug'],
                        isolation_level=TenantIsolationLevel(settings.get('isolation_level', 'enhanced')),
                        encryption_key=row['encryption_key'],
                        database_schema=settings.get('database_schema'),
                        redis_namespace=settings.get('redis_namespace'),
                        max_connections=settings.get('max_connections', 10),
                        storage_quota_gb=settings.get('storage_quota_gb', 10),
                        api_rate_limit=settings.get('api_rate_limit', 1000),
                        features=settings.get('features', []),
                        metadata=settings.get('metadata', {})
                    )
                    
                    # Cache the configuration
                    self.tenant_cache[tenant_id] = tenant
                    
                    # Cache in Redis
                    if self.redis_client:
                        redis_key = f"odk:tenant_config:{tenant_id}"
                        self.redis_client.setex(
                            redis_key, 
                            3600,  # 1 hour
                            json.dumps(tenant.__dict__, default=str)
                        )
                    
                    return tenant
                
        except Exception as e:
            logger.error(f"Failed to load tenant configuration {tenant_id}: {e}")
        finally:
            conn.close()
        
        return None
    
    def check_rate_limit(self, tenant_id: str, action: str = 'api_call') -> bool:
        """Check if tenant is within rate limits"""
        if not self.redis_client:
            return True  # No rate limiting without Redis
        
        tenant = self.get_tenant_config(tenant_id)
        if not tenant:
            return False
        
        rate_limit_key = f"{tenant.redis_namespace}:rate_limit:{action}"
        current_count = self.redis_client.get(rate_limit_key) or 0
        
        if int(current_count) >= tenant.api_rate_limit:
            return False
        
        # Increment counter
        pipe = self.redis_client.pipeline()
        pipe.incr(rate_limit_key)
        pipe.expire(rate_limit_key, 3600)  # Reset hourly
        pipe.execute()
        
        return True
    
    def cache_analytics_data(self, tenant_id: str, cache_key: str, 
                           data: Dict, ttl: int = 3600):
        """Cache analytics data for tenant"""
        
        # Cache in Redis if available
        if self.redis_client:
            tenant = self.get_tenant_config(tenant_id)
            if tenant:
                redis_key = f"{tenant.redis_namespace}:analytics:{cache_key}"
                self.redis_client.setex(redis_key, ttl, json.dumps(data, default=str))
        
        # Also cache in database for persistence
        with self.get_tenant_connection(tenant_id) as conn:
            with conn.cursor() as cursor:
                # Clean expired cache entries
                cursor.execute(
                    f"DELETE FROM {self.get_tenant_config(tenant_id).database_schema}.analytics_cache "
                    f"WHERE expires_at < NOW()"
                )
                
                # Insert new cache entry
                cursor.execute(
                    f"INSERT INTO {self.get_tenant_config(tenant_id).database_schema}.analytics_cache "
                    f"(cache_key, data, expires_at) VALUES (%s, %s, %s) "
                    f"ON CONFLICT (cache_key) DO UPDATE SET "
                    f"data = EXCLUDED.data, expires_at = EXCLUDED.expires_at",
                    (cache_key, json.dumps(data, default=str), 
                     datetime.now() + timedelta(seconds=ttl))
                )
            conn.commit()
    
    def get_cached_analytics_data(self, tenant_id: str, cache_key: str) -> Optional[Dict]:
        """Get cached analytics data for tenant"""
        
        # Try Redis first
        if self.redis_client:
            tenant = self.get_tenant_config(tenant_id)
            if tenant:
                redis_key = f"{tenant.redis_namespace}:analytics:{cache_key}"
                cached_data = self.redis_client.get(redis_key)
                if cached_data:
                    return json.loads(cached_data)
        
        # Fallback to database
        with self.get_tenant_connection(tenant_id) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT data FROM {self.get_tenant_config(tenant_id).database_schema}.analytics_cache "
                    f"WHERE cache_key = %s AND expires_at > NOW()",
                    (cache_key,)
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row['data'])
        
        return None
    
    def delete_tenant(self, tenant_id: str, confirm: bool = False):
        """Delete tenant and all associated data"""
        if not confirm:
            raise ValueError("Tenant deletion requires explicit confirmation")
        
        tenant = self.get_tenant_config(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        try:
            # Delete from Redis
            if self.redis_client:
                pattern = f"{tenant.redis_namespace}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            
            # Delete database schema
            conn = psycopg2.connect(
                host=self.postgres_config['host'],
                port=self.postgres_config['port'],
                database=self.postgres_config['database'],
                user=self.postgres_config['user'],
                password=self.postgres_config['password']
            )
            
            with conn.cursor() as cursor:
                cursor.execute(f"DROP SCHEMA IF EXISTS {tenant.database_schema} CASCADE")
                cursor.execute(
                    "DELETE FROM system_data.organizations WHERE id = %s",
                    (tenant_id,)
                )
            conn.commit()
            conn.close()
            
            # Remove from cache
            if tenant_id in self.tenant_cache:
                del self.tenant_cache[tenant_id]
            
            logger.info(f"Deleted tenant {tenant_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete tenant {tenant_id}: {e}")
            raise
    
    def list_tenants(self) -> List[TenantConfig]:
        """List all active tenants"""
        tenants = []
        
        select_sql = """
        SELECT id, name, slug, encryption_key, settings
        FROM system_data.organizations
        WHERE status = 'active'
        ORDER BY created_at DESC
        """
        
        conn = psycopg2.connect(
            host=self.postgres_config['host'],
            port=self.postgres_config['port'],
            database=self.postgres_config['database'],
            user=self.postgres_config['user'],
            password=self.postgres_config['password'],
            cursor_factory=RealDictCursor
        )
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(select_sql)
                rows = cursor.fetchall()
                
                for row in rows:
                    settings = json.loads(row['settings']) if row['settings'] else {}
                    
                    tenant = TenantConfig(
                        id=row['id'],
                        name=row['name'],
                        slug=row['slug'],
                        isolation_level=TenantIsolationLevel(settings.get('isolation_level', 'enhanced')),
                        encryption_key=row['encryption_key'],
                        database_schema=settings.get('database_schema'),
                        redis_namespace=settings.get('redis_namespace'),
                        max_connections=settings.get('max_connections', 10),
                        storage_quota_gb=settings.get('storage_quota_gb', 10),
                        api_rate_limit=settings.get('api_rate_limit', 1000),
                        features=settings.get('features', []),
                        metadata=settings.get('metadata', {})
                    )
                    
                    tenants.append(tenant)
                    
        except Exception as e:
            logger.error(f"Failed to list tenants: {e}")
        finally:
            conn.close()
        
        return tenants
    
    def get_tenant_statistics(self, tenant_id: str) -> Dict:
        """Get tenant usage statistics"""
        tenant = self.get_tenant_config(tenant_id)
        if not tenant:
            return {}
        
        stats = {}
        
        try:
            with self.get_tenant_connection(tenant_id) as conn:
                with conn.cursor() as cursor:
                    # Get project count
                    cursor.execute(
                        f"SELECT COUNT(*) as count FROM {tenant.database_schema}.projects"
                    )
                    stats['project_count'] = cursor.fetchone()['count']
                    
                    # Get form count
                    cursor.execute(
                        f"SELECT COUNT(*) as count FROM {tenant.database_schema}.forms"
                    )
                    stats['form_count'] = cursor.fetchone()['count']
                    
                    # Get submission count
                    cursor.execute(
                        f"SELECT COUNT(*) as count FROM {tenant.database_schema}.submissions"
                    )
                    stats['submission_count'] = cursor.fetchone()['count']
                    
                    # Get storage usage (approximate)
                    cursor.execute(
                        f"SELECT pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size "
                        f"FROM pg_tables WHERE schemaname = '{tenant.database_schema}'"
                    )
                    storage_sizes = cursor.fetchall()
                    stats['storage_usage'] = [row['size'] for row in storage_sizes]
                    
                    # Get recent activity
                    cursor.execute(
                        f"SELECT COUNT(*) as count FROM {tenant.database_schema}.submissions "
                        f"WHERE submitted_at >= NOW() - INTERVAL '24 hours'"
                    )
                    stats['recent_submissions'] = cursor.fetchone()['count']
        
        except Exception as e:
            logger.error(f"Failed to get statistics for tenant {tenant_id}: {e}")
        
        return stats

# Example usage and testing
if __name__ == '__main__':
    # Configuration
    postgres_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'odk_mcp_production',
        'user': 'odk_admin',
        'password': 'your_password'
    }
    
    redis_config = {
        'host': 'localhost',
        'port': 6379,
        'db': 0
    }
    
    # Initialize tenant manager
    tenant_manager = TenantManager(postgres_config, redis_config)
    
    # Create sample tenants
    try:
        # NGO tenant
        ngo_tenant = tenant_manager.create_tenant(
            name="Save the Children Foundation",
            slug="save-children",
            isolation_level=TenantIsolationLevel.ENTERPRISE,
            storage_quota_gb=50,
            api_rate_limit=5000,
            features=["advanced_analytics", "custom_reports", "api_access"]
        )
        print(f"✅ Created NGO tenant: {ngo_tenant.name}")
        
        # Research organization tenant
        research_tenant = tenant_manager.create_tenant(
            name="Global Health Research Institute",
            slug="ghri",
            isolation_level=TenantIsolationLevel.ENHANCED,
            storage_quota_gb=100,
            api_rate_limit=10000,
            features=["data_export", "statistical_analysis", "collaboration"]
        )
        print(f"✅ Created research tenant: {research_tenant.name}")
        
        # Corporate CSR tenant
        csr_tenant = tenant_manager.create_tenant(
            name="TechCorp CSR Division",
            slug="techcorp-csr",
            isolation_level=TenantIsolationLevel.BASIC,
            storage_quota_gb=25,
            api_rate_limit=2000,
            features=["basic_reports", "data_visualization"]
        )
        print(f"✅ Created CSR tenant: {csr_tenant.name}")
        
        # List all tenants
        all_tenants = tenant_manager.list_tenants()
        print(f"\n📊 Total tenants: {len(all_tenants)}")
        
        for tenant in all_tenants:
            stats = tenant_manager.get_tenant_statistics(tenant.id)
            print(f"  - {tenant.name}: {stats}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

