"""
PostgreSQL Migration Scripts for ODK MCP System
Handles migration from SQLite to PostgreSQL with data preservation
"""

import os
import sqlite3
import psycopg2
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, MetaData, Table, Column, inspect
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLMigrator:
    """Handles migration from SQLite to PostgreSQL"""
    
    def __init__(self, postgres_config: Dict[str, Any]):
        self.postgres_config = postgres_config
        self.postgres_engine = None
        self.postgres_session = None
        
    def setup_postgresql(self):
        """Setup PostgreSQL database and connection"""
        
        # Create database if it doesn't exist
        self._create_database_if_not_exists()
        
        # Create engine and session
        url = self._build_postgres_url()
        self.postgres_engine = create_engine(url, echo=False)
        Session = sessionmaker(bind=self.postgres_engine)
        self.postgres_session = Session()
        
        logger.info("PostgreSQL setup completed")
    
    def _create_database_if_not_exists(self):
        """Create PostgreSQL database if it doesn't exist"""
        
        # Connect to postgres database to create target database
        admin_url = (
            f"postgresql://{self.postgres_config['username']}:"
            f"{self.postgres_config['password']}@"
            f"{self.postgres_config['host']}:{self.postgres_config['port']}/postgres"
        )
        
        try:
            admin_engine = create_engine(admin_url)
            
            with admin_engine.connect() as conn:
                # Check if database exists
                result = conn.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self.postgres_config['database'],)
                )
                
                if not result.fetchone():
                    # Create database
                    conn.execute("COMMIT")
                    conn.execute(f"CREATE DATABASE {self.postgres_config['database']}")
                    logger.info(f"Created database: {self.postgres_config['database']}")
                else:
                    logger.info(f"Database already exists: {self.postgres_config['database']}")
                    
        except Exception as e:
            logger.error(f"Error creating database: {str(e)}")
            raise
    
    def _build_postgres_url(self) -> str:
        """Build PostgreSQL connection URL"""
        
        return (
            f"postgresql://{self.postgres_config['username']}:"
            f"{self.postgres_config['password']}@"
            f"{self.postgres_config['host']}:{self.postgres_config['port']}/"
            f"{self.postgres_config['database']}"
        )
    
    def migrate_service_data(self, service_name: str, sqlite_path: str):
        """Migrate data from SQLite to PostgreSQL for a specific service"""
        
        if not os.path.exists(sqlite_path):
            logger.warning(f"SQLite database not found: {sqlite_path}")
            return
        
        logger.info(f"Starting migration for {service_name} from {sqlite_path}")
        
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        
        try:
            # Get table list from SQLite
            tables = self._get_sqlite_tables(sqlite_conn)
            
            for table_name in tables:
                self._migrate_table(sqlite_conn, table_name, service_name)
                
            logger.info(f"Migration completed for {service_name}")
            
        except Exception as e:
            logger.error(f"Migration failed for {service_name}: {str(e)}")
            raise
        finally:
            sqlite_conn.close()
    
    def _get_sqlite_tables(self, sqlite_conn) -> List[str]:
        """Get list of tables from SQLite database"""
        
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Filter out system tables
        tables = [t for t in tables if not t.startswith('sqlite_')]
        
        return tables
    
    def _migrate_table(self, sqlite_conn, table_name: str, service_name: str):
        """Migrate a single table from SQLite to PostgreSQL"""
        
        logger.info(f"Migrating table: {table_name}")
        
        # Get table schema from SQLite
        schema = self._get_sqlite_table_schema(sqlite_conn, table_name)
        
        # Create table in PostgreSQL
        postgres_table_name = f"{service_name}_{table_name}"
        self._create_postgres_table(postgres_table_name, schema)
        
        # Migrate data
        self._migrate_table_data(sqlite_conn, table_name, postgres_table_name)
        
        logger.info(f"Table migration completed: {table_name} -> {postgres_table_name}")
    
    def _get_sqlite_table_schema(self, sqlite_conn, table_name: str) -> List[Dict]:
        """Get table schema from SQLite"""
        
        cursor = sqlite_conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        schema = []
        for col in columns:
            schema.append({
                'name': col[1],
                'type': self._convert_sqlite_type_to_postgres(col[2]),
                'nullable': not col[3],
                'primary_key': col[5] == 1
            })
        
        return schema
    
    def _convert_sqlite_type_to_postgres(self, sqlite_type: str) -> str:
        """Convert SQLite data type to PostgreSQL data type"""
        
        type_mapping = {
            'INTEGER': 'INTEGER',
            'TEXT': 'TEXT',
            'REAL': 'REAL',
            'BLOB': 'BYTEA',
            'NUMERIC': 'NUMERIC',
            'VARCHAR': 'VARCHAR',
            'CHAR': 'CHAR',
            'BOOLEAN': 'BOOLEAN',
            'DATE': 'DATE',
            'DATETIME': 'TIMESTAMP',
            'TIMESTAMP': 'TIMESTAMP'
        }
        
        sqlite_type_upper = sqlite_type.upper()
        
        # Handle VARCHAR with length
        if 'VARCHAR' in sqlite_type_upper:
            return sqlite_type
        
        return type_mapping.get(sqlite_type_upper, 'TEXT')
    
    def _create_postgres_table(self, table_name: str, schema: List[Dict]):
        """Create table in PostgreSQL"""
        
        columns = []
        primary_keys = []
        
        for col in schema:
            col_def = f"{col['name']} {col['type']}"
            
            if not col['nullable']:
                col_def += " NOT NULL"
            
            if col['primary_key']:
                primary_keys.append(col['name'])
            
            columns.append(col_def)
        
        if primary_keys:
            columns.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
        
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        
        with self.postgres_engine.connect() as conn:
            conn.execute(create_sql)
            conn.commit()
    
    def _migrate_table_data(self, sqlite_conn, sqlite_table: str, postgres_table: str):
        """Migrate data from SQLite table to PostgreSQL table"""
        
        # Get all data from SQLite
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {sqlite_table}")
        rows = cursor.fetchall()
        
        if not rows:
            logger.info(f"No data to migrate for table: {sqlite_table}")
            return
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Prepare insert statement
        placeholders = ', '.join(['%s'] * len(column_names))
        insert_sql = f"INSERT INTO {postgres_table} ({', '.join(column_names)}) VALUES ({placeholders})"
        
        # Insert data into PostgreSQL
        with self.postgres_engine.connect() as conn:
            for row in rows:
                try:
                    conn.execute(insert_sql, tuple(row))
                except Exception as e:
                    logger.error(f"Error inserting row into {postgres_table}: {str(e)}")
                    logger.error(f"Row data: {dict(zip(column_names, row))}")
            
            conn.commit()
        
        logger.info(f"Migrated {len(rows)} rows from {sqlite_table} to {postgres_table}")

def setup_postgresql_environment():
    """Setup PostgreSQL environment with required extensions"""
    
    from shared.database_config import DatabaseConfig
    
    config = DatabaseConfig()
    
    if config.database_type != 'postgresql':
        logger.info("PostgreSQL not configured, skipping setup")
        return
    
    postgres_config = config.config
    
    # Connect to PostgreSQL and setup extensions
    url = (
        f"postgresql://{postgres_config['username']}:"
        f"{postgres_config['password']}@"
        f"{postgres_config['host']}:{postgres_config['port']}/"
        f"{postgres_config['database']}"
    )
    
    engine = create_engine(url)
    
    with engine.connect() as conn:
        # Create required extensions
        extensions = [
            'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
            'CREATE EXTENSION IF NOT EXISTS "pg_trgm"',
            'CREATE EXTENSION IF NOT EXISTS "btree_gin"'
        ]
        
        for ext_sql in extensions:
            try:
                conn.execute(ext_sql)
                logger.info(f"Extension created: {ext_sql}")
            except Exception as e:
                logger.warning(f"Could not create extension: {ext_sql}, Error: {str(e)}")
        
        conn.commit()
    
    logger.info("PostgreSQL environment setup completed")

def migrate_all_services():
    """Migrate all services from SQLite to PostgreSQL"""
    
    from shared.database_config import DatabaseConfig
    
    config = DatabaseConfig()
    
    if config.database_type != 'postgresql':
        logger.info("PostgreSQL not configured, skipping migration")
        return
    
    # Setup PostgreSQL
    setup_postgresql_environment()
    
    migrator = PostgreSQLMigrator(config.config)
    migrator.setup_postgresql()
    
    # Define services and their SQLite paths
    services = {
        'form_management': 'mcps/form_management/src/database/app.db',
        'data_collection': 'mcps/data_collection/src/database/app.db',
        'data_aggregation': 'mcps/data_aggregation/src/database/app.db'
    }
    
    for service_name, sqlite_path in services.items():
        try:
            migrator.migrate_service_data(service_name, sqlite_path)
        except Exception as e:
            logger.error(f"Failed to migrate {service_name}: {str(e)}")
    
    logger.info("All services migration completed")

if __name__ == "__main__":
    migrate_all_services()

