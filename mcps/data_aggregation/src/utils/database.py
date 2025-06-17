import os
import sys
# DON\'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import current_app
from src.models.user import db, User, Project, ProjectUser
from src.models.data import AggregatedData, DataAnalysisResult
import logging
import requests
import json

logger = logging.getLogger(__name__)

def init_database(app):
    """Initialize database and create default admin user"""
    with app.app_context():
        try:
            # Create all tables
            db.init_app(app)
            db.create_all()
            
            # Create default admin user if it doesn\'t exist
            admin_user = User.query.filter_by(username=\'admin\').first()
            if not admin_user:
                admin_user = User(
                    username=\'admin\',
                    email=\'admin@odk-system.local\',
                    first_name=\'System\',
                    last_name=\'Administrator\',
                    is_admin=True
                )
                admin_user.set_password(\'admin123\')  # Change this in production!
                
                db.session.add(admin_user)
                db.session.commit()
                
                logger.info("Created default admin user (username: admin, password: admin123)")
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

def get_database_adapter():
    """Get the appropriate database adapter based on configuration"""
    database_type = current_app.config.get(\'DATABASE_TYPE\', \'sqlite\')
    
    if database_type == \'baserow\':
        return BaserowAdapter()
    else:
        return SQLiteAdapter()

class SQLiteAdapter:
    """SQLite database adapter for data operations"""
    
    def create_aggregated_data(self, data):
        """Create new aggregated data record"""
        try:
            aggregated_data = AggregatedData(**data)
            db.session.add(aggregated_data)
            db.session.commit()
            return aggregated_data.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating aggregated data: {str(e)}")
            raise
    
    def get_aggregated_data(self, project_id, filters=None, pagination=None):
        """Retrieve aggregated data with optional filters and pagination"""
        try:
            query = AggregatedData.query.filter_by(project_id=project_id)
            
            # Apply filters
            if filters:
                if filters.get(\'form_id\'):
                    query = query.filter_by(form_id=filters[\'form_id\'])
                if filters.get(\'status\'):
                    query = query.filter_by(processing_status=filters[\'status\'])
                if filters.get(\'start_date\'):
                    query = query.filter(AggregatedData.submitted_at >= filters[\'start_date\'])
                if filters.get(\'end_date\'):
                    query = query.filter(AggregatedData.submitted_at <= filters[\'end_date\'])
            
            # Apply pagination
            if pagination:
                page = pagination.get(\'page\', 1)
                limit = pagination.get(\'limit\', 10)
                
                paginated = query.paginate(
                    page=page,
                    per_page=limit,
                    error_out=False
                )
                
                return {
                    \'data\': [item.to_dict() for item in paginated.items],
                    \'pagination\': {
                        \'page\': page,
                        \'limit\': limit,
                        \'total\': paginated.total,
                        \'pages\': paginated.pages,
                        \'has_next\': paginated.has_next,
                        \'has_prev\': paginated.has_prev
                    }
                }
            else:
                items = query.all()
                return {
                    \'data\': [item.to_dict() for item in items],
                    \'total\': len(items)
                }
                
        except Exception as e:
            logger.error(f"Error retrieving aggregated data: {str(e)}")
            raise
    
    def update_aggregated_data(self, data_id, updates):
        """Update aggregated data record"""
        try:
            data_record = AggregatedData.query.filter_by(data_id=data_id).first()
            if not data_record:
                return None
            
            for key, value in updates.items():
                if hasattr(data_record, key):
                    setattr(data_record, key, value)
            
            db.session.commit()
            return data_record.to_dict()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating aggregated data: {str(e)}")
            raise
    
    def delete_aggregated_data(self, data_id):
        """Delete aggregated data record"""
        try:
            data_record = AggregatedData.query.filter_by(data_id=data_id).first()
            if not data_record:
                return False
            
            db.session.delete(data_record)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting aggregated data: {str(e)}")
            raise

class BaserowAdapter:
    """Baserow database adapter for data operations"""
    
    def __init__(self):
        self.base_url = current_app.config.get(\'BASEROW_URL\')
        self.token = current_app.config.get(\'BASEROW_TOKEN\')
        self.database_id = current_app.config.get(\'BASEROW_DATABASE_ID\')
        
        if not all([self.base_url, self.token, self.database_id]):
            raise ValueError("Baserow configuration incomplete. Please set BASEROW_URL, BASEROW_TOKEN, and BASEROW_DATABASE_ID")
        
        self.headers = {
            \'Authorization\': f\'Token {self.token}\'
        }
    
    def _get_table_id(self, table_name):
        """Helper to get table ID from table name"""
        # In a real scenario, you\'d likely cache this or have a mapping
        # For simplicity, we\'ll assume table_name is directly the table_id or we fetch it
        # For now, we\'ll just return the table_name as is, assuming it\'s the ID
        return table_name # Placeholder: In a real app, fetch from Baserow API

    def create_aggregated_data(self, data):
        """Create new aggregated data record in Baserow"""
        try:
            table_id = self._get_table_id("aggregated_data") # Assuming a table named aggregated_data
            url = f"{self.base_url}/api/database/rows/table/{table_id}/?user_field_names=true"
            
            # Map internal data model to Baserow fields
            baserow_data = {
                "project_id": data.get("project_id"),
                "form_id": data.get("form_id"),
                "submission_id": data.get("submission_id"),
                "instance_id": data.get("instance_id"),
                "submission_data": json.dumps(data.get("submission_data")),
                "metadata": json.dumps(data.get("metadata")),
                "submitted_by": data.get("submitted_by"),
                "submitted_at": data.get("submitted_at").isoformat() if data.get("submitted_at") else None,
                "aggregated_at": datetime.utcnow().isoformat(),
                "is_processed": data.get("is_processed", False),
                "processing_status": data.get("processing_status", "raw"),
                "quality_score": data.get("quality_score"),
                "validation_errors": json.dumps(data.get("validation_errors"))
            }
            
            response = requests.post(url, headers=self.headers, json=baserow_data)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            baserow_record = response.json()
            # Map Baserow response back to internal format (simplified)
            return {
                "data_id": baserow_record.get("id"), # Baserow row ID as data_id
                "project_id": baserow_record.get("project_id"),
                "form_id": baserow_record.get("form_id"),
                "submission_id": baserow_record.get("submission_id"),
                "instance_id": baserow_record.get("instance_id"),
                "submitted_by": baserow_record.get("submitted_by"),
                "submitted_at": baserow_record.get("submitted_at"),
                "aggregated_at": baserow_record.get("aggregated_at"),
                "is_processed": baserow_record.get("is_processed"),
                "processing_status": baserow_record.get("processing_status"),
                "quality_score": baserow_record.get("quality_score"),
                "validation_errors": baserow_record.get("validation_errors"),
                "data": json.loads(baserow_record.get("submission_data", "{}")),
                "metadata": json.loads(baserow_record.get("metadata", "{}"))
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Baserow API error during create: {e}")
            raise ValueError(f"Baserow API error: {e}")
        except Exception as e:
            logger.error(f"Error creating aggregated data in Baserow: {str(e)}")
            raise
    
    def get_aggregated_data(self, project_id, filters=None, pagination=None):
        """Retrieve aggregated data from Baserow"""
        try:
            table_id = self._get_table_id("aggregated_data")
            url = f"{self.base_url}/api/database/rows/table/{table_id}/?user_field_names=true"
            
            params = {
                "filter__field_project_id__equal": project_id
            }
            
            if filters:
                if filters.get("form_id"):
                    params["filter__field_form_id__equal"] = filters["form_id"]
                if filters.get("status"):
                    params["filter__field_processing_status__equal"] = filters["status"]
                if filters.get("start_date"):
                    params["filter__field_submitted_at__gte"] = filters["start_date"]
                if filters.get("end_date"):
                    params["filter__field_submitted_at__lte"] = filters["end_date"]
            
            if pagination:
                params["page"] = pagination.get("page", 1)
                params["size"] = pagination.get("limit", 10)
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            baserow_response = response.json()
            results = []
            for row in baserow_response.get("results", []):
                results.append({
                    "data_id": row.get("id"),
                    "project_id": row.get("project_id"),
                    "form_id": row.get("form_id"),
                    "submission_id": row.get("submission_id"),
                    "instance_id": row.get("instance_id"),
                    "submitted_by": row.get("submitted_by"),
                    "submitted_at": row.get("submitted_at"),
                    "aggregated_at": row.get("aggregated_at"),
                    "is_processed": row.get("is_processed"),
                    "processing_status": row.get("processing_status"),
                    "quality_score": row.get("quality_score"),
                    "validation_errors": row.get("validation_errors"),
                    "data": json.loads(row.get("submission_data", "{}")),
                    "metadata": json.loads(row.get("metadata", "{}"))
                })
            
            return {
                "data": results,
                "pagination": {
                    "page": pagination.get("page", 1),
                    "limit": pagination.get("limit", 10),
                    "total": baserow_response.get("count"),
                    "pages": (baserow_response.get("count") + pagination.get("limit", 10) - 1) // pagination.get("limit", 10),
                    "has_next": baserow_response.get("next") is not None,
                    "has_prev": baserow_response.get("previous") is not None
                }
            } if pagination else {"data": results, "total": baserow_response.get("count")}

        except requests.exceptions.RequestException as e:
            logger.error(f"Baserow API error during get: {e}")
            raise ValueError(f"Baserow API error: {e}")
        except Exception as e:
            logger.error(f"Error retrieving aggregated data from Baserow: {str(e)}")
            raise
    
    def update_aggregated_data(self, data_id, updates):
        """Update aggregated data record in Baserow"""
        try:
            table_id = self._get_table_id("aggregated_data")
            url = f"{self.base_url}/api/database/rows/table/{table_id}/{data_id}/?user_field_names=true"
            
            # Map internal updates to Baserow fields
            baserow_updates = {}
            if "project_id" in updates: baserow_updates["project_id"] = updates["project_id"]
            if "form_id" in updates: baserow_updates["form_id"] = updates["form_id"]
            if "submission_id" in updates: baserow_updates["submission_id"] = updates["submission_id"]
            if "instance_id" in updates: baserow_updates["instance_id"] = updates["instance_id"]
            if "submission_data" in updates: baserow_updates["submission_data"] = json.dumps(updates["submission_data"])
            if "metadata" in updates: baserow_updates["metadata"] = json.dumps(updates["metadata"])
            if "submitted_by" in updates: baserow_updates["submitted_by"] = updates["submitted_by"]
            if "submitted_at" in updates: baserow_updates["submitted_at"] = updates["submitted_at"].isoformat() if isinstance(updates["submitted_at"], datetime) else updates["submitted_at"]
            if "aggregated_at" in updates: baserow_updates["aggregated_at"] = updates["aggregated_at"].isoformat() if isinstance(updates["aggregated_at"], datetime) else updates["aggregated_at"]
            if "is_processed" in updates: baserow_updates["is_processed"] = updates["is_processed"]
            if "processing_status" in updates: baserow_updates["processing_status"] = updates["processing_status"]
            if "quality_score" in updates: baserow_updates["quality_score"] = updates["quality_score"]
            if "validation_errors" in updates: baserow_updates["validation_errors"] = json.dumps(updates["validation_errors"])

            response = requests.patch(url, headers=self.headers, json=baserow_updates)
            response.raise_for_status()
            
            baserow_record = response.json()
            return {
                "data_id": baserow_record.get("id"),
                "project_id": baserow_record.get("project_id"),
                "form_id": baserow_record.get("form_id"),
                "submission_id": baserow_record.get("submission_id"),
                "instance_id": baserow_record.get("instance_id"),
                "submitted_by": baserow_record.get("submitted_by"),
                "submitted_at": baserow_record.get("submitted_at"),
                "aggregated_at": baserow_record.get("aggregated_at"),
                "is_processed": baserow_record.get("is_processed"),
                "processing_status": baserow_record.get("processing_status"),
                "quality_score": baserow_record.get("quality_score"),
                "validation_errors": baserow_record.get("validation_errors"),
                "data": json.loads(baserow_record.get("submission_data", "{}")),
                "metadata": json.loads(baserow_record.get("metadata", "{}"))
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Baserow API error during update: {e}")
            raise ValueError(f"Baserow API error: {e}")
        except Exception as e:
            logger.error(f"Error updating aggregated data in Baserow: {str(e)}")
            raise
    
    def delete_aggregated_data(self, data_id):
        """Delete aggregated data record from Baserow"""
        try:
            table_id = self._get_table_id("aggregated_data")
            url = f"{self.base_url}/api/database/rows/table/{table_id}/{data_id}/"
            
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status() # 204 No Content for successful delete
            
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Baserow API error during delete: {e}")
            raise ValueError(f"Baserow API error: {e}")
        except Exception as e:
            logger.error(f"Error deleting aggregated data from Baserow: {str(e)}")
            raise

