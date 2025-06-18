#!/usr/bin/env python3
"""
Development Data Seeder for Enhanced ODK MCP System
Seeds the database with realistic development and testing data
"""

import os
import sys
import logging
import argparse
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import psycopg2
import sqlite3
from pathlib import Path
import bcrypt
from faker import Faker

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

# Initialize Faker for generating realistic data
fake = Faker()

class DevelopmentDataSeeder:
    """Seeds database with development and testing data"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize data seeder with database configuration"""
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
                self.connection.autocommit = True
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
    
    def clear_existing_data(self):
        """Clear existing development data"""
        logger.info("Clearing existing development data...")
        
        cursor = self.connection.cursor()
        
        # List of tables to clear in dependency order
        tables = [
            'audit_logs',
            'security_sessions',
            'encryption_keys',
            'usage_tracking',
            'subscriptions',
            'analytics_cache',
            'analytics_reports',
            'submissions',
            'forms',
            'projects',
            'users',
            'organizations'
        ]
        
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table}")
                logger.info(f"Cleared table: {table}")
            except Exception as e:
                logger.warning(f"Could not clear table {table}: {str(e)}")
    
    def seed_organizations(self) -> List[str]:
        """Seed organizations data"""
        logger.info("Seeding organizations...")
        
        organizations = [
            {
                'name': 'Save the Children Foundation',
                'type': 'ngo',
                'description': 'International non-governmental organization that promotes children\'s rights',
                'contact_email': 'contact@savechildren.org',
                'contact_phone': '+1-800-728-3843',
                'subscription_tier': 'enterprise',
                'storage_quota': 107374182400,  # 100GB
                'api_quota': 100000
            },
            {
                'name': 'Global Health Research Institute',
                'type': 'academic',
                'description': 'Leading research institution focused on global health challenges',
                'contact_email': 'research@ghri.edu',
                'contact_phone': '+1-617-555-0123',
                'subscription_tier': 'professional',
                'storage_quota': 10737418240,  # 10GB
                'api_quota': 10000
            },
            {
                'name': 'TechCorp CSR Division',
                'type': 'corporate',
                'description': 'Corporate social responsibility division of TechCorp',
                'contact_email': 'csr@techcorp.com',
                'contact_phone': '+1-415-555-0199',
                'subscription_tier': 'starter',
                'storage_quota': 1073741824,  # 1GB
                'api_quota': 1000
            },
            {
                'name': 'Ministry of Health - Data Analytics',
                'type': 'government',
                'description': 'Government health ministry data collection and analytics unit',
                'contact_email': 'data@health.gov',
                'contact_phone': '+1-202-555-0167',
                'subscription_tier': 'professional',
                'storage_quota': 53687091200,  # 50GB
                'api_quota': 50000
            },
            {
                'name': 'EduTech Startup',
                'type': 'startup',
                'description': 'Educational technology startup focusing on developing countries',
                'contact_email': 'hello@edutech.startup',
                'contact_phone': '+1-650-555-0142',
                'subscription_tier': 'free',
                'storage_quota': 1073741824,  # 1GB
                'api_quota': 1000
            }
        ]
        
        cursor = self.connection.cursor()
        org_ids = []
        
        for org_data in organizations:
            org_id = str(uuid.uuid4())
            org_ids.append(org_id)
            
            if self.db_type == 'postgresql':
                cursor.execute("""
                    INSERT INTO organizations (
                        id, name, type, description, contact_email, contact_phone,
                        subscription_tier, storage_quota, api_quota
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    org_id, org_data['name'], org_data['type'], org_data['description'],
                    org_data['contact_email'], org_data['contact_phone'],
                    org_data['subscription_tier'], org_data['storage_quota'], org_data['api_quota']
                ))
            else:  # SQLite
                cursor.execute("""
                    INSERT INTO organizations (
                        id, name, type, description, contact_email, contact_phone,
                        subscription_tier, storage_quota, api_quota
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    org_id, org_data['name'], org_data['type'], org_data['description'],
                    org_data['contact_email'], org_data['contact_phone'],
                    org_data['subscription_tier'], org_data['storage_quota'], org_data['api_quota']
                ))
        
        logger.info(f"Seeded {len(organizations)} organizations")
        return org_ids
    
    def seed_users(self, org_ids: List[str]) -> List[str]:
        """Seed users data"""
        logger.info("Seeding users...")
        
        cursor = self.connection.cursor()
        user_ids = []
        
        # Create admin users for each organization
        for i, org_id in enumerate(org_ids):
            # Admin user
            admin_id = str(uuid.uuid4())
            user_ids.append(admin_id)
            
            password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            api_key = f"odk_api_{uuid.uuid4().hex[:16]}"
            
            if self.db_type == 'postgresql':
                cursor.execute("""
                    INSERT INTO users (
                        id, organization_id, username, email, password_hash,
                        first_name, last_name, role, api_key
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    admin_id, org_id, f'admin{i+1}', f'admin{i+1}@example.com',
                    password_hash, 'Admin', f'User{i+1}', 'admin', api_key
                ))
            else:  # SQLite
                cursor.execute("""
                    INSERT INTO users (
                        id, organization_id, username, email, password_hash,
                        first_name, last_name, role, api_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    admin_id, org_id, f'admin{i+1}', f'admin{i+1}@example.com',
                    password_hash, 'Admin', f'User{i+1}', 'admin', api_key
                ))
            
            # Regular users
            for j in range(3):  # 3 users per organization
                user_id = str(uuid.uuid4())
                user_ids.append(user_id)
                
                password_hash = bcrypt.hashpw('user123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                api_key = f"odk_api_{uuid.uuid4().hex[:16]}"
                
                first_name = fake.first_name()
                last_name = fake.last_name()
                username = f"{first_name.lower()}.{last_name.lower()}{j+1}"
                email = f"{username}@example.com"
                role = ['manager', 'analyst', 'user'][j]
                
                if self.db_type == 'postgresql':
                    cursor.execute("""
                        INSERT INTO users (
                            id, organization_id, username, email, password_hash,
                            first_name, last_name, role, api_key
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_id, org_id, username, email, password_hash,
                        first_name, last_name, role, api_key
                    ))
                else:  # SQLite
                    cursor.execute("""
                        INSERT INTO users (
                            id, organization_id, username, email, password_hash,
                            first_name, last_name, role, api_key
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id, org_id, username, email, password_hash,
                        first_name, last_name, role, api_key
                    ))
        
        logger.info(f"Seeded {len(user_ids)} users")
        return user_ids
    
    def seed_projects(self, org_ids: List[str], user_ids: List[str]) -> List[str]:
        """Seed projects data"""
        logger.info("Seeding projects...")
        
        project_templates = [
            {
                'name': 'Child Nutrition Survey 2024',
                'description': 'Comprehensive survey on child nutrition status in rural areas',
                'status': 'active',
                'budget': 150000.00,
                'target_beneficiaries': 5000
            },
            {
                'name': 'Healthcare Access Assessment',
                'description': 'Assessment of healthcare accessibility in underserved communities',
                'status': 'active',
                'budget': 75000.00,
                'target_beneficiaries': 2500
            },
            {
                'name': 'Education Quality Monitoring',
                'description': 'Monitoring and evaluation of education quality improvements',
                'status': 'completed',
                'budget': 200000.00,
                'target_beneficiaries': 10000
            },
            {
                'name': 'Water Sanitation Impact Study',
                'description': 'Impact assessment of water and sanitation interventions',
                'status': 'active',
                'budget': 120000.00,
                'target_beneficiaries': 3000
            }
        ]
        
        cursor = self.connection.cursor()
        project_ids = []
        
        for org_id in org_ids:
            for i, template in enumerate(project_templates):
                project_id = str(uuid.uuid4())
                project_ids.append(project_id)
                
                # Get a random user from this organization as creator
                org_users = [uid for uid in user_ids if self._get_user_org(uid) == org_id]
                created_by = org_users[0] if org_users else user_ids[0]
                
                start_date = fake.date_between(start_date='-1y', end_date='today')
                end_date = fake.date_between(start_date=start_date, end_date='+1y')
                
                if self.db_type == 'postgresql':
                    cursor.execute("""
                        INSERT INTO projects (
                            id, organization_id, name, description, status,
                            start_date, end_date, budget, target_beneficiaries, created_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        project_id, org_id, template['name'], template['description'],
                        template['status'], start_date, end_date, template['budget'],
                        template['target_beneficiaries'], created_by
                    ))
                else:  # SQLite
                    cursor.execute("""
                        INSERT INTO projects (
                            id, organization_id, name, description, status,
                            start_date, end_date, budget, target_beneficiaries, created_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        project_id, org_id, template['name'], template['description'],
                        template['status'], start_date, end_date, template['budget'],
                        template['target_beneficiaries'], created_by
                    ))
        
        logger.info(f"Seeded {len(project_ids)} projects")
        return project_ids
    
    def seed_forms(self, project_ids: List[str], user_ids: List[str]) -> List[str]:
        """Seed forms data"""
        logger.info("Seeding forms...")
        
        form_templates = [
            {
                'name': 'Household Survey Form',
                'description': 'Basic household demographic and socioeconomic survey',
                'status': 'active'
            },
            {
                'name': 'Health Assessment Form',
                'description': 'Individual health status assessment form',
                'status': 'active'
            },
            {
                'name': 'Education Enrollment Form',
                'description': 'School enrollment and attendance tracking form',
                'status': 'draft'
            }
        ]
        
        cursor = self.connection.cursor()
        form_ids = []
        
        for project_id in project_ids:
            for template in form_templates:
                form_id = str(uuid.uuid4())
                form_ids.append(form_id)
                
                # Sample XLSForm content
                xlsform_content = {
                    'survey': [
                        {'type': 'text', 'name': 'respondent_name', 'label': 'Respondent Name'},
                        {'type': 'integer', 'name': 'age', 'label': 'Age'},
                        {'type': 'select_one gender', 'name': 'gender', 'label': 'Gender'},
                        {'type': 'geopoint', 'name': 'location', 'label': 'Location'},
                        {'type': 'date', 'name': 'survey_date', 'label': 'Survey Date'}
                    ],
                    'choices': [
                        {'list_name': 'gender', 'name': 'male', 'label': 'Male'},
                        {'list_name': 'gender', 'name': 'female', 'label': 'Female'},
                        {'list_name': 'gender', 'name': 'other', 'label': 'Other'}
                    ]
                }
                
                created_by = user_ids[0]  # Use first user as creator
                
                if self.db_type == 'postgresql':
                    cursor.execute("""
                        INSERT INTO forms (
                            id, project_id, name, description, xlsform_content, status, created_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        form_id, project_id, template['name'], template['description'],
                        json.dumps(xlsform_content), template['status'], created_by
                    ))
                else:  # SQLite
                    cursor.execute("""
                        INSERT INTO forms (
                            id, project_id, name, description, xlsform_content, status, created_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        form_id, project_id, template['name'], template['description'],
                        json.dumps(xlsform_content), template['status'], created_by
                    ))
        
        logger.info(f"Seeded {len(form_ids)} forms")
        return form_ids
    
    def seed_submissions(self, form_ids: List[str], user_ids: List[str]):
        """Seed submissions data"""
        logger.info("Seeding submissions...")
        
        cursor = self.connection.cursor()
        submission_count = 0
        
        for form_id in form_ids:
            # Generate 10-50 submissions per form
            num_submissions = fake.random_int(min=10, max=50)
            
            for _ in range(num_submissions):
                submission_id = str(uuid.uuid4())
                
                # Generate realistic submission data
                submission_data = {
                    'respondent_name': fake.name(),
                    'age': fake.random_int(min=18, max=80),
                    'gender': fake.random_element(elements=['male', 'female', 'other']),
                    'location': f"{fake.latitude()},{fake.longitude()}",
                    'survey_date': fake.date_between(start_date='-6m', end_date='today').isoformat()
                }
                
                metadata = {
                    'device_id': fake.uuid4(),
                    'app_version': '2.0.0',
                    'duration': fake.random_int(min=300, max=1800)  # 5-30 minutes
                }
                
                submitted_by = fake.random_element(elements=user_ids)
                submitted_at = fake.date_time_between(start_date='-6m', end_date='now')
                
                if self.db_type == 'postgresql':
                    cursor.execute("""
                        INSERT INTO submissions (
                            id, form_id, data, metadata, submitted_by, submitted_at
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        submission_id, form_id, json.dumps(submission_data),
                        json.dumps(metadata), submitted_by, submitted_at
                    ))
                else:  # SQLite
                    cursor.execute("""
                        INSERT INTO submissions (
                            id, form_id, data, metadata, submitted_by, submitted_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        submission_id, form_id, json.dumps(submission_data),
                        json.dumps(metadata), submitted_by, submitted_at
                    ))
                
                submission_count += 1
        
        logger.info(f"Seeded {submission_count} submissions")
    
    def seed_subscriptions(self, org_ids: List[str]):
        """Seed subscription data"""
        logger.info("Seeding subscriptions...")
        
        cursor = self.connection.cursor()
        
        subscription_plans = {
            'free': {'amount': 0.00, 'billing_cycle': 'monthly'},
            'starter': {'amount': 29.00, 'billing_cycle': 'monthly'},
            'professional': {'amount': 99.00, 'billing_cycle': 'monthly'},
            'enterprise': {'amount': 299.00, 'billing_cycle': 'monthly'}
        }
        
        for org_id in org_ids:
            # Get organization's subscription tier
            if self.db_type == 'postgresql':
                cursor.execute("SELECT subscription_tier FROM organizations WHERE id = %s", (org_id,))
            else:
                cursor.execute("SELECT subscription_tier FROM organizations WHERE id = ?", (org_id,))
            
            tier = cursor.fetchone()[0]
            plan_info = subscription_plans.get(tier, subscription_plans['free'])
            
            subscription_id = str(uuid.uuid4())
            next_billing_date = fake.date_between(start_date='today', end_date='+1m')
            
            if self.db_type == 'postgresql':
                cursor.execute("""
                    INSERT INTO subscriptions (
                        id, organization_id, plan_name, amount, billing_cycle, next_billing_date
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    subscription_id, org_id, tier, plan_info['amount'],
                    plan_info['billing_cycle'], next_billing_date
                ))
            else:
                cursor.execute("""
                    INSERT INTO subscriptions (
                        id, organization_id, plan_name, amount, billing_cycle, next_billing_date
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    subscription_id, org_id, tier, plan_info['amount'],
                    plan_info['billing_cycle'], next_billing_date
                ))
        
        logger.info(f"Seeded {len(org_ids)} subscriptions")
    
    def _get_user_org(self, user_id: str) -> str:
        """Get organization ID for a user"""
        cursor = self.connection.cursor()
        
        if self.db_type == 'postgresql':
            cursor.execute("SELECT organization_id FROM users WHERE id = %s", (user_id,))
        else:
            cursor.execute("SELECT organization_id FROM users WHERE id = ?", (user_id,))
        
        result = cursor.fetchone()
        return result[0] if result else None
    
    def seed_all_data(self, clear_existing: bool = True):
        """Seed all development data"""
        logger.info("Starting development data seeding...")
        
        if clear_existing:
            self.clear_existing_data()
        
        # Seed data in dependency order
        org_ids = self.seed_organizations()
        user_ids = self.seed_users(org_ids)
        project_ids = self.seed_projects(org_ids, user_ids)
        form_ids = self.seed_forms(project_ids, user_ids)
        self.seed_submissions(form_ids, user_ids)
        self.seed_subscriptions(org_ids)
        
        logger.info("Development data seeding completed successfully!")
        
        # Print summary
        print("\n" + "="*60)
        print("DEVELOPMENT DATA SEEDING SUMMARY")
        print("="*60)
        print(f"Organizations: {len(org_ids)}")
        print(f"Users: {len(user_ids)}")
        print(f"Projects: {len(project_ids)}")
        print(f"Forms: {len(form_ids)}")
        print("\nDefault Login Credentials:")
        print("- admin1@example.com / admin123 (Save the Children)")
        print("- admin2@example.com / admin123 (Global Health Research)")
        print("- admin3@example.com / admin123 (TechCorp CSR)")
        print("- admin4@example.com / admin123 (Ministry of Health)")
        print("- admin5@example.com / admin123 (EduTech Startup)")
        print("="*60)

def main():
    """Main seeder function"""
    parser = argparse.ArgumentParser(description='Seed development data for ODK MCP System')
    parser.add_argument('--no-clear', action='store_true', help='Do not clear existing data')
    parser.add_argument('--organizations-only', action='store_true', help='Seed only organizations')
    parser.add_argument('--minimal', action='store_true', help='Seed minimal data set')
    
    args = parser.parse_args()
    
    try:
        # Initialize data seeder
        seeder = DevelopmentDataSeeder()
        
        # Connect to database
        seeder.connect()
        
        # Seed data
        if args.organizations_only:
            seeder.seed_organizations()
        elif args.minimal:
            org_ids = seeder.seed_organizations()
            user_ids = seeder.seed_users(org_ids)
            logger.info("Minimal data seeding completed")
        else:
            seeder.seed_all_data(clear_existing=not args.no_clear)
        
    except Exception as e:
        logger.error(f"Data seeding failed: {str(e)}")
        sys.exit(1)
    
    finally:
        if 'seeder' in locals():
            seeder.disconnect()

if __name__ == "__main__":
    main()

