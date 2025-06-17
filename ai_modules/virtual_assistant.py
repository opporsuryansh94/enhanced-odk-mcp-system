"""
Virtual Assistant module for ODK MCP System.
Provides intelligent chatbot assistance for form creation, data analysis, and system guidance.
"""

import os
import json
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime
import re

from ..config import AI_CONFIG, check_subscription_limit
from ..utils.logging import setup_logger, log_ai_event
from ..rag.generator import EnhancedRAGSystem


class VirtualAssistant:
    """
    Virtual Assistant that provides intelligent guidance and support
    for ODK MCP System users through conversational interface.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the virtual assistant.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["virtual_assistant"]
        self.logger = setup_logger("virtual_assistant")
        
        # Initialize components
        self.rag_system = None
        self.conversation_history = {}
        self.user_contexts = {}
        self.response_cache = {}
        
        # Initialize if enabled
        if self.config["enabled"]:
            self._initialize_components()
            self._load_knowledge_base()
    
    def chat(self, message: str, 
             user_id: str,
             context: Dict = None,
             user_plan: str = "starter",
             current_usage: int = 0) -> Dict:
        """
        Process a chat message and generate a response.
        
        Args:
            message: User's message.
            user_id: Unique user identifier.
            context: Additional context information.
            user_plan: User's subscription plan.
            current_usage: Current monthly usage count.
            
        Returns:
            Dictionary with assistant response and metadata.
        """
        if not self.config["enabled"]:
            return {"status": "disabled", "message": "Virtual assistant is disabled"}
        
        # Check subscription limits
        if not check_subscription_limit("virtual_assistant", user_plan, 
                                      "max_queries_per_month", current_usage):
            return {
                "status": "limit_exceeded",
                "message": f"Monthly assistant queries limit exceeded for {user_plan} plan"
            }
        
        try:
            # Initialize user context if needed
            if user_id not in self.user_contexts:
                self.user_contexts[user_id] = {
                    "conversation_history": [],
                    "current_task": None,
                    "preferences": {},
                    "expertise_level": "beginner"
                }
            
            user_context = self.user_contexts[user_id]
            
            # Analyze message intent
            intent = self._analyze_intent(message, user_context)
            
            # Generate response based on intent
            response = self._generate_response(message, intent, user_context, context)
            
            # Update conversation history
            self._update_conversation_history(user_id, message, response)
            
            # Log event
            log_ai_event("virtual_assistant_chat", {
                "user_plan": user_plan,
                "intent": intent["category"],
                "confidence": intent["confidence"],
                "response_type": response["type"]
            })
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "assistant_response": response["text"],
                "intent": intent,
                "suggestions": response.get("suggestions", []),
                "actions": response.get("actions", []),
                "confidence": response["confidence"]
            }
            
        except Exception as e:
            self.logger.error(f"Error processing chat message: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_help_for_task(self, task: str, user_level: str = "beginner") -> Dict:
        """
        Get specific help for a task.
        
        Args:
            task: Task name (e.g., "form_creation", "data_analysis").
            user_level: User's expertise level.
            
        Returns:
            Dictionary with task-specific help.
        """
        try:
            help_content = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "task": task,
                "user_level": user_level,
                "help_content": {},
                "step_by_step": [],
                "tips": [],
                "common_issues": []
            }
            
            # Get task-specific help
            if task == "form_creation":
                help_content.update(self._get_form_creation_help(user_level))
            elif task == "data_analysis":
                help_content.update(self._get_data_analysis_help(user_level))
            elif task == "data_collection":
                help_content.update(self._get_data_collection_help(user_level))
            elif task == "report_generation":
                help_content.update(self._get_report_generation_help(user_level))
            else:
                help_content.update(self._get_general_help(task, user_level))
            
            return help_content
            
        except Exception as e:
            self.logger.error(f"Error getting help for task {task}: {e}")
            return {"status": "error", "message": str(e)}
    
    def suggest_next_steps(self, current_context: Dict) -> Dict:
        """
        Suggest next steps based on current context.
        
        Args:
            current_context: Current user context and system state.
            
        Returns:
            Dictionary with suggested next steps.
        """
        try:
            suggestions = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "context": current_context,
                "suggestions": []
            }
            
            # Analyze current state
            current_step = current_context.get("current_step", "")
            completed_tasks = current_context.get("completed_tasks", [])
            available_data = current_context.get("available_data", {})
            
            # Generate contextual suggestions
            if "form" in current_step.lower():
                suggestions["suggestions"].extend(self._suggest_form_next_steps(current_context))
            elif "data" in current_step.lower():
                suggestions["suggestions"].extend(self._suggest_data_next_steps(current_context))
            elif "analysis" in current_step.lower():
                suggestions["suggestions"].extend(self._suggest_analysis_next_steps(current_context))
            else:
                suggestions["suggestions"].extend(self._suggest_general_next_steps(current_context))
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error suggesting next steps: {e}")
            return {"status": "error", "message": str(e)}
    
    def explain_concept(self, concept: str, context: Dict = None) -> Dict:
        """
        Explain a concept or term.
        
        Args:
            concept: Concept to explain.
            context: Additional context for explanation.
            
        Returns:
            Dictionary with concept explanation.
        """
        try:
            explanation = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "concept": concept,
                "explanation": "",
                "examples": [],
                "related_concepts": [],
                "practical_tips": []
            }
            
            # Get explanation from knowledge base
            if self.rag_system:
                rag_response = self.rag_system.query(
                    f"Explain {concept} in the context of ODK and data collection",
                    context=context
                )
                
                if rag_response["status"] == "success" and rag_response["generated_response"]:
                    explanation["explanation"] = rag_response["generated_response"]
                    explanation["sources"] = rag_response.get("sources", [])
            
            # Add predefined explanations for common concepts
            predefined_explanations = self._get_predefined_explanations()
            if concept.lower() in predefined_explanations:
                predefined = predefined_explanations[concept.lower()]
                explanation.update(predefined)
            
            # If no explanation found, provide a generic response
            if not explanation["explanation"]:
                explanation["explanation"] = f"I don't have specific information about '{concept}' in my knowledge base. Could you provide more context or try rephrasing your question?"
            
            return explanation
            
        except Exception as e:
            self.logger.error(f"Error explaining concept {concept}: {e}")
            return {"status": "error", "message": str(e)}
    
    def _initialize_components(self) -> None:
        """Initialize virtual assistant components."""
        try:
            # Initialize RAG system if knowledge base integration is enabled
            if self.config.get("knowledge_base_integration", True):
                self.rag_system = EnhancedRAGSystem()
            
            self.logger.info("Initialized virtual assistant components")
            
        except Exception as e:
            self.logger.error(f"Error initializing virtual assistant: {e}")
    
    def _load_knowledge_base(self) -> None:
        """Load knowledge base with ODK-specific information."""
        if not self.rag_system:
            return
        
        # Define ODK-specific knowledge documents
        odk_documents = [
            {
                "id": "odk_overview",
                "title": "ODK Overview",
                "type": "documentation",
                "content": """
                Open Data Kit (ODK) is a suite of tools for collecting, managing, and using data in resource-constrained environments.
                It consists of several components:
                - ODK Collect: Mobile app for data collection
                - ODK Central: Server for form and data management
                - XLSForm: Spreadsheet-based form authoring
                - ODK Build: Web-based form designer
                
                ODK is particularly useful for:
                - Survey data collection
                - Monitoring and evaluation
                - Research studies
                - Field data collection in remote areas
                """,
                "source": "official_documentation"
            },
            {
                "id": "xlsform_guide",
                "title": "XLSForm Guide",
                "type": "tutorial",
                "content": """
                XLSForm is a standard for authoring forms using spreadsheet software like Excel or Google Sheets.
                
                Basic structure:
                - survey sheet: Contains questions and their properties
                - choices sheet: Contains answer choices for select questions
                - settings sheet: Contains form metadata
                
                Common question types:
                - text: Free text input
                - integer: Whole numbers
                - decimal: Decimal numbers
                - select_one: Single choice from options
                - select_multiple: Multiple choices from options
                - date: Date picker
                - time: Time picker
                - geopoint: GPS coordinates
                - image: Photo capture
                - audio: Audio recording
                
                Advanced features:
                - Skip logic using relevant column
                - Calculations using calculation column
                - Constraints for validation
                - Groups for organizing questions
                """,
                "source": "official_documentation"
            },
            {
                "id": "data_analysis_basics",
                "title": "Data Analysis Basics",
                "type": "tutorial",
                "content": """
                Data analysis in ODK involves several steps:
                
                1. Data Export: Download data from ODK Central in CSV or other formats
                2. Data Cleaning: Remove duplicates, handle missing values, correct errors
                3. Descriptive Analysis: Calculate summary statistics, frequencies, distributions
                4. Inferential Analysis: Perform statistical tests, correlation analysis
                5. Visualization: Create charts, graphs, and maps
                6. Reporting: Generate reports with findings and recommendations
                
                Common analysis techniques:
                - Frequency analysis for categorical data
                - Mean, median, mode for numerical data
                - Cross-tabulation for relationships between variables
                - Correlation analysis for associations
                - Regression analysis for predictions
                - Geographic analysis for location-based data
                
                Tools for analysis:
                - Excel or Google Sheets for basic analysis
                - R or Python for advanced statistical analysis
                - Tableau or Power BI for visualization
                - SPSS or Stata for statistical analysis
                """,
                "source": "best_practices"
            }
        ]
        
        # Add documents to RAG system
        try:
            self.rag_system.add_documents(odk_documents)
            self.logger.info("Loaded ODK knowledge base")
        except Exception as e:
            self.logger.error(f"Error loading knowledge base: {e}")
    
    def _analyze_intent(self, message: str, user_context: Dict) -> Dict:
        """Analyze user message intent."""
        message_lower = message.lower()
        
        # Define intent patterns
        intent_patterns = {
            "form_creation": [
                "create form", "new form", "design form", "build form", "xlsform",
                "form builder", "survey design", "questionnaire"
            ],
            "data_analysis": [
                "analyze data", "data analysis", "statistics", "correlation",
                "visualization", "chart", "graph", "report"
            ],
            "data_collection": [
                "collect data", "submission", "mobile app", "odk collect",
                "field work", "survey"
            ],
            "help": [
                "help", "how to", "tutorial", "guide", "explain", "what is",
                "how do i", "can you help"
            ],
            "troubleshooting": [
                "error", "problem", "issue", "not working", "bug", "fix",
                "trouble", "difficulty"
            ],
            "explanation": [
                "what is", "explain", "define", "meaning", "concept",
                "understand", "clarify"
            ]
        }
        
        # Score intents
        intent_scores = {}
        for intent, patterns in intent_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in message_lower:
                    score += 1
            intent_scores[intent] = score
        
        # Determine primary intent
        if intent_scores and max(intent_scores.values()) > 0:
            primary_intent = max(intent_scores, key=intent_scores.get)
            confidence = min(intent_scores[primary_intent] / len(intent_patterns[primary_intent]), 1.0)
        else:
            primary_intent = "general"
            confidence = 0.5
        
        return {
            "category": primary_intent,
            "confidence": confidence,
            "all_scores": intent_scores
        }
    
    def _generate_response(self, message: str, intent: Dict, user_context: Dict, context: Dict = None) -> Dict:
        """Generate response based on intent and context."""
        intent_category = intent["category"]
        
        if intent_category == "form_creation":
            return self._generate_form_creation_response(message, user_context, context)
        elif intent_category == "data_analysis":
            return self._generate_data_analysis_response(message, user_context, context)
        elif intent_category == "data_collection":
            return self._generate_data_collection_response(message, user_context, context)
        elif intent_category == "help":
            return self._generate_help_response(message, user_context, context)
        elif intent_category == "troubleshooting":
            return self._generate_troubleshooting_response(message, user_context, context)
        elif intent_category == "explanation":
            return self._generate_explanation_response(message, user_context, context)
        else:
            return self._generate_general_response(message, user_context, context)
    
    def _generate_form_creation_response(self, message: str, user_context: Dict, context: Dict = None) -> Dict:
        """Generate response for form creation queries."""
        response_text = """I can help you create forms! Here are some ways I can assist:

1. **Form Design**: I can guide you through designing effective forms for your data collection needs
2. **XLSForm**: I can help you understand XLSForm syntax and best practices
3. **Question Types**: I can suggest appropriate question types for different data
4. **Skip Logic**: I can help you implement conditional logic in your forms
5. **Validation**: I can suggest validation rules to ensure data quality

What specific aspect of form creation would you like help with?"""
        
        suggestions = [
            "Help me design a survey form",
            "Explain XLSForm syntax",
            "What question types should I use?",
            "How do I add skip logic?",
            "Show me form validation examples"
        ]
        
        actions = [
            {"type": "open_form_builder", "label": "Open Form Builder"},
            {"type": "view_templates", "label": "Browse Form Templates"},
            {"type": "xlsform_tutorial", "label": "XLSForm Tutorial"}
        ]
        
        return {
            "type": "form_creation",
            "text": response_text,
            "confidence": 0.9,
            "suggestions": suggestions,
            "actions": actions
        }
    
    def _generate_data_analysis_response(self, message: str, user_context: Dict, context: Dict = None) -> Dict:
        """Generate response for data analysis queries."""
        response_text = """I can help you analyze your data! Here's what I can assist with:

1. **Descriptive Statistics**: Calculate means, medians, frequencies, and distributions
2. **Data Visualization**: Create charts, graphs, and maps from your data
3. **Correlation Analysis**: Find relationships between variables
4. **Statistical Tests**: Perform t-tests, ANOVA, chi-square tests
5. **Report Generation**: Create comprehensive analysis reports

What type of analysis are you looking to perform?"""
        
        suggestions = [
            "Show me summary statistics",
            "Create visualizations",
            "Find correlations in my data",
            "Generate an analysis report",
            "Help with statistical tests"
        ]
        
        actions = [
            {"type": "open_analysis_tool", "label": "Open Analysis Tool"},
            {"type": "view_data", "label": "View Your Data"},
            {"type": "create_visualization", "label": "Create Visualization"}
        ]
        
        return {
            "type": "data_analysis",
            "text": response_text,
            "confidence": 0.9,
            "suggestions": suggestions,
            "actions": actions
        }
    
    def _generate_data_collection_response(self, message: str, user_context: Dict, context: Dict = None) -> Dict:
        """Generate response for data collection queries."""
        response_text = """I can help you with data collection! Here's how:

1. **Mobile App Setup**: Guide you through setting up ODK Collect
2. **Form Distribution**: Help you share forms with data collectors
3. **Offline Collection**: Explain how to collect data without internet
4. **Data Submission**: Assist with uploading collected data
5. **Quality Control**: Help ensure data quality during collection

What aspect of data collection do you need help with?"""
        
        suggestions = [
            "How to set up ODK Collect?",
            "Share forms with my team",
            "Collect data offline",
            "Check data quality",
            "Troubleshoot submission issues"
        ]
        
        actions = [
            {"type": "setup_guide", "label": "Setup Guide"},
            {"type": "share_form", "label": "Share Form"},
            {"type": "view_submissions", "label": "View Submissions"}
        ]
        
        return {
            "type": "data_collection",
            "text": response_text,
            "confidence": 0.9,
            "suggestions": suggestions,
            "actions": actions
        }
    
    def _generate_help_response(self, message: str, user_context: Dict, context: Dict = None) -> Dict:
        """Generate response for help queries."""
        response_text = """I'm here to help! I can assist you with:

🔹 **Form Creation**: Design surveys and questionnaires
🔹 **Data Collection**: Set up mobile data collection
🔹 **Data Analysis**: Analyze and visualize your data
🔹 **Reporting**: Generate insights and reports
🔹 **Troubleshooting**: Solve technical issues

You can ask me questions like:
- "How do I create a form?"
- "What's the best way to analyze my data?"
- "How do I set up offline data collection?"

What would you like help with today?"""
        
        suggestions = [
            "Getting started guide",
            "Form creation tutorial",
            "Data analysis basics",
            "Mobile app setup",
            "Best practices"
        ]
        
        return {
            "type": "help",
            "text": response_text,
            "confidence": 0.8,
            "suggestions": suggestions
        }
    
    def _generate_troubleshooting_response(self, message: str, user_context: Dict, context: Dict = None) -> Dict:
        """Generate response for troubleshooting queries."""
        response_text = """I can help you troubleshoot issues! Common problems and solutions:

🔧 **Form Issues**:
- Form not loading: Check XLSForm syntax
- Validation errors: Review constraint expressions
- Skip logic not working: Verify relevant conditions

🔧 **Data Collection Issues**:
- App crashes: Update ODK Collect app
- Submission failures: Check internet connection
- Missing data: Review required field settings

🔧 **Analysis Issues**:
- Data not displaying: Check data format
- Charts not generating: Verify data types
- Export problems: Check file permissions

Can you describe the specific issue you're experiencing?"""
        
        suggestions = [
            "Form validation errors",
            "App not working",
            "Data submission problems",
            "Analysis tool issues",
            "Export/import problems"
        ]
        
        return {
            "type": "troubleshooting",
            "text": response_text,
            "confidence": 0.8,
            "suggestions": suggestions
        }
    
    def _generate_explanation_response(self, message: str, user_context: Dict, context: Dict = None) -> Dict:
        """Generate response for explanation queries."""
        # Extract the concept to explain
        concept_patterns = [
            r"what is (.+?)[\?\.]",
            r"explain (.+?)[\?\.]",
            r"define (.+?)[\?\.]",
            r"meaning of (.+?)[\?\.]"
        ]
        
        concept = None
        for pattern in concept_patterns:
            match = re.search(pattern, message.lower())
            if match:
                concept = match.group(1).strip()
                break
        
        if concept:
            explanation_result = self.explain_concept(concept, context)
            if explanation_result["status"] == "success":
                return {
                    "type": "explanation",
                    "text": explanation_result["explanation"],
                    "confidence": 0.9,
                    "concept": concept,
                    "examples": explanation_result.get("examples", []),
                    "related_concepts": explanation_result.get("related_concepts", [])
                }
        
        # Fallback response
        return {
            "type": "explanation",
            "text": "I'd be happy to explain concepts related to ODK and data collection. Could you be more specific about what you'd like me to explain?",
            "confidence": 0.6,
            "suggestions": [
                "What is XLSForm?",
                "Explain skip logic",
                "What is ODK Collect?",
                "Define data validation",
                "Explain correlation analysis"
            ]
        }
    
    def _generate_general_response(self, message: str, user_context: Dict, context: Dict = None) -> Dict:
        """Generate general response."""
        response_text = """I'm your ODK assistant! I can help you with:

• Creating and designing forms
• Setting up data collection
• Analyzing your data
• Generating reports and insights
• Troubleshooting issues

Feel free to ask me anything about ODK, data collection, or analysis. I'm here to make your work easier!"""
        
        suggestions = [
            "How do I get started?",
            "Create a new form",
            "Analyze my data",
            "Set up data collection",
            "Generate a report"
        ]
        
        return {
            "type": "general",
            "text": response_text,
            "confidence": 0.7,
            "suggestions": suggestions
        }
    
    def _update_conversation_history(self, user_id: str, message: str, response: Dict) -> None:
        """Update conversation history for a user."""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {"conversation_history": []}
        
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": message,
            "assistant_response": response["text"],
            "intent": response.get("type", "unknown")
        }
        
        self.user_contexts[user_id]["conversation_history"].append(conversation_entry)
        
        # Keep only last 10 conversations to manage memory
        if len(self.user_contexts[user_id]["conversation_history"]) > 10:
            self.user_contexts[user_id]["conversation_history"] = \
                self.user_contexts[user_id]["conversation_history"][-10:]
    
    def _get_form_creation_help(self, user_level: str) -> Dict:
        """Get form creation help content."""
        if user_level == "beginner":
            return {
                "help_content": {
                    "overview": "Form creation in ODK involves designing surveys using XLSForm format",
                    "key_concepts": ["XLSForm", "Question types", "Skip logic", "Validation"]
                },
                "step_by_step": [
                    "1. Plan your survey questions",
                    "2. Choose appropriate question types",
                    "3. Create XLSForm spreadsheet",
                    "4. Add skip logic if needed",
                    "5. Test your form",
                    "6. Upload to ODK Central"
                ],
                "tips": [
                    "Start with simple question types",
                    "Test your form before deployment",
                    "Use clear, concise question labels",
                    "Group related questions together"
                ]
            }
        else:
            return {
                "help_content": {
                    "overview": "Advanced form creation with complex logic and validation",
                    "key_concepts": ["Advanced skip logic", "Calculations", "Constraints", "Cascading selects"]
                },
                "step_by_step": [
                    "1. Design complex question flows",
                    "2. Implement advanced skip logic",
                    "3. Add calculations and constraints",
                    "4. Set up cascading selects",
                    "5. Optimize form performance",
                    "6. Implement quality controls"
                ],
                "tips": [
                    "Use calculations for dynamic content",
                    "Implement robust validation rules",
                    "Consider form performance with large choice lists",
                    "Use groups for better organization"
                ]
            }
    
    def _get_data_analysis_help(self, user_level: str) -> Dict:
        """Get data analysis help content."""
        return {
            "help_content": {
                "overview": "Data analysis involves exploring, cleaning, and interpreting your collected data",
                "key_concepts": ["Descriptive statistics", "Data visualization", "Statistical tests", "Reporting"]
            },
            "step_by_step": [
                "1. Export data from ODK Central",
                "2. Clean and prepare data",
                "3. Perform descriptive analysis",
                "4. Create visualizations",
                "5. Conduct statistical tests",
                "6. Generate reports"
            ],
            "tips": [
                "Always clean your data first",
                "Use appropriate chart types for your data",
                "Check for outliers and missing values",
                "Document your analysis process"
            ]
        }
    
    def _get_data_collection_help(self, user_level: str) -> Dict:
        """Get data collection help content."""
        return {
            "help_content": {
                "overview": "Data collection involves using mobile devices to gather information in the field",
                "key_concepts": ["ODK Collect", "Offline collection", "Data submission", "Quality control"]
            },
            "step_by_step": [
                "1. Install ODK Collect app",
                "2. Configure server settings",
                "3. Download forms",
                "4. Collect data offline",
                "5. Submit when online",
                "6. Monitor data quality"
            ],
            "tips": [
                "Test forms before field deployment",
                "Train data collectors properly",
                "Monitor submission rates",
                "Have backup plans for technical issues"
            ]
        }
    
    def _get_report_generation_help(self, user_level: str) -> Dict:
        """Get report generation help content."""
        return {
            "help_content": {
                "overview": "Report generation involves creating comprehensive summaries of your analysis",
                "key_concepts": ["Report structure", "Visualizations", "Key findings", "Recommendations"]
            },
            "step_by_step": [
                "1. Define report objectives",
                "2. Analyze your data",
                "3. Create visualizations",
                "4. Write key findings",
                "5. Add recommendations",
                "6. Format and export report"
            ],
            "tips": [
                "Start with an executive summary",
                "Use clear, compelling visualizations",
                "Focus on actionable insights",
                "Tailor content to your audience"
            ]
        }
    
    def _get_general_help(self, task: str, user_level: str) -> Dict:
        """Get general help content."""
        return {
            "help_content": {
                "overview": f"General guidance for {task}",
                "key_concepts": ["Planning", "Implementation", "Best practices", "Quality control"]
            },
            "step_by_step": [
                "1. Define your objectives",
                "2. Plan your approach",
                "3. Implement step by step",
                "4. Test and validate",
                "5. Monitor and adjust",
                "6. Document lessons learned"
            ],
            "tips": [
                "Start with clear objectives",
                "Break complex tasks into smaller steps",
                "Test early and often",
                "Document your process"
            ]
        }
    
    def _suggest_form_next_steps(self, context: Dict) -> List[Dict]:
        """Suggest next steps for form-related tasks."""
        return [
            {
                "action": "test_form",
                "title": "Test Your Form",
                "description": "Test the form on a mobile device before deployment",
                "priority": "high"
            },
            {
                "action": "add_validation",
                "title": "Add Validation Rules",
                "description": "Implement constraints to ensure data quality",
                "priority": "medium"
            },
            {
                "action": "setup_skip_logic",
                "title": "Add Skip Logic",
                "description": "Implement conditional logic for better user experience",
                "priority": "medium"
            }
        ]
    
    def _suggest_data_next_steps(self, context: Dict) -> List[Dict]:
        """Suggest next steps for data-related tasks."""
        return [
            {
                "action": "clean_data",
                "title": "Clean Your Data",
                "description": "Remove duplicates and handle missing values",
                "priority": "high"
            },
            {
                "action": "create_visualizations",
                "title": "Create Visualizations",
                "description": "Generate charts and graphs to explore your data",
                "priority": "medium"
            },
            {
                "action": "run_analysis",
                "title": "Run Statistical Analysis",
                "description": "Perform statistical tests and correlation analysis",
                "priority": "medium"
            }
        ]
    
    def _suggest_analysis_next_steps(self, context: Dict) -> List[Dict]:
        """Suggest next steps for analysis-related tasks."""
        return [
            {
                "action": "generate_report",
                "title": "Generate Report",
                "description": "Create a comprehensive analysis report",
                "priority": "high"
            },
            {
                "action": "share_insights",
                "title": "Share Insights",
                "description": "Share your findings with stakeholders",
                "priority": "medium"
            },
            {
                "action": "plan_followup",
                "title": "Plan Follow-up",
                "description": "Plan additional data collection or analysis",
                "priority": "low"
            }
        ]
    
    def _suggest_general_next_steps(self, context: Dict) -> List[Dict]:
        """Suggest general next steps."""
        return [
            {
                "action": "explore_features",
                "title": "Explore Features",
                "description": "Learn about additional system capabilities",
                "priority": "medium"
            },
            {
                "action": "get_training",
                "title": "Get Training",
                "description": "Access tutorials and training materials",
                "priority": "medium"
            },
            {
                "action": "join_community",
                "title": "Join Community",
                "description": "Connect with other ODK users",
                "priority": "low"
            }
        ]
    
    def _get_predefined_explanations(self) -> Dict:
        """Get predefined explanations for common concepts."""
        return {
            "xlsform": {
                "explanation": "XLSForm is a standard for authoring forms using spreadsheet software like Excel or Google Sheets. It allows you to create complex forms with skip logic, calculations, and validation rules using a simple spreadsheet format.",
                "examples": [
                    "Creating a survey with multiple question types",
                    "Adding skip logic based on previous answers",
                    "Implementing data validation rules"
                ],
                "related_concepts": ["ODK Build", "Form design", "Skip logic", "Data validation"],
                "practical_tips": [
                    "Start with the survey sheet for questions",
                    "Use the choices sheet for select options",
                    "Test your form before deployment"
                ]
            },
            "skip logic": {
                "explanation": "Skip logic allows you to show or hide questions based on previous answers. This creates a dynamic form experience where users only see relevant questions.",
                "examples": [
                    "Show pregnancy questions only for females",
                    "Skip detailed questions if user answers 'No' to main question",
                    "Show different question sets based on age groups"
                ],
                "related_concepts": ["XLSForm", "Relevant column", "Conditional logic"],
                "practical_tips": [
                    "Use the 'relevant' column in XLSForm",
                    "Test all possible paths through your form",
                    "Keep logic simple and clear"
                ]
            },
            "data validation": {
                "explanation": "Data validation ensures that collected data meets specific criteria or constraints. It helps maintain data quality by preventing invalid entries.",
                "examples": [
                    "Age must be between 0 and 120",
                    "Email must contain @ symbol",
                    "Date must be in the past"
                ],
                "related_concepts": ["Constraints", "Data quality", "Form design"],
                "practical_tips": [
                    "Use the 'constraint' column in XLSForm",
                    "Provide clear error messages",
                    "Balance validation with user experience"
                ]
            }
        }


# Create a global instance for easy access
virtual_assistant = VirtualAssistant()

