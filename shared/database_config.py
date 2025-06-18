"""
Enhanced Database Configuration for ODK MCP System
Supports PostgreSQL, SQLite, and Baserow with dynamic configuration
"""

import os
import logging
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import psycopg2
from urllib.parse import quote_plus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Dynamic database configuration supporting multiple database types"""
    
    def __init__(self):
        self.database_type = os.getenv('DATABASE_TYPE', 'postgresql').lower()
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration based on environment variables"""
        
        if self.database_type == 'postgresql':
            return self._get_postgresql_config()
        elif self.database_type == 'sqlite':
            return self._get_sqlite_config()
        elif self.database_type == 'baserow':
            return self._get_baserow_config()
        else:
            raise ValueError(f"Unsupported database type: {self.database_type}")
    
    def _get_postgresql_config(self) -> Dict[str, Any]:
        """Get PostgreSQL configuration from environment variables"""
        
        # Default PostgreSQL configuration
        config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'odk_mcp_system'),
            'username': os.getenv('POSTGRES_USER', 'odk_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'odk_password'),
            'ssl_mode': os.getenv('POSTGRES_SSL_MODE', 'prefer'),
            'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', 20)),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', 30)),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', 3600))
        }
        
        # Build connection URL
        password_encoded = quote_plus(config['password'])
        config['url'] = (
            f"postgresql://{config['username']}:{password_encoded}@"
            f"{config['host']}:{config['port']}/{config['database']}"
            f"?sslmode={config['ssl_mode']}"
        )
        
        return config
    
    def _get_sqlite_config(self) -> Dict[str, Any]:
        """Get SQLite configuration for development/testing"""
        
        db_path = os.getenv('SQLITE_PATH', 'data/odk_mcp_system.db')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        return {
            'path': db_path,
            'url': f"sqlite:///{db_path}",
            'pool_size': 1,
            'max_overflow': 0,
            'pool_timeout': 30,
            'pool_recycle': -1
        }
    
    def _get_baserow_config(self) -> Dict[str, Any]:
        """Get Baserow configuration for external data storage"""
        
        return {
            'api_url': os.getenv('BASEROW_API_URL', 'https://api.baserow.io'),
            'api_token': os.getenv('BASEROW_API_TOKEN'),
            'database_id': os.getenv('BASEROW_DATABASE_ID'),
            'timeout': int(os.getenv('BASEROW_TIMEOUT', 30)),
            'retry_attempts': int(os.getenv('BASEROW_RETRY_ATTEMPTS', 3))
        }
    
    def get_sqlalchemy_url(self) -> str:
        """Get SQLAlchemy database URL"""
        return self.config.get('url', '')
    
    def get_engine_kwargs(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration"""
        
        kwargs = {
            'echo': os.getenv('DB_ECHO', 'false').lower() == 'true',
            'pool_pre_ping': True
        }
        
        if self.database_type in ['postgresql', 'sqlite']:
            kwargs.update({
                'pool_size': self.config.get('pool_size', 10),
                'max_overflow': self.config.get('max_overflow', 20),
                'pool_timeout': self.config.get('pool_timeout', 30),
                'pool_recycle': self.config.get('pool_recycle', 3600)
            })
        
        return kwargs

class DatabaseManager:
    """Database manager with support for multiple database types"""
    
    def __init__(self, service_name: str = None):
        self.service_name = service_name or 'default'
        self.config = DatabaseConfig()
        self.engine = None
        self.session_factory = None
        self.Base = declarative_base()
        
    def initialize(self):
        """Initialize database connection and session factory"""
        
        try:
            if self.config.database_type == 'baserow':
                self._initialize_baserow()
            else:
                self._initialize_sqlalchemy()
                
            logger.info(f"Database initialized successfully for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database for {self.service_name}: {str(e)}")
            raise
    
    def _initialize_sqlalchemy(self):
        """Initialize SQLAlchemy engine and session factory"""
        
        url = self.config.get_sqlalchemy_url()
        engine_kwargs = self.config.get_engine_kwargs()
        
        self.engine = create_engine(url, **engine_kwargs)
        self.session_factory = sessionmaker(bind=self.engine)
        
        # Test connection
        with self.engine.connect() as conn:
            conn.execute("SELECT 1")
            
        logger.info(f"SQLAlchemy engine created for {self.config.database_type}")
    
    def _initialize_baserow(self):
        """Initialize Baserow connection"""
        
        # Import Baserow adapter
        from .baserow_adapter import BaserowAdapter
        
        self.baserow_adapter = BaserowAdapter(
            api_url=self.config.config['api_url'],
            api_token=self.config.config['api_token'],
            database_id=self.config.config['database_id']
        )
        
        # Test connection
        self.baserow_adapter.test_connection()
        
        logger.info("Baserow adapter initialized successfully")
    
    def get_session(self):
        """Get database session"""
        
        if self.config.database_type == 'baserow':
            return self.baserow_adapter.get_session()
        else:
            return self.session_factory()
    
    def create_tables(self):
        """Create database tables"""
        
        if self.config.database_type == 'baserow':
            self.baserow_adapter.create_tables()
        else:
            self.Base.metadata.create_all(self.engine)
    
    def drop_tables(self):
        """Drop database tables"""
        
        if self.config.database_type == 'baserow':
            self.baserow_adapter.drop_tables()
        else:
            self.Base.metadata.drop_all(self.engine)
    
    def migrate_from_sqlite(self, sqlite_path: str):
        """Migrate data from SQLite to current database"""
        
        if self.config.database_type == 'sqlite':
            logger.warning("Cannot migrate from SQLite to SQLite")
            return
            
        from .migration_utils import SQLiteMigrator
        
        migrator = SQLiteMigrator(
            source_path=sqlite_path,
            target_manager=self
        )
        
        migrator.migrate()
        logger.info(f"Migration from SQLite completed for {self.service_name}")

# Global database managers for each service
_db_managers = {}

def get_database_manager(service_name: str) -> DatabaseManager:
    """Get or create database manager for a service"""
    
    if service_name not in _db_managers:
        _db_managers[service_name] = DatabaseManager(service_name)
        _db_managers[service_name].initialize()
    
    return _db_managers[service_name]

def initialize_all_databases():
    """Initialize all database connections"""
    
    services = [
        'form_management',
        'data_collection', 
        'data_aggregation',
        'user_management',
        'subscription_management'
    ]
    
    for service in services:
        try:
            get_database_manager(service)
            logger.info(f"Database initialized for {service}")
        except Exception as e:
            logger.error(f"Failed to initialize database for {service}: {str(e)}")
            raise

# Environment configuration validation
def validate_environment():
    """Validate required environment variables"""
    
    database_type = os.getenv('DATABASE_TYPE', 'postgresql').lower()
    
    if database_type == 'postgresql':
        required_vars = [
            'POSTGRES_HOST', 'POSTGRES_DB', 
            'POSTGRES_USER', 'POSTGRES_PASSWORD'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(f"Missing PostgreSQL environment variables: {missing_vars}")
            logger.info("Using default PostgreSQL configuration")
    
    elif database_type == 'baserow':
        required_vars = ['BASEROW_API_TOKEN', 'BASEROW_DATABASE_ID']
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required Baserow environment variables: {missing_vars}")

if __name__ == "__main__":
    # Validate environment and initialize databases
    validate_environment()
    initialize_all_databases()
    print("Database configuration validated and initialized successfully")

