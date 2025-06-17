from flask import Blueprint, request, jsonify
from src.models.user import db, Project, User, ProjectUser
from src.utils.auth import auth_required, validate_project_access, validate_user_role_in_project, sanitize_input
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

projects_bp = Blueprint("projects", __name__)

@projects_bp.route("/projects", methods=["POST"])
@auth_required(permissions=["project:create"])
def create_project():
    """Create a new project"""
    try:
        if not request.is_json:
            return jsonify({
                "code": "BAD_REQUEST",
                "message": "Content-Type must be application/json",
                "details": "Project data must be provided as JSON"
            }), 400

        data = sanitize_input(request.get_json())

        required_fields = ["name"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "code": "BAD_REQUEST",
                    "message": f"Missing required field: {field}",
                    "details": f"{field} is required for project creation"
                }), 400

        # Check if project name already exists for this user (or globally if admin)
        existing_project = Project.query.filter_by(name=data["name"]).first()
        if existing_project:
            return jsonify({
                "code": "CONFLICT",
                "message": "Project with this name already exists",
                "details": "Please choose a different project name"
            }), 409

        new_project = Project(
            name=data["name"],
            description=data.get("description", ""),
            created_by=request.current_user_id
        )

        db.session.add(new_project)
        db.session.flush()  # To get the project_id before commit

        # Add creator as project admin
        project_user = ProjectUser(
            project_id=new_project.project_id,
            user_id=request.current_user_id,
            role="admin",
            added_by=request.current_user_id
        )
        db.session.add(project_user)
        db.session.commit()

        logger.info(f"Project {new_project.name} created by {request.current_user.username}")

        return jsonify({
            "project_id": new_project.project_id,
            "name": new_project.name,
            "message": "Project created successfully"
        }), 201

    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to create project",
            "details": str(e)
        }), 500

@projects_bp.route("/projects", methods=["GET"])
@auth_required(permissions=["project:read"])
def list_projects():
    """List projects accessible by the current user"""
    try:
        user = request.current_user
        
        if user.is_admin:
            projects = Project.query.all()
        else:
            # Get projects user is a member of
            project_memberships = ProjectUser.query.filter_by(user_id=user.user_id).all()
            project_ids = [pm.project_id for pm in project_memberships]
            projects = Project.query.filter(Project.project_id.in_(project_ids)).all()

        return jsonify({"projects": [p.to_dict() for p in projects]}), 200

    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to retrieve projects",
            "details": str(e)
        }), 500

@projects_bp.route("/projects/<project_id>", methods=["GET"])
@auth_required(permissions=["project:read"])
def get_project(project_id):
    """Get details of a specific project"""
    try:
        project = Project.query.filter_by(project_id=project_id).first()
        if not project:
            return jsonify({
                "code": "NOT_FOUND",
                "message": "Project not found",
                "details": f"Project {project_id} does not exist"
            }), 404

        # Access check is handled by auth_required decorator
        return jsonify(project.to_dict(include_members=True)), 200

    except Exception as e:
        logger.error(f"Error retrieving project {project_id}: {str(e)}")
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to retrieve project details",
            "details": str(e)
        }), 500

@projects_bp.route("/projects/<project_id>", methods=["PUT"])
@auth_required(permissions=["project:manage"])
def update_project(project_id):
    """Update project details"""
    try:
        project = Project.query.filter_by(project_id=project_id).first()
        if not project:
            return jsonify({
                "code": "NOT_FOUND",
                "message": "Project not found",
                "details": f"Project {project_id} does not exist"
            }), 404

        data = sanitize_input(request.get_json())

        if "name" in data:
            project.name = data["name"]
        if "description" in data:
            project.description = data["description"]
        if "status" in data:
            project.status = data["status"]

        project.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Project {project_id} updated by {request.current_user.username}")
        return jsonify({"message": "Project updated successfully", "project": project.to_dict()}), 200

    except Exception as e:
        logger.error(f"Error updating project {project_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to update project",
            "details": str(e)
        }), 500

@projects_bp.route("/projects/<project_id>", methods=["DELETE"])
@auth_required(permissions=["project:manage"])
def delete_project(project_id):
    """Delete a project"""
    try:
        project = Project.query.filter_by(project_id=project_id).first()
        if not project:
            return jsonify({
                "code": "NOT_FOUND",
                "message": "Project not found",
                "details": f"Project {project_id} does not exist"
            }), 404

        db.session.delete(project)
        db.session.commit()

        logger.info(f"Project {project_id} deleted by {request.current_user.username}")
        return jsonify({"message": "Project deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to delete project",
            "details": str(e)
        }), 500

@projects_bp.route("/projects/<project_id>/users", methods=["POST"])
@auth_required(permissions=["project:manage"])
def add_user_to_project(project_id):
    """Add a user to a project with a specific role"""
    try:
        project = Project.query.filter_by(project_id=project_id).first()
        if not project:
            return jsonify({
                "code": "NOT_FOUND",
                "message": "Project not found",
                "details": f"Project {project_id} does not exist"
            }), 404

        data = sanitize_input(request.get_json())
        user_id = data.get("user_id")
        role = data.get("role")

        if not user_id or not role:
            return jsonify({
                "code": "BAD_REQUEST",
                "message": "Missing required fields",
                "details": "user_id and role are required"
            }), 400

        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return jsonify({
                "code": "NOT_FOUND",
                "message": "User not found",
                "details": f"User {user_id} does not exist"
            }), 404

        if role not in ["admin", "manager", "analyst", "collector", "viewer"]:
            return jsonify({
                "code": "BAD_REQUEST",
                "message": "Invalid role",
                "details": "Role must be one of: admin, manager, analyst, collector, viewer"
            }), 400

        existing_membership = ProjectUser.query.filter_by(project_id=project_id, user_id=user_id).first()
        if existing_membership:
            return jsonify({
                "code": "CONFLICT",
                "message": "User already a member of this project",
                "details": f"User {user_id} is already a member of project {project_id}"
            }), 409

        new_membership = ProjectUser(
            project_id=project_id,
            user_id=user_id,
            role=role,
            added_by=request.current_user_id
        )
        db.session.add(new_membership)
        db.session.commit()

        logger.info(f"User {user_id} added to project {project_id} with role {role} by {request.current_user.username}")
        return jsonify({"message": "User added to project successfully", "membership": new_membership.to_dict()}), 201

    except Exception as e:
        logger.error(f"Error adding user to project {project_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to add user to project",
            "details": str(e)
        }), 500

@projects_bp.route("/projects/<project_id>/users/<user_id>", methods=["DELETE"])
@auth_required(permissions=["project:manage"])
def remove_user_from_project(project_id, user_id):
    """Remove a user from a project"""
    try:
        project = Project.query.filter_by(project_id=project_id).first()
        if not project:
            return jsonify({
                "code": "NOT_FOUND",
                "message": "Project not found",
                "details": f"Project {project_id} does not exist"
            }), 404

        membership = ProjectUser.query.filter_by(project_id=project_id, user_id=user_id).first()
        if not membership:
            return jsonify({
                "code": "NOT_FOUND",
                "message": "User not found in project",
                "details": f"User {user_id} is not a member of project {project_id}"
            }), 404

        # Prevent removing the last admin of a project if it's not the creator
        # Or prevent removing the creator if they are the only admin
        if membership.role == "admin":
            admin_members = ProjectUser.query.filter_by(project_id=project_id, role="admin").all()
            if len(admin_members) == 1 and admin_members[0].user_id == user_id:
                # If the user being removed is the only admin, check if they are the creator
                if project.created_by == user_id:
                    return jsonify({
                        "code": "FORBIDDEN",
                        "message": "Cannot remove project creator if they are the only admin",
                        "details": "Assign another admin or delete the project instead"
                    }), 403
                else:
                    # If the user being removed is the only admin and not the creator, allow removal
                    pass

        db.session.delete(membership)
        db.session.commit()

        logger.info(f"User {user_id} removed from project {project_id} by {request.current_user.username}")
        return jsonify({"message": "User removed from project successfully"}), 200

    except Exception as e:
        logger.error(f"Error removing user from project {project_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to remove user from project",
            "details": str(e)
        }), 500

