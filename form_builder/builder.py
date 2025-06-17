"""
Enhanced Smart Form Builder for ODK MCP System.
Provides drag-and-drop form creation with AI-powered suggestions and real-time preview.
"""

import os
import json
import uuid
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import xlsxwriter
from io import BytesIO

from .config import FORM_BUILDER, FORM_COMPONENTS, AI_INTEGRATION, SUBSCRIPTION_LIMITS
from ..ai_modules.form_recommendations.recommender import EnhancedFormRecommender
from ..ai_modules.nlp.text_analysis import TextAnalyzer


class SmartFormBuilder:
    """
    Smart Form Builder with drag-and-drop interface and AI-powered suggestions.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the smart form builder.
        
        Args:
            config: Configuration dictionary.
        """
        self.config = config or FORM_BUILDER
        self.form_recommender = EnhancedFormRecommender()
        self.text_analyzer = TextAnalyzer()
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                        static_folder=os.path.join(os.path.dirname(__file__), 'static'))
        CORS(self.app)
        
        # Form storage
        self.forms = {}
        self.form_templates = {}
        self.form_versions = {}
        
        # Setup routes
        self._setup_routes()
        self._load_templates()
    
    def _setup_routes(self):
        """Setup Flask routes for the form builder."""
        
        @self.app.route('/')
        def index():
            """Main form builder interface."""
            return render_template('form_builder.html')
        
        @self.app.route('/api/components')
        def get_components():
            """Get available form components."""
            return jsonify({
                "status": "success",
                "components": FORM_COMPONENTS
            })
        
        @self.app.route('/api/form/new', methods=['POST'])
        def create_new_form():
            """Create a new form."""
            try:
                data = request.get_json()
                form_id = str(uuid.uuid4())
                
                form_data = {
                    "id": form_id,
                    "title": data.get("title", "Untitled Form"),
                    "description": data.get("description", ""),
                    "fields": [],
                    "settings": {
                        "language": "en",
                        "theme": "default",
                        "auto_save": True
                    },
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "version": 1,
                        "created_by": data.get("user_id", "anonymous")
                    }
                }
                
                self.forms[form_id] = form_data
                
                return jsonify({
                    "status": "success",
                    "form_id": form_id,
                    "form": form_data
                })
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/form/<form_id>')
        def get_form(form_id):
            """Get form by ID."""
            if form_id not in self.forms:
                return jsonify({
                    "status": "error",
                    "message": "Form not found"
                }), 404
            
            return jsonify({
                "status": "success",
                "form": self.forms[form_id]
            })
        
        @self.app.route('/api/form/<form_id>', methods=['PUT'])
        def update_form(form_id):
            """Update form."""
            try:
                if form_id not in self.forms:
                    return jsonify({
                        "status": "error",
                        "message": "Form not found"
                    }), 404
                
                data = request.get_json()
                form_data = self.forms[form_id]
                
                # Update form data
                if "title" in data:
                    form_data["title"] = data["title"]
                if "description" in data:
                    form_data["description"] = data["description"]
                if "fields" in data:
                    form_data["fields"] = data["fields"]
                if "settings" in data:
                    form_data["settings"].update(data["settings"])
                
                # Update metadata
                form_data["metadata"]["updated_at"] = datetime.now().isoformat()
                form_data["metadata"]["version"] += 1
                
                # Save version if versioning is enabled
                if self.config.get("form_versioning_enabled", True):
                    self._save_form_version(form_id, form_data)
                
                return jsonify({
                    "status": "success",
                    "form": form_data
                })
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/form/<form_id>/field', methods=['POST'])
        def add_field(form_id):
            """Add field to form."""
            try:
                if form_id not in self.forms:
                    return jsonify({
                        "status": "error",
                        "message": "Form not found"
                    }), 404
                
                data = request.get_json()
                field_data = {
                    "id": str(uuid.uuid4()),
                    "type": data.get("type", "text"),
                    "name": data.get("name", f"field_{len(self.forms[form_id]['fields']) + 1}"),
                    "label": data.get("label", ""),
                    "hint": data.get("hint", ""),
                    "required": data.get("required", False),
                    "properties": data.get("properties", {}),
                    "validation": data.get("validation", {}),
                    "position": len(self.forms[form_id]["fields"])
                }
                
                self.forms[form_id]["fields"].append(field_data)
                self.forms[form_id]["metadata"]["updated_at"] = datetime.now().isoformat()
                
                return jsonify({
                    "status": "success",
                    "field": field_data
                })
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/form/<form_id>/field/<field_id>', methods=['PUT'])
        def update_field(form_id, field_id):
            """Update field in form."""
            try:
                if form_id not in self.forms:
                    return jsonify({
                        "status": "error",
                        "message": "Form not found"
                    }), 404
                
                data = request.get_json()
                form_data = self.forms[form_id]
                
                # Find and update field
                field_found = False
                for field in form_data["fields"]:
                    if field["id"] == field_id:
                        field.update(data)
                        field_found = True
                        break
                
                if not field_found:
                    return jsonify({
                        "status": "error",
                        "message": "Field not found"
                    }), 404
                
                form_data["metadata"]["updated_at"] = datetime.now().isoformat()
                
                return jsonify({
                    "status": "success",
                    "message": "Field updated successfully"
                })
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/form/<form_id>/field/<field_id>', methods=['DELETE'])
        def delete_field(form_id, field_id):
            """Delete field from form."""
            try:
                if form_id not in self.forms:
                    return jsonify({
                        "status": "error",
                        "message": "Form not found"
                    }), 404
                
                form_data = self.forms[form_id]
                
                # Find and remove field
                field_found = False
                for i, field in enumerate(form_data["fields"]):
                    if field["id"] == field_id:
                        del form_data["fields"][i]
                        field_found = True
                        break
                
                if not field_found:
                    return jsonify({
                        "status": "error",
                        "message": "Field not found"
                    }), 404
                
                # Update positions
                for i, field in enumerate(form_data["fields"]):
                    field["position"] = i
                
                form_data["metadata"]["updated_at"] = datetime.now().isoformat()
                
                return jsonify({
                    "status": "success",
                    "message": "Field deleted successfully"
                })
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/form/<form_id>/reorder', methods=['POST'])
        def reorder_fields(form_id):
            """Reorder form fields."""
            try:
                if form_id not in self.forms:
                    return jsonify({
                        "status": "error",
                        "message": "Form not found"
                    }), 404
                
                data = request.get_json()
                field_order = data.get("field_order", [])
                
                form_data = self.forms[form_id]
                
                # Reorder fields
                reordered_fields = []
                for field_id in field_order:
                    for field in form_data["fields"]:
                        if field["id"] == field_id:
                            field["position"] = len(reordered_fields)
                            reordered_fields.append(field)
                            break
                
                form_data["fields"] = reordered_fields
                form_data["metadata"]["updated_at"] = datetime.now().isoformat()
                
                return jsonify({
                    "status": "success",
                    "message": "Fields reordered successfully"
                })
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/form/<form_id>/preview')
        def preview_form(form_id):
            """Get form preview."""
            if form_id not in self.forms:
                return jsonify({
                    "status": "error",
                    "message": "Form not found"
                }), 404
            
            form_data = self.forms[form_id]
            
            # Generate preview HTML
            preview_html = self._generate_form_preview(form_data)
            
            return jsonify({
                "status": "success",
                "preview_html": preview_html,
                "form_data": form_data
            })
        
        @self.app.route('/api/form/<form_id>/export/xlsform')
        def export_xlsform(form_id):
            """Export form as XLSForm."""
            try:
                if form_id not in self.forms:
                    return jsonify({
                        "status": "error",
                        "message": "Form not found"
                    }), 404
                
                form_data = self.forms[form_id]
                xlsform_data = self._convert_to_xlsform(form_data)
                
                # Create Excel file
                output = BytesIO()
                workbook = xlsxwriter.Workbook(output)
                
                # Survey sheet
                survey_sheet = workbook.add_worksheet('survey')
                survey_headers = ['type', 'name', 'label', 'hint', 'required', 'constraint', 'relevant', 'default', 'appearance']
                
                for col, header in enumerate(survey_headers):
                    survey_sheet.write(0, col, header)
                
                for row, field in enumerate(xlsform_data['survey'], 1):
                    for col, header in enumerate(survey_headers):
                        survey_sheet.write(row, col, field.get(header, ''))
                
                # Choices sheet
                if xlsform_data['choices']:
                    choices_sheet = workbook.add_worksheet('choices')
                    choices_headers = ['list_name', 'name', 'label']
                    
                    for col, header in enumerate(choices_headers):
                        choices_sheet.write(0, col, header)
                    
                    for row, choice in enumerate(xlsform_data['choices'], 1):
                        for col, header in enumerate(choices_headers):
                            choices_sheet.write(row, col, choice.get(header, ''))
                
                # Settings sheet
                settings_sheet = workbook.add_worksheet('settings')
                settings_headers = ['form_title', 'form_id', 'version', 'default_language']
                
                for col, header in enumerate(settings_headers):
                    settings_sheet.write(0, col, header)
                
                settings_data = xlsform_data['settings']
                for col, header in enumerate(settings_headers):
                    settings_sheet.write(1, col, settings_data.get(header, ''))
                
                workbook.close()
                output.seek(0)
                
                return send_file(
                    output,
                    as_attachment=True,
                    download_name=f"{form_data['title']}.xlsx",
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/ai/suggestions', methods=['POST'])
        def get_ai_suggestions():
            """Get AI-powered form suggestions."""
            try:
                data = request.get_json()
                description = data.get("description", "")
                current_fields = data.get("current_fields", [])
                user_plan = data.get("user_plan", "starter")
                
                # Check subscription limits
                if not SUBSCRIPTION_LIMITS[user_plan].get("ai_suggestions", False):
                    return jsonify({
                        "status": "error",
                        "message": "AI suggestions not available in your plan"
                    }), 403
                
                # Get AI recommendations
                recommendations = self.form_recommender.recommend_similar_forms(
                    description, current_fields, user_plan
                )
                
                # Get field type suggestions
                field_descriptions = data.get("field_descriptions", [])
                if field_descriptions:
                    field_suggestions = self.form_recommender.suggest_field_types(field_descriptions)
                    recommendations["field_suggestions"] = field_suggestions
                
                return jsonify(recommendations)
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/csv/analyze', methods=['POST'])
        def analyze_csv():
            """Analyze CSV file for form structure suggestions."""
            try:
                if 'file' not in request.files:
                    return jsonify({
                        "status": "error",
                        "message": "No file uploaded"
                    }), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({
                        "status": "error",
                        "message": "No file selected"
                    }), 400
                
                # Read CSV file
                try:
                    df = pd.read_csv(file)
                except Exception as e:
                    return jsonify({
                        "status": "error",
                        "message": f"Error reading CSV file: {str(e)}"
                    }), 400
                
                # Analyze CSV structure
                analysis = self.form_recommender.analyze_csv_for_form_structure(df)
                
                return jsonify(analysis)
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/templates')
        def get_templates():
            """Get available form templates."""
            return jsonify({
                "status": "success",
                "templates": list(self.form_templates.values())
            })
        
        @self.app.route('/api/template/<template_id>')
        def get_template(template_id):
            """Get specific template."""
            if template_id not in self.form_templates:
                return jsonify({
                    "status": "error",
                    "message": "Template not found"
                }), 404
            
            return jsonify({
                "status": "success",
                "template": self.form_templates[template_id]
            })
        
        @self.app.route('/api/form/<form_id>/from-template/<template_id>', methods=['POST'])
        def create_from_template(form_id, template_id):
            """Create form from template."""
            try:
                if template_id not in self.form_templates:
                    return jsonify({
                        "status": "error",
                        "message": "Template not found"
                    }), 404
                
                template = self.form_templates[template_id]
                data = request.get_json()
                
                # Create form from template
                form_data = {
                    "id": form_id,
                    "title": data.get("title", template["title"]),
                    "description": data.get("description", template["description"]),
                    "fields": template["fields"].copy(),
                    "settings": template.get("settings", {}).copy(),
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "version": 1,
                        "created_by": data.get("user_id", "anonymous"),
                        "template_id": template_id
                    }
                }
                
                # Assign new IDs to fields
                for field in form_data["fields"]:
                    field["id"] = str(uuid.uuid4())
                
                self.forms[form_id] = form_data
                
                return jsonify({
                    "status": "success",
                    "form": form_data
                })
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
    
    def _generate_form_preview(self, form_data: Dict) -> str:
        """Generate HTML preview of the form."""
        html = f"""
        <div class="form-preview">
            <div class="form-header">
                <h2>{form_data['title']}</h2>
                <p class="form-description">{form_data['description']}</p>
            </div>
            <div class="form-body">
        """
        
        for field in form_data["fields"]:
            html += self._generate_field_html(field)
        
        html += """
            </div>
            <div class="form-footer">
                <button type="submit" class="btn btn-primary">Submit</button>
            </div>
        </div>
        """
        
        return html
    
    def _generate_field_html(self, field: Dict) -> str:
        """Generate HTML for a single field."""
        field_type = field["type"]
        field_id = field["id"]
        field_name = field["name"]
        field_label = field["label"]
        field_hint = field.get("hint", "")
        required = field.get("required", False)
        
        required_attr = "required" if required else ""
        required_mark = "*" if required else ""
        
        html = f"""
        <div class="form-field" data-field-type="{field_type}">
            <label for="{field_id}" class="field-label">
                {field_label}{required_mark}
            </label>
        """
        
        if field_hint:
            html += f'<p class="field-hint">{field_hint}</p>'
        
        if field_type == "text":
            html += f'<input type="text" id="{field_id}" name="{field_name}" class="form-control" {required_attr}>'
        
        elif field_type == "number":
            min_val = field.get("properties", {}).get("min", "")
            max_val = field.get("properties", {}).get("max", "")
            html += f'<input type="number" id="{field_id}" name="{field_name}" class="form-control" {required_attr} min="{min_val}" max="{max_val}">'
        
        elif field_type == "date":
            html += f'<input type="date" id="{field_id}" name="{field_name}" class="form-control" {required_attr}>'
        
        elif field_type == "time":
            html += f'<input type="time" id="{field_id}" name="{field_name}" class="form-control" {required_attr}>'
        
        elif field_type in ["select_one", "radio"]:
            options = field.get("properties", {}).get("options", [])
            if field_type == "select_one":
                html += f'<select id="{field_id}" name="{field_name}" class="form-control" {required_attr}>'
                html += '<option value="">Select an option</option>'
                for option in options:
                    html += f'<option value="{option["value"]}">{option["label"]}</option>'
                html += '</select>'
            else:  # radio
                for option in options:
                    html += f'''
                    <div class="form-check">
                        <input type="radio" id="{field_id}_{option["value"]}" name="{field_name}" value="{option["value"]}" class="form-check-input" {required_attr}>
                        <label for="{field_id}_{option["value"]}" class="form-check-label">{option["label"]}</label>
                    </div>
                    '''
        
        elif field_type in ["select_multiple", "checkbox"]:
            options = field.get("properties", {}).get("options", [])
            for option in options:
                html += f'''
                <div class="form-check">
                    <input type="checkbox" id="{field_id}_{option["value"]}" name="{field_name}[]" value="{option["value"]}" class="form-check-input">
                    <label for="{field_id}_{option["value"]}" class="form-check-label">{option["label"]}</label>
                </div>
                '''
        
        elif field_type == "geopoint":
            html += f'<input type="text" id="{field_id}" name="{field_name}" class="form-control" placeholder="GPS coordinates will be captured" readonly>'
        
        elif field_type == "image":
            html += f'<input type="file" id="{field_id}" name="{field_name}" class="form-control" accept="image/*" capture="camera">'
        
        elif field_type == "audio":
            html += f'<input type="file" id="{field_id}" name="{field_name}" class="form-control" accept="audio/*" capture="microphone">'
        
        else:
            html += f'<input type="text" id="{field_id}" name="{field_name}" class="form-control" {required_attr}>'
        
        html += '</div>'
        
        return html
    
    def _convert_to_xlsform(self, form_data: Dict) -> Dict:
        """Convert form data to XLSForm format."""
        xlsform_data = {
            "survey": [],
            "choices": [],
            "settings": {
                "form_title": form_data["title"],
                "form_id": form_data["id"],
                "version": str(form_data["metadata"]["version"]),
                "default_language": form_data["settings"].get("language", "en")
            }
        }
        
        choice_lists = {}
        
        for field in form_data["fields"]:
            survey_row = {
                "type": field["type"],
                "name": field["name"],
                "label": field["label"],
                "hint": field.get("hint", ""),
                "required": "yes" if field.get("required", False) else "",
                "constraint": field.get("validation", {}).get("constraint", ""),
                "relevant": field.get("validation", {}).get("relevant", ""),
                "default": field.get("properties", {}).get("default", ""),
                "appearance": field.get("properties", {}).get("appearance", "")
            }
            
            # Handle choice fields
            if field["type"] in ["select_one", "select_multiple", "radio", "checkbox"]:
                options = field.get("properties", {}).get("options", [])
                if options:
                    list_name = f"{field['name']}_choices"
                    survey_row["type"] = f"{field['type']} {list_name}"
                    
                    if list_name not in choice_lists:
                        choice_lists[list_name] = []
                        for option in options:
                            choice_lists[list_name].append({
                                "list_name": list_name,
                                "name": option["value"],
                                "label": option["label"]
                            })
            
            xlsform_data["survey"].append(survey_row)
        
        # Add choices to xlsform_data
        for choices in choice_lists.values():
            xlsform_data["choices"].extend(choices)
        
        return xlsform_data
    
    def _save_form_version(self, form_id: str, form_data: Dict) -> None:
        """Save a version of the form."""
        if form_id not in self.form_versions:
            self.form_versions[form_id] = []
        
        version_data = form_data.copy()
        version_data["version_timestamp"] = datetime.now().isoformat()
        
        self.form_versions[form_id].append(version_data)
        
        # Keep only the last N versions
        max_versions = self.config.get("max_versions_per_form", 50)
        if len(self.form_versions[form_id]) > max_versions:
            self.form_versions[form_id] = self.form_versions[form_id][-max_versions:]
    
    def _load_templates(self) -> None:
        """Load predefined form templates."""
        templates = [
            {
                "id": "survey_template",
                "title": "Survey Template",
                "description": "General purpose survey form template",
                "category": "survey",
                "fields": [
                    {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "name": "respondent_name",
                        "label": "Respondent Name",
                        "hint": "Enter your full name",
                        "required": True,
                        "properties": {},
                        "validation": {},
                        "position": 0
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "select_one",
                        "name": "gender",
                        "label": "Gender",
                        "hint": "Select your gender",
                        "required": True,
                        "properties": {
                            "options": [
                                {"value": "male", "label": "Male"},
                                {"value": "female", "label": "Female"},
                                {"value": "other", "label": "Other"},
                                {"value": "prefer_not_to_say", "label": "Prefer not to say"}
                            ]
                        },
                        "validation": {},
                        "position": 1
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "number",
                        "name": "age",
                        "label": "Age",
                        "hint": "Enter your age in years",
                        "required": True,
                        "properties": {
                            "min": 0,
                            "max": 120
                        },
                        "validation": {
                            "constraint": ". >= 0 and . <= 120"
                        },
                        "position": 2
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "select_multiple",
                        "name": "interests",
                        "label": "Areas of Interest",
                        "hint": "Select all that apply",
                        "required": False,
                        "properties": {
                            "options": [
                                {"value": "technology", "label": "Technology"},
                                {"value": "health", "label": "Health"},
                                {"value": "education", "label": "Education"},
                                {"value": "environment", "label": "Environment"},
                                {"value": "sports", "label": "Sports"},
                                {"value": "arts", "label": "Arts & Culture"}
                            ]
                        },
                        "validation": {},
                        "position": 3
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "name": "feedback",
                        "label": "Additional Comments",
                        "hint": "Please share any additional feedback",
                        "required": False,
                        "properties": {
                            "appearance": "multiline"
                        },
                        "validation": {},
                        "position": 4
                    }
                ],
                "settings": {
                    "language": "en",
                    "theme": "default"
                }
            },
            {
                "id": "registration_template",
                "title": "Registration Form",
                "description": "User registration form template",
                "category": "registration",
                "fields": [
                    {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "name": "first_name",
                        "label": "First Name",
                        "hint": "Enter your first name",
                        "required": True,
                        "properties": {},
                        "validation": {},
                        "position": 0
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "name": "last_name",
                        "label": "Last Name",
                        "hint": "Enter your last name",
                        "required": True,
                        "properties": {},
                        "validation": {},
                        "position": 1
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "name": "email",
                        "label": "Email Address",
                        "hint": "Enter a valid email address",
                        "required": True,
                        "properties": {
                            "appearance": "email"
                        },
                        "validation": {
                            "constraint": "regex(., '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$')"
                        },
                        "position": 2
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "name": "phone",
                        "label": "Phone Number",
                        "hint": "Enter your phone number",
                        "required": False,
                        "properties": {
                            "appearance": "tel"
                        },
                        "validation": {},
                        "position": 3
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "date",
                        "name": "birth_date",
                        "label": "Date of Birth",
                        "hint": "Select your date of birth",
                        "required": True,
                        "properties": {},
                        "validation": {
                            "constraint": ". <= today()"
                        },
                        "position": 4
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "geopoint",
                        "name": "location",
                        "label": "Current Location",
                        "hint": "Capture your current GPS location",
                        "required": False,
                        "properties": {},
                        "validation": {},
                        "position": 5
                    }
                ],
                "settings": {
                    "language": "en",
                    "theme": "default"
                }
            },
            {
                "id": "assessment_template",
                "title": "Assessment Form",
                "description": "Assessment or evaluation form template",
                "category": "assessment",
                "fields": [
                    {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "name": "participant_id",
                        "label": "Participant ID",
                        "hint": "Enter unique participant identifier",
                        "required": True,
                        "properties": {},
                        "validation": {},
                        "position": 0
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "date",
                        "name": "assessment_date",
                        "label": "Assessment Date",
                        "hint": "Date of assessment",
                        "required": True,
                        "properties": {
                            "default": "today()"
                        },
                        "validation": {},
                        "position": 1
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "select_one",
                        "name": "assessment_type",
                        "label": "Assessment Type",
                        "hint": "Select the type of assessment",
                        "required": True,
                        "properties": {
                            "options": [
                                {"value": "baseline", "label": "Baseline"},
                                {"value": "midline", "label": "Midline"},
                                {"value": "endline", "label": "Endline"},
                                {"value": "follow_up", "label": "Follow-up"}
                            ]
                        },
                        "validation": {},
                        "position": 2
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "rating",
                        "name": "overall_satisfaction",
                        "label": "Overall Satisfaction",
                        "hint": "Rate overall satisfaction (1-5 scale)",
                        "required": True,
                        "properties": {
                            "min": 1,
                            "max": 5,
                            "step": 1
                        },
                        "validation": {},
                        "position": 3
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "name": "observations",
                        "label": "Observations",
                        "hint": "Record any observations or notes",
                        "required": False,
                        "properties": {
                            "appearance": "multiline"
                        },
                        "validation": {},
                        "position": 4
                    }
                ],
                "settings": {
                    "language": "en",
                    "theme": "default"
                }
            }
        ]
        
        for template in templates:
            self.form_templates[template["id"]] = template
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the form builder application."""
        self.app.run(host=host, port=port, debug=debug)


# Create a global instance
form_builder = SmartFormBuilder()

