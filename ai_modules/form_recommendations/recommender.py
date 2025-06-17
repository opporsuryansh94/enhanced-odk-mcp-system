"""
Enhanced form recommendations system for ODK MCP System.
Provides AI-powered form suggestions, smart skip logic, and field optimization.
"""

import os
import json
import pickle
import numpy as np
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans

from ..config import AI_CONFIG, check_subscription_limit
from ..utils.logging import setup_logger, log_ai_event
from ..nlp.embeddings import TextEmbeddings


class EnhancedFormRecommender:
    """
    Enhanced form recommender that provides AI-powered form suggestions,
    smart skip logic recommendations, and field optimization.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the enhanced form recommender.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["form_recommendations"]
        self.logger = setup_logger("enhanced_form_recommender")
        
        # Initialize components
        self.embeddings = TextEmbeddings()
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.form_embeddings = {}
        self.form_database = []
        self.field_patterns = {}
        
        # Load existing data
        if self.config["enabled"]:
            self._load_form_database()
            self._load_embeddings()
    
    def recommend_similar_forms(self, form_description: str, 
                               form_fields: List[Dict] = None,
                               user_plan: str = "starter",
                               current_usage: int = 0) -> Dict:
        """
        Recommend similar forms based on description and fields.
        
        Args:
            form_description: Description of the desired form.
            form_fields: List of form fields (optional).
            user_plan: User's subscription plan.
            current_usage: Current monthly usage count.
            
        Returns:
            Dictionary with form recommendations.
        """
        if not self.config["enabled"]:
            return {"status": "disabled", "message": "Form recommendations are disabled"}
        
        # Check subscription limits
        if not check_subscription_limit("form_recommendations", user_plan, 
                                      "max_recommendations_per_month", current_usage):
            return {
                "status": "limit_exceeded",
                "message": f"Monthly recommendations limit exceeded for {user_plan} plan"
            }
        
        try:
            recommendations = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "query": form_description,
                "recommendations": []
            }
            
            if self.config.get("ai_powered_suggestions", True):
                # AI-powered recommendations
                ai_recommendations = self._get_ai_recommendations(form_description, form_fields)
                recommendations["recommendations"].extend(ai_recommendations)
            
            # Template-based recommendations
            template_recommendations = self._get_template_recommendations(form_description)
            recommendations["recommendations"].extend(template_recommendations)
            
            # Field-based recommendations
            if form_fields:
                field_recommendations = self._get_field_recommendations(form_fields)
                recommendations["field_suggestions"] = field_recommendations
            
            # Sort by relevance score
            recommendations["recommendations"].sort(
                key=lambda x: x.get("relevance_score", 0), reverse=True
            )
            
            # Limit results
            max_recommendations = self.config.get("max_recommendations", 5)
            recommendations["recommendations"] = recommendations["recommendations"][:max_recommendations]
            
            # Log event
            log_ai_event("form_recommendations", {
                "user_plan": user_plan,
                "query_length": len(form_description),
                "num_recommendations": len(recommendations["recommendations"])
            })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating form recommendations: {e}")
            return {"status": "error", "message": str(e)}
    
    def suggest_smart_skip_logic(self, form_fields: List[Dict]) -> Dict:
        """
        Suggest smart skip logic for form fields.
        
        Args:
            form_fields: List of form fields with their properties.
            
        Returns:
            Dictionary with skip logic suggestions.
        """
        if not self.config.get("smart_skip_logic", True):
            return {"status": "disabled", "message": "Smart skip logic is disabled"}
        
        try:
            suggestions = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "skip_logic_suggestions": []
            }
            
            # Analyze field relationships
            for i, field in enumerate(form_fields):
                field_suggestions = self._analyze_field_for_skip_logic(field, form_fields)
                if field_suggestions:
                    suggestions["skip_logic_suggestions"].extend(field_suggestions)
            
            # Generate conditional logic patterns
            conditional_patterns = self._generate_conditional_patterns(form_fields)
            suggestions["conditional_patterns"] = conditional_patterns
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating skip logic suggestions: {e}")
            return {"status": "error", "message": str(e)}
    
    def suggest_field_types(self, field_descriptions: List[str]) -> Dict:
        """
        Suggest appropriate field types based on descriptions.
        
        Args:
            field_descriptions: List of field descriptions or labels.
            
        Returns:
            Dictionary with field type suggestions.
        """
        if not self.config.get("field_type_suggestions", True):
            return {"status": "disabled", "message": "Field type suggestions are disabled"}
        
        try:
            suggestions = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "field_type_suggestions": []
            }
            
            for description in field_descriptions:
                field_type = self._predict_field_type(description)
                validation_rules = self._suggest_validation_rules(description, field_type)
                
                suggestions["field_type_suggestions"].append({
                    "description": description,
                    "suggested_type": field_type,
                    "confidence": self._calculate_type_confidence(description, field_type),
                    "validation_rules": validation_rules,
                    "alternatives": self._get_alternative_types(description)
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating field type suggestions: {e}")
            return {"status": "error", "message": str(e)}
    
    def analyze_csv_for_form_structure(self, csv_data: pd.DataFrame) -> Dict:
        """
        Analyze CSV data to suggest form structure using AI.
        
        Args:
            csv_data: Pandas DataFrame with CSV data.
            
        Returns:
            Dictionary with form structure suggestions.
        """
        try:
            suggestions = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "suggested_fields": [],
                "form_metadata": {
                    "estimated_completion_time": 0,
                    "complexity_score": 0,
                    "recommended_sections": []
                }
            }
            
            # Analyze each column
            for column in csv_data.columns:
                field_analysis = self._analyze_csv_column(column, csv_data[column])
                suggestions["suggested_fields"].append(field_analysis)
            
            # Generate form metadata
            suggestions["form_metadata"] = self._generate_form_metadata(suggestions["suggested_fields"])
            
            # Suggest form sections
            sections = self._suggest_form_sections(suggestions["suggested_fields"])
            suggestions["form_metadata"]["recommended_sections"] = sections
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error analyzing CSV for form structure: {e}")
            return {"status": "error", "message": str(e)}
    
    def optimize_form_structure(self, form_fields: List[Dict], 
                               usage_data: List[Dict] = None) -> Dict:
        """
        Optimize form structure based on best practices and usage data.
        
        Args:
            form_fields: Current form fields.
            usage_data: Historical usage/submission data (optional).
            
        Returns:
            Dictionary with optimization suggestions.
        """
        try:
            optimizations = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "optimizations": [],
                "estimated_improvement": {}
            }
            
            # Analyze current structure
            structure_analysis = self._analyze_form_structure(form_fields)
            
            # Generate optimization suggestions
            optimizations["optimizations"] = self._generate_optimization_suggestions(
                form_fields, structure_analysis, usage_data
            )
            
            # Estimate improvement metrics
            optimizations["estimated_improvement"] = self._estimate_improvements(
                form_fields, optimizations["optimizations"]
            )
            
            return optimizations
            
        except Exception as e:
            self.logger.error(f"Error optimizing form structure: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_ai_recommendations(self, description: str, fields: List[Dict] = None) -> List[Dict]:
        """Get AI-powered form recommendations."""
        recommendations = []
        
        try:
            # Generate embedding for the description
            query_embedding = self.embeddings.get_embedding(description)
            
            # Compare with stored form embeddings
            similarities = []
            for form_id, form_data in self.form_embeddings.items():
                if "embedding" in form_data:
                    similarity = cosine_similarity(
                        [query_embedding], [form_data["embedding"]]
                    )[0][0]
                    similarities.append((form_id, similarity, form_data))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Generate recommendations
            for form_id, similarity, form_data in similarities[:5]:
                if similarity >= self.config["min_similarity"]:
                    recommendations.append({
                        "type": "ai_powered",
                        "form_id": form_id,
                        "title": form_data.get("title", "Unknown Form"),
                        "description": form_data.get("description", ""),
                        "relevance_score": float(similarity),
                        "fields": form_data.get("fields", []),
                        "usage_count": form_data.get("usage_count", 0),
                        "rating": form_data.get("rating", 0)
                    })
        
        except Exception as e:
            self.logger.error(f"Error in AI recommendations: {e}")
        
        return recommendations
    
    def _get_template_recommendations(self, description: str) -> List[Dict]:
        """Get template-based recommendations."""
        recommendations = []
        
        # Define common form templates
        templates = {
            "survey": {
                "keywords": ["survey", "questionnaire", "feedback", "opinion"],
                "template": {
                    "title": "Survey Template",
                    "description": "General survey form template",
                    "fields": [
                        {"name": "respondent_info", "type": "group", "label": "Respondent Information"},
                        {"name": "questions", "type": "group", "label": "Survey Questions"},
                        {"name": "feedback", "type": "text", "label": "Additional Comments"}
                    ]
                }
            },
            "registration": {
                "keywords": ["registration", "signup", "enrollment", "application"],
                "template": {
                    "title": "Registration Template",
                    "description": "User registration form template",
                    "fields": [
                        {"name": "personal_info", "type": "group", "label": "Personal Information"},
                        {"name": "contact_info", "type": "group", "label": "Contact Information"},
                        {"name": "preferences", "type": "group", "label": "Preferences"}
                    ]
                }
            },
            "assessment": {
                "keywords": ["assessment", "evaluation", "test", "exam", "quiz"],
                "template": {
                    "title": "Assessment Template",
                    "description": "Assessment or evaluation form template",
                    "fields": [
                        {"name": "participant_info", "type": "group", "label": "Participant Information"},
                        {"name": "assessment_items", "type": "group", "label": "Assessment Items"},
                        {"name": "scoring", "type": "group", "label": "Scoring Section"}
                    ]
                }
            },
            "data_collection": {
                "keywords": ["data", "collection", "monitoring", "tracking", "observation"],
                "template": {
                    "title": "Data Collection Template",
                    "description": "General data collection form template",
                    "fields": [
                        {"name": "metadata", "type": "group", "label": "Collection Metadata"},
                        {"name": "observations", "type": "group", "label": "Observations"},
                        {"name": "measurements", "type": "group", "label": "Measurements"}
                    ]
                }
            }
        }
        
        # Match description with templates
        description_lower = description.lower()
        for template_type, template_data in templates.items():
            for keyword in template_data["keywords"]:
                if keyword in description_lower:
                    recommendations.append({
                        "type": "template",
                        "template_type": template_type,
                        "title": template_data["template"]["title"],
                        "description": template_data["template"]["description"],
                        "relevance_score": 0.8,  # High relevance for keyword matches
                        "fields": template_data["template"]["fields"]
                    })
                    break
        
        return recommendations
    
    def _get_field_recommendations(self, fields: List[Dict]) -> List[Dict]:
        """Get field-specific recommendations."""
        recommendations = []
        
        for field in fields:
            field_type = field.get("type", "text")
            field_name = field.get("name", "")
            field_label = field.get("label", "")
            
            # Suggest improvements for each field
            field_suggestions = []
            
            # Validation suggestions
            if field_type in ["integer", "decimal"]:
                field_suggestions.append({
                    "type": "validation",
                    "suggestion": "Add range constraints",
                    "description": f"Consider adding min/max values for {field_name}"
                })
            
            if field_type == "text":
                field_suggestions.append({
                    "type": "validation",
                    "suggestion": "Add length constraints",
                    "description": f"Consider adding character limits for {field_name}"
                })
            
            # Type optimization suggestions
            if "email" in field_name.lower() or "email" in field_label.lower():
                if field_type != "email":
                    field_suggestions.append({
                        "type": "type_optimization",
                        "suggestion": "Change to email type",
                        "description": f"Field {field_name} appears to be an email field"
                    })
            
            if field_suggestions:
                recommendations.append({
                    "field": field_name,
                    "suggestions": field_suggestions
                })
        
        return recommendations
    
    def _analyze_field_for_skip_logic(self, field: Dict, all_fields: List[Dict]) -> List[Dict]:
        """Analyze a field for potential skip logic."""
        suggestions = []
        
        field_type = field.get("type", "text")
        field_name = field.get("name", "")
        
        # Skip logic patterns for different field types
        if field_type in ["select_one", "select_multiple"]:
            # Suggest skip logic based on choices
            choices = field.get("choices", [])
            if choices:
                for choice in choices:
                    choice_value = choice.get("name", "")
                    if choice_value.lower() in ["no", "none", "na", "not_applicable"]:
                        suggestions.append({
                            "trigger_field": field_name,
                            "trigger_value": choice_value,
                            "action": "skip_section",
                            "description": f"Skip related questions when '{choice_value}' is selected",
                            "confidence": 0.8
                        })
        
        elif field_type == "integer":
            # Age-based skip logic
            if "age" in field_name.lower():
                suggestions.append({
                    "trigger_field": field_name,
                    "trigger_condition": "< 18",
                    "action": "skip_adult_questions",
                    "description": "Skip adult-specific questions for minors",
                    "confidence": 0.9
                })
        
        return suggestions
    
    def _generate_conditional_patterns(self, fields: List[Dict]) -> List[Dict]:
        """Generate conditional logic patterns."""
        patterns = []
        
        # Look for common conditional patterns
        field_names = [f.get("name", "") for f in fields]
        
        # Gender-based patterns
        if any("gender" in name.lower() for name in field_names):
            patterns.append({
                "pattern_type": "gender_conditional",
                "description": "Show gender-specific questions based on gender selection",
                "example": "Show pregnancy-related questions only for females"
            })
        
        # Age-based patterns
        if any("age" in name.lower() for name in field_names):
            patterns.append({
                "pattern_type": "age_conditional",
                "description": "Show age-appropriate questions",
                "example": "Show different question sets for different age groups"
            })
        
        # Yes/No branching patterns
        yes_no_fields = [f for f in fields if f.get("type") == "select_one" 
                        and any(choice.get("name", "").lower() in ["yes", "no"] 
                               for choice in f.get("choices", []))]
        
        for field in yes_no_fields:
            patterns.append({
                "pattern_type": "yes_no_branching",
                "field": field.get("name", ""),
                "description": f"Create follow-up questions based on {field.get('label', '')} response"
            })
        
        return patterns
    
    def _predict_field_type(self, description: str) -> str:
        """Predict the most appropriate field type for a description."""
        description_lower = description.lower()
        
        # Define patterns for different field types
        type_patterns = {
            "email": ["email", "e-mail", "electronic mail"],
            "phone": ["phone", "telephone", "mobile", "contact number"],
            "date": ["date", "birthday", "birth date", "when", "day"],
            "time": ["time", "hour", "minute", "when"],
            "integer": ["age", "number", "count", "quantity", "how many"],
            "decimal": ["price", "cost", "amount", "weight", "height", "temperature"],
            "geopoint": ["location", "gps", "coordinates", "where", "place"],
            "image": ["photo", "picture", "image", "take a photo"],
            "audio": ["record", "voice", "audio", "sound"],
            "select_one": ["choose one", "select", "pick", "option"],
            "select_multiple": ["choose all", "select all", "multiple", "check all"],
            "note": ["note", "instruction", "information", "please note"]
        }
        
        # Score each type
        type_scores = {}
        for field_type, patterns in type_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in description_lower:
                    score += 1
            type_scores[field_type] = score
        
        # Return the highest scoring type, default to text
        if type_scores and max(type_scores.values()) > 0:
            return max(type_scores, key=type_scores.get)
        else:
            return "text"
    
    def _suggest_validation_rules(self, description: str, field_type: str) -> List[Dict]:
        """Suggest validation rules for a field."""
        rules = []
        description_lower = description.lower()
        
        if field_type == "integer":
            if "age" in description_lower:
                rules.append({"type": "range", "min": 0, "max": 150})
            elif "year" in description_lower:
                rules.append({"type": "range", "min": 1900, "max": 2030})
        
        elif field_type == "decimal":
            if "percentage" in description_lower or "percent" in description_lower:
                rules.append({"type": "range", "min": 0, "max": 100})
            elif "temperature" in description_lower:
                rules.append({"type": "range", "min": -50, "max": 60})
        
        elif field_type == "text":
            if "name" in description_lower:
                rules.append({"type": "length", "min": 2, "max": 50})
            elif "comment" in description_lower or "description" in description_lower:
                rules.append({"type": "length", "max": 500})
        
        return rules
    
    def _calculate_type_confidence(self, description: str, field_type: str) -> float:
        """Calculate confidence score for field type prediction."""
        # This is a simplified confidence calculation
        # In practice, you might use a trained model
        
        description_lower = description.lower()
        
        # High confidence patterns
        high_confidence_patterns = {
            "email": ["email", "e-mail"],
            "phone": ["phone", "telephone"],
            "date": ["date", "birthday"],
            "geopoint": ["gps", "coordinates", "location"]
        }
        
        if field_type in high_confidence_patterns:
            for pattern in high_confidence_patterns[field_type]:
                if pattern in description_lower:
                    return 0.9
        
        # Medium confidence for partial matches
        return 0.7
    
    def _get_alternative_types(self, description: str) -> List[str]:
        """Get alternative field types for a description."""
        primary_type = self._predict_field_type(description)
        alternatives = []
        
        # Define alternative mappings
        type_alternatives = {
            "text": ["note", "select_one"],
            "integer": ["decimal", "text"],
            "select_one": ["select_multiple", "text"],
            "date": ["text"],
            "geopoint": ["text"]
        }
        
        if primary_type in type_alternatives:
            alternatives = type_alternatives[primary_type]
        
        return alternatives
    
    def _analyze_csv_column(self, column_name: str, column_data: pd.Series) -> Dict:
        """Analyze a CSV column to suggest form field structure."""
        analysis = {
            "name": column_name,
            "label": column_name.replace("_", " ").title(),
            "suggested_type": "text",
            "required": False,
            "validation": [],
            "choices": [],
            "analysis": {}
        }
        
        # Basic statistics
        total_count = len(column_data)
        non_null_count = column_data.notna().sum()
        null_count = total_count - non_null_count
        unique_count = column_data.nunique()
        
        analysis["analysis"] = {
            "total_count": total_count,
            "non_null_count": non_null_count,
            "null_percentage": (null_count / total_count) * 100,
            "unique_count": unique_count,
            "unique_percentage": (unique_count / non_null_count) * 100 if non_null_count > 0 else 0
        }
        
        # Suggest required field
        if null_count / total_count < 0.1:  # Less than 10% missing
            analysis["required"] = True
        
        # Determine field type
        if pd.api.types.is_numeric_dtype(column_data):
            if column_data.dtype == 'int64':
                analysis["suggested_type"] = "integer"
                analysis["validation"].append({
                    "type": "range",
                    "min": int(column_data.min()),
                    "max": int(column_data.max())
                })
            else:
                analysis["suggested_type"] = "decimal"
                analysis["validation"].append({
                    "type": "range",
                    "min": float(column_data.min()),
                    "max": float(column_data.max())
                })
        
        elif pd.api.types.is_datetime64_any_dtype(column_data):
            analysis["suggested_type"] = "date"
        
        else:
            # Categorical analysis
            if unique_count <= 10 and unique_count > 1:
                analysis["suggested_type"] = "select_one"
                value_counts = column_data.value_counts()
                analysis["choices"] = [
                    {"name": str(value), "label": str(value)}
                    for value in value_counts.index
                ]
            else:
                analysis["suggested_type"] = "text"
                if non_null_count > 0:
                    avg_length = column_data.astype(str).str.len().mean()
                    if avg_length > 100:
                        analysis["suggested_type"] = "note"
        
        return analysis
    
    def _generate_form_metadata(self, fields: List[Dict]) -> Dict:
        """Generate form metadata based on suggested fields."""
        metadata = {
            "estimated_completion_time": 0,
            "complexity_score": 0,
            "field_count": len(fields),
            "required_field_count": sum(1 for f in fields if f.get("required", False))
        }
        
        # Estimate completion time (rough calculation)
        time_per_field = {
            "text": 30,  # seconds
            "integer": 15,
            "decimal": 15,
            "select_one": 10,
            "select_multiple": 20,
            "date": 20,
            "note": 60,
            "geopoint": 30
        }
        
        total_time = 0
        for field in fields:
            field_type = field.get("suggested_type", "text")
            total_time += time_per_field.get(field_type, 30)
        
        metadata["estimated_completion_time"] = total_time  # in seconds
        
        # Calculate complexity score (0-100)
        complexity_factors = {
            "field_count": min(len(fields) / 20, 1) * 30,  # Max 30 points
            "required_fields": (metadata["required_field_count"] / len(fields)) * 20,  # Max 20 points
            "field_variety": min(len(set(f.get("suggested_type") for f in fields)) / 8, 1) * 25,  # Max 25 points
            "validation_rules": min(sum(len(f.get("validation", [])) for f in fields) / len(fields), 1) * 25  # Max 25 points
        }
        
        metadata["complexity_score"] = sum(complexity_factors.values())
        
        return metadata
    
    def _suggest_form_sections(self, fields: List[Dict]) -> List[Dict]:
        """Suggest logical sections for organizing form fields."""
        sections = []
        
        # Group fields by similarity
        field_names = [f["name"] for f in fields]
        
        # Common section patterns
        section_patterns = {
            "Personal Information": ["name", "age", "gender", "birth", "personal"],
            "Contact Information": ["email", "phone", "address", "contact"],
            "Demographics": ["age", "gender", "education", "income", "occupation"],
            "Location": ["location", "address", "gps", "coordinates", "place"],
            "Measurements": ["height", "weight", "temperature", "measurement", "size"],
            "Feedback": ["comment", "feedback", "opinion", "suggestion", "note"]
        }
        
        # Assign fields to sections
        assigned_fields = set()
        for section_name, keywords in section_patterns.items():
            section_fields = []
            for field in fields:
                if field["name"] in assigned_fields:
                    continue
                
                field_name_lower = field["name"].lower()
                if any(keyword in field_name_lower for keyword in keywords):
                    section_fields.append(field["name"])
                    assigned_fields.add(field["name"])
            
            if section_fields:
                sections.append({
                    "name": section_name,
                    "fields": section_fields,
                    "estimated_time": len(section_fields) * 25  # seconds
                })
        
        # Add remaining fields to a general section
        remaining_fields = [f["name"] for f in fields if f["name"] not in assigned_fields]
        if remaining_fields:
            sections.append({
                "name": "General Information",
                "fields": remaining_fields,
                "estimated_time": len(remaining_fields) * 25
            })
        
        return sections
    
    def _analyze_form_structure(self, fields: List[Dict]) -> Dict:
        """Analyze current form structure."""
        analysis = {
            "total_fields": len(fields),
            "field_types": {},
            "validation_coverage": 0,
            "organization_score": 0,
            "usability_issues": []
        }
        
        # Count field types
        for field in fields:
            field_type = field.get("type", "unknown")
            analysis["field_types"][field_type] = analysis["field_types"].get(field_type, 0) + 1
        
        # Calculate validation coverage
        fields_with_validation = sum(1 for f in fields if f.get("constraint") or f.get("required"))
        analysis["validation_coverage"] = (fields_with_validation / len(fields)) * 100
        
        # Identify usability issues
        if len(fields) > 30:
            analysis["usability_issues"].append("Form is very long (>30 fields)")
        
        required_fields = sum(1 for f in fields if f.get("required"))
        if required_fields / len(fields) > 0.8:
            analysis["usability_issues"].append("Too many required fields (>80%)")
        
        return analysis
    
    def _generate_optimization_suggestions(self, fields: List[Dict], 
                                         analysis: Dict, 
                                         usage_data: List[Dict] = None) -> List[Dict]:
        """Generate optimization suggestions."""
        suggestions = []
        
        # Field organization suggestions
        if analysis["total_fields"] > 15:
            suggestions.append({
                "type": "organization",
                "priority": "high",
                "title": "Group fields into sections",
                "description": "Consider organizing fields into logical sections to improve user experience",
                "impact": "Reduces cognitive load and improves completion rates"
            })
        
        # Validation suggestions
        if analysis["validation_coverage"] < 50:
            suggestions.append({
                "type": "validation",
                "priority": "medium",
                "title": "Add more validation rules",
                "description": "Consider adding validation rules to improve data quality",
                "impact": "Reduces data entry errors and improves data consistency"
            })
        
        # Field type optimization
        text_fields = analysis["field_types"].get("text", 0)
        if text_fields > len(fields) * 0.7:
            suggestions.append({
                "type": "field_types",
                "priority": "medium",
                "title": "Use more specific field types",
                "description": "Consider using specific field types (date, email, select) instead of text",
                "impact": "Improves data quality and user experience"
            })
        
        return suggestions
    
    def _estimate_improvements(self, fields: List[Dict], optimizations: List[Dict]) -> Dict:
        """Estimate improvement metrics from optimizations."""
        improvements = {
            "completion_rate_increase": 0,
            "data_quality_improvement": 0,
            "user_satisfaction_increase": 0,
            "time_savings": 0
        }
        
        # Rough estimates based on optimization types
        for optimization in optimizations:
            opt_type = optimization.get("type", "")
            priority = optimization.get("priority", "low")
            
            multiplier = {"high": 1.0, "medium": 0.7, "low": 0.4}.get(priority, 0.4)
            
            if opt_type == "organization":
                improvements["completion_rate_increase"] += 15 * multiplier
                improvements["user_satisfaction_increase"] += 20 * multiplier
            
            elif opt_type == "validation":
                improvements["data_quality_improvement"] += 25 * multiplier
            
            elif opt_type == "field_types":
                improvements["data_quality_improvement"] += 15 * multiplier
                improvements["time_savings"] += 10 * multiplier
        
        return improvements
    
    def _load_form_database(self) -> None:
        """Load form database from storage."""
        # This would load from a persistent storage
        # For now, using a simple in-memory database
        self.form_database = []
    
    def _load_embeddings(self) -> None:
        """Load form embeddings from storage."""
        embeddings_path = self.config.get("embeddings_path", "")
        
        if embeddings_path and os.path.exists(embeddings_path):
            try:
                with open(embeddings_path, 'rb') as f:
                    self.form_embeddings = pickle.load(f)
                self.logger.info(f"Loaded {len(self.form_embeddings)} form embeddings")
            except Exception as e:
                self.logger.error(f"Error loading form embeddings: {e}")
                self.form_embeddings = {}
    
    def _save_embeddings(self) -> None:
        """Save form embeddings to storage."""
        embeddings_path = self.config.get("embeddings_path", "")
        
        if embeddings_path:
            try:
                os.makedirs(os.path.dirname(embeddings_path), exist_ok=True)
                with open(embeddings_path, 'wb') as f:
                    pickle.dump(self.form_embeddings, f)
                self.logger.info(f"Saved {len(self.form_embeddings)} form embeddings")
            except Exception as e:
                self.logger.error(f"Error saving form embeddings: {e}")


# Backward compatibility
FormRecommender = EnhancedFormRecommender

