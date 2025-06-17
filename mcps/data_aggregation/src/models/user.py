from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import uuid

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    project_memberships = db.relationship('ProjectUser', back_populates='user', cascade='all, delete-orphan')
    created_projects = db.relationship('Project', back_populates='created_by_user')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.user_id:
            self.user_id = str(uuid.uuid4())
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_sensitive:
            data['projects'] = [pm.project.to_dict() for pm in self.project_memberships if pm.project]
            data['roles'] = list(set([pm.role for pm in self.project_memberships]))
        
        return data
    
    def get_permissions(self):
        """Get user permissions based on roles"""
        permissions = set()
        
        if self.is_admin:
            # Admin users have all permissions
            permissions.update([
                'user:manage', 'project:create', 'project:manage', 'project:read',
                'form:create', 'form:read', 'form:update', 'form:delete',
                'data:submit', 'data:read', 'data:export', 'data:analyze', 'data:report'
            ])
        else:
            # Regular users get permissions based on project roles
            for membership in self.project_memberships:
                if membership.role == 'admin':
                    permissions.update([
                        'project:manage', 'project:read', 'form:create', 'form:read', 
                        'form:update', 'form:delete', 'data:submit', 'data:read', 
                        'data:export', 'data:analyze', 'data:report'
                    ])
                elif membership.role == 'manager':
                    permissions.update([
                        'project:read', 'form:create', 'form:read', 'form:update',
                        'data:submit', 'data:read', 'data:export', 'data:analyze', 'data:report'
                    ])
                elif membership.role == 'analyst':
                    permissions.update([
                        'project:read', 'form:read', 'data:read', 'data:export', 
                        'data:analyze', 'data:report'
                    ])
                elif membership.role == 'collector':
                    permissions.update([
                        'project:read', 'form:read', 'data:submit', 'data:read'
                    ])
                elif membership.role == 'viewer':
                    permissions.update([
                        'project:read', 'form:read', 'data:read'
                    ])
        
        return list(permissions)
    
    def get_project_ids(self):
        """Get list of project IDs user has access to"""
        if self.is_admin:
            # Admin users have access to all projects
            return [p.project_id for p in Project.query.all()]
        else:
            return [pm.project.project_id for pm in self.project_memberships if pm.project]

class Project(db.Model):
    """Project model for organizing forms and data"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='active')  # active, inactive, archived
    created_by = db.Column(db.String(255), db.ForeignKey('users.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by_user = db.relationship('User', back_populates='created_projects')
    members = db.relationship('ProjectUser', back_populates='project', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.project_id:
            self.project_id = str(uuid.uuid4())
    
    def to_dict(self, include_members=False):
        """Convert project to dictionary"""
        data = {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_members:
            data['members'] = [member.to_dict() for member in self.members]
            data['member_count'] = len(self.members)
        
        return data

class ProjectUser(db.Model):
    """Association table for project membership with roles"""
    __tablename__ = 'project_users'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(255), db.ForeignKey('projects.project_id'), nullable=False)
    user_id = db.Column(db.String(255), db.ForeignKey('users.user_id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, manager, analyst, collector, viewer
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by = db.Column(db.String(255), db.ForeignKey('users.user_id'))
    
    # Relationships
    project = db.relationship('Project', back_populates='members')
    user = db.relationship('User', back_populates='project_memberships')
    added_by_user = db.relationship('User', foreign_keys=[added_by])
    
    # Unique constraint to prevent duplicate memberships
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='unique_project_user'),)
    
    def to_dict(self):
        """Convert project membership to dictionary"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role': self.role,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'added_by': self.added_by,
            'user': self.user.to_dict() if self.user else None,
            'project': self.project.to_dict() if self.project else None
        }

