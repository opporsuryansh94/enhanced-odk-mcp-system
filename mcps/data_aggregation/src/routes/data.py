from flask import Blueprint, request, jsonify, current_app
from src.models.data import AggregatedData, DataAnalysisResult
from src.utils.auth import auth_required
from src.utils.database import get_database_adapter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

data_bp = Blueprint("data", __name__)

@data_bp.route("/projects/<project_id>/data", methods=["POST"])
@auth_required(permissions=["data:submit"])
def add_aggregated_data(project_id):
    """Add aggregated data (e.g., from Data Collection MCP)"""
    try:
        if not request.is_json:
            return jsonify({
                "code": "BAD_REQUEST",
                "message": "Content-Type must be application/json",
                "details": "Data must be provided as JSON"
            }), 400

        data = request.get_json()

        required_fields = ["form_id", "submission_id", "instance_id", "submission_data", "submitted_by", "submitted_at"]
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "code": "BAD_REQUEST",
                    "message": f"Missing required field: {field}",
                    "details": f"{field} is required for aggregated data"
                }), 400

        # Convert submitted_at to datetime object
        try:
            data["submitted_at"] = datetime.fromisoformat(data["submitted_at"]) if isinstance(data["submitted_at"], str) else data["submitted_at"]
        except ValueError:
            return jsonify({
                "code": "BAD_REQUEST",
                "message": "Invalid submitted_at format",
                "details": "Use ISO format: YYYY-MM-DDTHH:MM:SS"
            }), 400

        # Add project_id to data
        data["project_id"] = project_id

        db_adapter = get_database_adapter()
        aggregated_record = db_adapter.create_aggregated_data(data)

        logger.info(f"Aggregated data for submission {data["submission_id"]} added to project {project_id}")
        return jsonify({"message": "Data added successfully", "data": aggregated_record}), 201

    except Exception as e:
        logger.error(f"Error adding aggregated data: {str(e)}")
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to add aggregated data",
            "details": str(e)
        }), 500

@data_bp.route("/projects/<project_id>/data", methods=["GET"])
@auth_required(permissions=["data:read"])
def get_aggregated_data(project_id):
    """Retrieve aggregated data for a project"""
    try:
        filters = {
            "form_id": request.args.get("form_id"),
            "status": request.args.get("status"),
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
        }
        pagination = {
            "page": request.args.get("page", 1, type=int),
            "limit": request.args.get("limit", 10, type=int),
        }

        db_adapter = get_database_adapter()
        result = db_adapter.get_aggregated_data(project_id, filters, pagination)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error retrieving aggregated data for project {project_id}: {str(e)}")
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to retrieve aggregated data",
            "details": str(e)
        }), 500

@data_bp.route("/projects/<project_id>/data/export", methods=["POST"])
@auth_required(permissions=["data:export"])
def export_aggregated_data(project_id):
    """Export aggregated data in various formats (CSV, JSON)"""
    try:
        if not request.is_json:
            return jsonify({
                "code": "BAD_REQUEST",
                "message": "Content-Type must be application/json",
                "details": "Export options must be provided as JSON"
            }), 400

        options = request.get_json()
        export_format = options.get("format", "json").lower()
        filters = options.get("filters", {})

        db_adapter = get_database_adapter()
        # Retrieve all data for export (no pagination)
        data_records = db_adapter.get_aggregated_data(project_id, filters, pagination=None)["data"]

        if export_format == "json":
            return jsonify(data_records), 200
        elif export_format == "csv":
            # Convert list of dicts to CSV string
            if not data_records:
                return current_app.response_class("", mimetype="text/csv")

            import pandas as pd
            df = pd.DataFrame(data_records)
            csv_output = df.to_csv(index=False)
            return current_app.response_class(
                csv_output,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=project_{project_id}_data.csv"
                }
            )
        else:
            return jsonify({
                "code": "BAD_REQUEST",
                "message": "Unsupported export format",
                "details": "Supported formats are json and csv"
            }), 400

    except Exception as e:
        logger.error(f"Error exporting data for project {project_id}: {str(e)}")
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to export data",
            "details": str(e)
        }), 500

@data_bp.route("/projects/<project_id>/data/analyze/<analysis_type>", methods=["POST"])
@auth_required(permissions=["data:analyze"])
def trigger_analysis(project_id, analysis_type):
    """Trigger data analysis (descriptive, inferential, exploration)"""
    try:
        if analysis_type not in ["descriptive", "inferential", "exploration", "clean", "report"]:
            return jsonify({
                "code": "BAD_REQUEST",
                "message": "Invalid analysis type",
                "details": "Supported types: descriptive, inferential, exploration, clean, report"
            }), 400

        # In a real multi-agent system, this would trigger a message to the relevant agent
        # For now, we simulate the call and return a placeholder response.
        logger.info(f"Triggering {analysis_type} analysis for project {project_id}")

        # Example: Get data for analysis
        filters = request.get_json().get("filters", {}) if request.is_json else {}
        db_adapter = get_database_adapter()
        data_records = db_adapter.get_aggregated_data(project_id, filters, pagination=None)["data"]

        # Simulate analysis result storage
        # This would be done by the analysis agent and then stored back here
        analysis_result_data = {
            "project_id": project_id,
            "analysis_type": analysis_type,
            "analysis_name": f"{analysis_type.capitalize()} Analysis for Project {project_id}",
            "parameters": filters,
            "results": {"message": f"Simulated {analysis_type} analysis result for {len(data_records)} records"},
            "created_by": request.current_user_id,
            "data_count": len(data_records)
        }

        # Store analysis result
        new_analysis_result = DataAnalysisResult(**analysis_result_data)
        db.session.add(new_analysis_result)
        db.session.commit()

        return jsonify({
            "message": f"Successfully triggered {analysis_type} analysis",
            "analysis_result_id": new_analysis_result.result_id,
            "simulated_result": new_analysis_result.to_dict(include_results=True)
        }), 200

    except Exception as e:
        logger.error(f"Error triggering {analysis_type} analysis for project {project_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": f"Failed to trigger {analysis_type} analysis",
            "details": str(e)
        }), 500

@data_bp.route("/projects/<project_id>/analysis-results", methods=["GET"])
@auth_required(permissions=["data:read"])
def list_analysis_results(project_id):
    """List analysis results for a project"""
    try:
        analysis_type = request.args.get("analysis_type")
        query = DataAnalysisResult.query.filter_by(project_id=project_id)

        if analysis_type:
            query = query.filter_by(analysis_type=analysis_type)

        results = query.order_by(DataAnalysisResult.created_at.desc()).all()

        return jsonify({"analysis_results": [r.to_dict(include_results=False) for r in results]}), 200

    except Exception as e:
        logger.error(f"Error listing analysis results for project {project_id}: {str(e)}")
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to retrieve analysis results",
            "details": str(e)
        }), 500

@data_bp.route("/projects/<project_id>/analysis-results/<result_id>", methods=["GET"])
@auth_required(permissions=["data:read"])
def get_analysis_result(project_id, result_id):
    """Get a specific analysis result"""
    try:
        result = DataAnalysisResult.query.filter_by(project_id=project_id, result_id=result_id).first()
        if not result:
            return jsonify({
                "code": "NOT_FOUND",
                "message": "Analysis result not found",
                "details": f"Analysis result {result_id} not found in project {project_id}"
            }), 404

        return jsonify(result.to_dict(include_results=True)), 200

    except Exception as e:
        logger.error(f"Error retrieving analysis result {result_id}: {str(e)}")
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to retrieve analysis result",
            "details": str(e)
        }), 500

