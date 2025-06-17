from flask import Blueprint, request, jsonify
from src.models.user import db, User
from src.utils.auth import auth_required, sanitize_input
import logging

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__)

@users_bp.route("/users", methods=["GET"])
@auth_required(permissions=["user:manage"])
def list_users():
    """List all users (Admin only)"""
    try:
        users = User.query.all()
        return jsonify({"users": [user.to_dict() for user in users]}), 200
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to retrieve users",
            "details": str(e)
        }), 500

@users_bp.route("/users/<user_id>/roles", methods=["PUT"])
@auth_required(permissions=["user:manage"])
def update_user_roles(user_id):
    """Update user roles (Admin only)"""
    try:
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return jsonify({
                "code": "NOT_FOUND",
                "message": "User not found",
                "details": f"User {user_id} does not exist"
            }), 404

        data = sanitize_input(request.get_json())
        is_admin = data.get("is_admin")

        if is_admin is None:
            return jsonify({
                "code": "BAD_REQUEST",
                "message": "Missing required field",
                "details": "is_admin field is required"
            }), 400

        user.is_admin = bool(is_admin)
        db.session.commit()

        logger.info(f"User {user_id} admin status updated to {is_admin} by {request.current_user.username}")
        return jsonify({"message": "User roles updated successfully", "user": user.to_dict()}), 200

    except Exception as e:
        logger.error(f"Error updating user roles for {user_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to update user roles",
            "details": str(e)
        }), 500

