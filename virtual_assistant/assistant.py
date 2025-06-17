"""
Enhanced Virtual Assistant for ODK MCP System.
Provides intelligent user guidance, onboarding, and contextual help using RAG and NLP.
"""

import os
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# Database Models
Base = declarative_base()


class ConversationStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"


class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class OnboardingStep(Enum):
    WELCOME = "welcome"
    PROFILE_SETUP = "profile_setup"
    PROJECT_CREATION = "project_creation"
    FORM_TUTORIAL = "form_tutorial"
    DATA_COLLECTION = "data_collection"
    ANALYTICS_INTRO = "analytics_intro"
    COMPLETION = "completion"


@dataclass
class AssistantResponse:
    message: str
    suggestions: List[str] = None
    actions: List[Dict[str, Any]] = None
    context: Dict[str, Any] = None
    confidence: float = 0.0


class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    session_id = Column(String)
    
    # Conversation details
    title = Column(String)
    context = Column(JSON, default=dict)
    status = Column(String, default=ConversationStatus.ACTIVE.value)
    
    # Metadata
    total_messages = Column(Integer, default=0)
    satisfaction_rating = Column(Integer)  # 1-5 scale
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)


class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(String, primary_key=True)
    conversation_id = Column(String, nullable=False)
    
    # Message details
    message_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    
    # AI processing
    intent = Column(String)
    entities = Column(JSON, default=list)
    confidence = Column(Float)
    
    # Response details
    response_time_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'
    
    id = Column(String, primary_key=True)
    
    # Content details
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    tags = Column(JSON, default=list)
    
    # Search optimization
    content_vector = Column(Text)  # Serialized vector
    keywords = Column(JSON, default=list)
    
    # Usage statistics
    view_count = Column(Integer, default=0)
    helpful_votes = Column(Integer, default=0)
    unhelpful_votes = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OnboardingProgress(Base):
    __tablename__ = 'onboarding_progress'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)
    
    # Progress tracking
    current_step = Column(String, default=OnboardingStep.WELCOME.value)
    completed_steps = Column(JSON, default=list)
    step_data = Column(JSON, default=dict)
    
    # Status
    is_completed = Column(Boolean, default=False)
    completion_percentage = Column(Float, default=0.0)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    last_activity_at = Column(DateTime, default=datetime.utcnow)


class VirtualAssistant:
    """
    Intelligent virtual assistant with RAG capabilities, onboarding guidance, and contextual help.
    """
    
    def __init__(self, database_url: str = "sqlite:///virtual_assistant.db"):
        """
        Initialize the virtual assistant.
        
        Args:
            database_url: Database connection URL.
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize NLP components
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Knowledge base
        self.knowledge_vectors = None
        self.knowledge_data = []
        
        # Intent patterns
        self.intent_patterns = {
            'greeting': [
                r'\b(hi|hello|hey|good morning|good afternoon|good evening)\b',
                r'\bwhat\'s up\b',
                r'\bhow are you\b'
            ],
            'form_creation': [
                r'\b(create|make|build|design)\s+(form|survey|questionnaire)\b',
                r'\bhow to create\b.*\bform\b',
                r'\bnew form\b'
            ],
            'data_collection': [
                r'\b(collect|gather|submit)\s+(data|responses|submissions)\b',
                r'\bhow to collect\b',
                r'\bsubmit form\b'
            ],
            'analytics': [
                r'\b(analyze|analysis|analytics|statistics|insights)\b',
                r'\bview data\b',
                r'\breports?\b'
            ],
            'help': [
                r'\b(help|support|assistance|guide|tutorial)\b',
                r'\bhow do i\b',
                r'\bwhat is\b',
                r'\bcan you\b'
            ],
            'onboarding': [
                r'\b(getting started|setup|onboard|tutorial|guide)\b',
                r'\bnew user\b',
                r'\bfirst time\b'
            ],
            'troubleshooting': [
                r'\b(error|problem|issue|bug|not working|broken)\b',
                r'\bwhy is\b',
                r'\btrouble\b'
            ]
        }
        
        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self._setup_routes()
        self._setup_socket_events()
        self._initialize_knowledge_base()
    
    def _setup_routes(self):
        """Setup Flask routes for the virtual assistant."""
        
        @self.app.route('/api/assistant/chat', methods=['POST'])
        def chat():
            """Handle chat messages."""
            try:
                data = request.get_json()
                user_id = data.get('user_id')
                message = data.get('message')
                conversation_id = data.get('conversation_id')
                context = data.get('context', {})
                
                if not user_id or not message:
                    return jsonify({
                        "status": "error",
                        "message": "User ID and message are required"
                    }), 400
                
                # Process message
                response = self.process_message(
                    user_id=user_id,
                    message=message,
                    conversation_id=conversation_id,
                    context=context
                )
                
                return jsonify({
                    "status": "success",
                    "response": asdict(response),
                    "conversation_id": conversation_id or self._get_or_create_conversation(user_id)
                })
                
            except Exception as e:
                self.logger.error(f"Chat error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/assistant/onboarding/<user_id>')
        def get_onboarding_status(user_id):
            """Get user's onboarding status."""
            try:
                with self.SessionLocal() as db:
                    progress = db.query(OnboardingProgress).filter(
                        OnboardingProgress.user_id == user_id
                    ).first()
                    
                    if not progress:
                        # Create new onboarding progress
                        progress = OnboardingProgress(
                            id=str(uuid.uuid4()),
                            user_id=user_id
                        )
                        db.add(progress)
                        db.commit()
                    
                    return jsonify({
                        "status": "success",
                        "onboarding": {
                            "current_step": progress.current_step,
                            "completed_steps": progress.completed_steps,
                            "completion_percentage": progress.completion_percentage,
                            "is_completed": progress.is_completed,
                            "step_data": progress.step_data
                        }
                    })
                    
            except Exception as e:
                self.logger.error(f"Onboarding status error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/assistant/onboarding/<user_id>/step', methods=['POST'])
        def update_onboarding_step(user_id):
            """Update user's onboarding step."""
            try:
                data = request.get_json()
                step = data.get('step')
                step_data = data.get('step_data', {})
                
                with self.SessionLocal() as db:
                    progress = db.query(OnboardingProgress).filter(
                        OnboardingProgress.user_id == user_id
                    ).first()
                    
                    if not progress:
                        return jsonify({
                            "status": "error",
                            "message": "Onboarding progress not found"
                        }), 404
                    
                    # Update progress
                    if step not in progress.completed_steps:
                        progress.completed_steps.append(progress.current_step)
                    
                    progress.current_step = step
                    progress.step_data.update(step_data)
                    progress.last_activity_at = datetime.utcnow()
                    
                    # Calculate completion percentage
                    total_steps = len(OnboardingStep)
                    progress.completion_percentage = (len(progress.completed_steps) / total_steps) * 100
                    
                    # Check if completed
                    if step == OnboardingStep.COMPLETION.value:
                        progress.is_completed = True
                        progress.completed_at = datetime.utcnow()
                    
                    db.commit()
                    
                    return jsonify({
                        "status": "success",
                        "message": "Onboarding step updated successfully"
                    })
                    
            except Exception as e:
                self.logger.error(f"Onboarding step update error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/assistant/knowledge/search')
        def search_knowledge():
            """Search knowledge base."""
            try:
                query = request.args.get('q', '')
                category = request.args.get('category')
                limit = int(request.args.get('limit', 10))
                
                if not query:
                    return jsonify({
                        "status": "error",
                        "message": "Search query is required"
                    }), 400
                
                results = self.search_knowledge_base(query, category, limit)
                
                return jsonify({
                    "status": "success",
                    "results": results
                })
                
            except Exception as e:
                self.logger.error(f"Knowledge search error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/assistant/feedback', methods=['POST'])
        def submit_feedback():
            """Submit feedback for assistant response."""
            try:
                data = request.get_json()
                conversation_id = data.get('conversation_id')
                rating = data.get('rating')  # 1-5 scale
                feedback = data.get('feedback', '')
                
                with self.SessionLocal() as db:
                    conversation = db.query(Conversation).filter(
                        Conversation.id == conversation_id
                    ).first()
                    
                    if conversation:
                        conversation.satisfaction_rating = rating
                        db.commit()
                
                return jsonify({
                    "status": "success",
                    "message": "Feedback submitted successfully"
                })
                
            except Exception as e:
                self.logger.error(f"Feedback submission error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
    
    def _setup_socket_events(self):
        """Setup Socket.IO events for real-time chat."""
        
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info('Client connected')
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info('Client disconnected')
        
        @self.socketio.on('join_conversation')
        def handle_join_conversation(data):
            conversation_id = data.get('conversation_id')
            if conversation_id:
                join_room(conversation_id)
                emit('joined_conversation', {'conversation_id': conversation_id})
        
        @self.socketio.on('leave_conversation')
        def handle_leave_conversation(data):
            conversation_id = data.get('conversation_id')
            if conversation_id:
                leave_room(conversation_id)
                emit('left_conversation', {'conversation_id': conversation_id})
        
        @self.socketio.on('send_message')
        def handle_send_message(data):
            try:
                user_id = data.get('user_id')
                message = data.get('message')
                conversation_id = data.get('conversation_id')
                context = data.get('context', {})
                
                # Process message
                response = self.process_message(
                    user_id=user_id,
                    message=message,
                    conversation_id=conversation_id,
                    context=context
                )
                
                # Emit response to conversation room
                if conversation_id:
                    emit('message_response', {
                        'response': asdict(response),
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=conversation_id)
                
            except Exception as e:
                self.logger.error(f"Socket message error: {str(e)}")
                emit('error', {'message': str(e)})
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base with default content."""
        default_knowledge = [
            {
                "title": "Getting Started with ODK MCP System",
                "content": "Welcome to ODK MCP System! This comprehensive platform helps you create forms, collect data, and analyze results. Start by creating your first project and designing a form using our intuitive form builder.",
                "category": "getting_started",
                "tags": ["onboarding", "basics", "introduction"]
            },
            {
                "title": "Creating Your First Form",
                "content": "To create a form: 1) Navigate to Forms section, 2) Click 'New Form', 3) Use the drag-and-drop form builder to add fields, 4) Configure validation rules, 5) Preview and publish your form.",
                "category": "forms",
                "tags": ["form_creation", "tutorial", "basics"]
            },
            {
                "title": "Data Collection Best Practices",
                "content": "For effective data collection: Use clear field labels, add help text for complex questions, implement validation rules, test forms before deployment, and train data collectors on proper usage.",
                "category": "data_collection",
                "tags": ["best_practices", "data_quality", "training"]
            },
            {
                "title": "Understanding Analytics Dashboard",
                "content": "The analytics dashboard provides real-time insights into your data. View submission statistics, generate visualizations, export reports, and set up automated alerts for data quality issues.",
                "category": "analytics",
                "tags": ["dashboard", "visualization", "reporting"]
            },
            {
                "title": "Troubleshooting Common Issues",
                "content": "Common issues and solutions: Form not loading - check internet connection; Data not syncing - verify permissions; Export failing - check file format settings; Login problems - reset password or contact support.",
                "category": "troubleshooting",
                "tags": ["problems", "solutions", "support"]
            }
        ]
        
        try:
            with self.SessionLocal() as db:
                # Check if knowledge base is already populated
                existing_count = db.query(KnowledgeBase).count()
                
                if existing_count == 0:
                    for item in default_knowledge:
                        kb_item = KnowledgeBase(
                            id=str(uuid.uuid4()),
                            title=item["title"],
                            content=item["content"],
                            category=item["category"],
                            tags=item["tags"]
                        )
                        db.add(kb_item)
                    
                    db.commit()
                    self.logger.info("Knowledge base initialized with default content")
                
                # Load knowledge base for vector search
                self._load_knowledge_vectors()
                
        except Exception as e:
            self.logger.error(f"Knowledge base initialization error: {str(e)}")
    
    def _load_knowledge_vectors(self):
        """Load and vectorize knowledge base content."""
        try:
            with self.SessionLocal() as db:
                knowledge_items = db.query(KnowledgeBase).filter(
                    KnowledgeBase.is_active == True
                ).all()
                
                if knowledge_items:
                    # Prepare text data
                    texts = []
                    self.knowledge_data = []
                    
                    for item in knowledge_items:
                        combined_text = f"{item.title} {item.content} {' '.join(item.tags)}"
                        texts.append(combined_text)
                        self.knowledge_data.append({
                            "id": item.id,
                            "title": item.title,
                            "content": item.content,
                            "category": item.category,
                            "tags": item.tags
                        })
                    
                    # Create vectors
                    self.knowledge_vectors = self.vectorizer.fit_transform(texts)
                    self.logger.info(f"Loaded {len(knowledge_items)} knowledge base items")
                
        except Exception as e:
            self.logger.error(f"Knowledge vector loading error: {str(e)}")
    
    def process_message(
        self,
        user_id: str,
        message: str,
        conversation_id: str = None,
        context: Dict[str, Any] = None
    ) -> AssistantResponse:
        """
        Process user message and generate intelligent response.
        
        Args:
            user_id: User identifier.
            message: User message.
            conversation_id: Conversation identifier.
            context: Additional context information.
            
        Returns:
            Assistant response with message, suggestions, and actions.
        """
        try:
            start_time = datetime.utcnow()
            
            # Get or create conversation
            if not conversation_id:
                conversation_id = self._get_or_create_conversation(user_id)
            
            # Detect intent
            intent = self._detect_intent(message)
            
            # Extract entities
            entities = self._extract_entities(message)
            
            # Generate response based on intent
            response = self._generate_response(
                message=message,
                intent=intent,
                entities=entities,
                user_id=user_id,
                context=context or {}
            )
            
            # Calculate response time
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Save message and response
            self._save_message(
                conversation_id=conversation_id,
                message_type=MessageType.USER.value,
                content=message,
                intent=intent,
                entities=entities,
                response_time_ms=response_time
            )
            
            self._save_message(
                conversation_id=conversation_id,
                message_type=MessageType.ASSISTANT.value,
                content=response.message,
                metadata={
                    "suggestions": response.suggestions,
                    "actions": response.actions,
                    "confidence": response.confidence
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Message processing error: {str(e)}")
            return AssistantResponse(
                message="I apologize, but I encountered an error processing your message. Please try again or contact support if the issue persists.",
                confidence=0.0
            )
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message."""
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent
        
        return "general"
    
    def _extract_entities(self, message: str) -> List[Dict[str, Any]]:
        """Extract entities from message."""
        entities = []
        
        # Simple entity extraction (can be enhanced with NER models)
        words = word_tokenize(message.lower())
        
        # Extract form-related entities
        form_keywords = ['form', 'survey', 'questionnaire', 'question']
        for keyword in form_keywords:
            if keyword in words:
                entities.append({
                    "type": "form_entity",
                    "value": keyword,
                    "confidence": 0.8
                })
        
        # Extract action entities
        action_keywords = ['create', 'build', 'make', 'design', 'analyze', 'view', 'export']
        for keyword in action_keywords:
            if keyword in words:
                entities.append({
                    "type": "action",
                    "value": keyword,
                    "confidence": 0.7
                })
        
        return entities
    
    def _generate_response(
        self,
        message: str,
        intent: str,
        entities: List[Dict[str, Any]],
        user_id: str,
        context: Dict[str, Any]
    ) -> AssistantResponse:
        """Generate intelligent response based on intent and context."""
        
        if intent == "greeting":
            return self._handle_greeting(user_id, context)
        elif intent == "form_creation":
            return self._handle_form_creation(message, entities, context)
        elif intent == "data_collection":
            return self._handle_data_collection(message, entities, context)
        elif intent == "analytics":
            return self._handle_analytics(message, entities, context)
        elif intent == "onboarding":
            return self._handle_onboarding(user_id, context)
        elif intent == "troubleshooting":
            return self._handle_troubleshooting(message, context)
        elif intent == "help":
            return self._handle_help_request(message, context)
        else:
            return self._handle_general_query(message, context)
    
    def _handle_greeting(self, user_id: str, context: Dict[str, Any]) -> AssistantResponse:
        """Handle greeting messages."""
        # Check onboarding status
        with self.SessionLocal() as db:
            progress = db.query(OnboardingProgress).filter(
                OnboardingProgress.user_id == user_id
            ).first()
            
            if not progress or not progress.is_completed:
                return AssistantResponse(
                    message="Hello! Welcome to ODK MCP System. I'm your virtual assistant, here to help you get started. Would you like me to guide you through the onboarding process?",
                    suggestions=[
                        "Start onboarding",
                        "Create my first form",
                        "Show me around",
                        "I need help"
                    ],
                    actions=[
                        {"type": "start_onboarding", "label": "Begin Onboarding"}
                    ],
                    confidence=0.9
                )
            else:
                return AssistantResponse(
                    message="Hello! Great to see you back. How can I help you today?",
                    suggestions=[
                        "Create a new form",
                        "View my data",
                        "Generate a report",
                        "Get help"
                    ],
                    confidence=0.9
                )
    
    def _handle_form_creation(
        self,
        message: str,
        entities: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> AssistantResponse:
        """Handle form creation requests."""
        return AssistantResponse(
            message="I'd be happy to help you create a form! You can use our drag-and-drop form builder to create professional forms quickly. Here's how to get started:",
            suggestions=[
                "Open form builder",
                "Use a template",
                "Import from Excel",
                "See examples"
            ],
            actions=[
                {"type": "navigate", "target": "/forms/new", "label": "Create New Form"},
                {"type": "show_tutorial", "topic": "form_creation", "label": "Watch Tutorial"}
            ],
            context={
                "next_steps": [
                    "Choose form type (survey, registration, assessment)",
                    "Add fields using drag-and-drop",
                    "Configure validation rules",
                    "Preview and test",
                    "Publish form"
                ]
            },
            confidence=0.95
        )
    
    def _handle_data_collection(
        self,
        message: str,
        entities: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> AssistantResponse:
        """Handle data collection queries."""
        return AssistantResponse(
            message="For data collection, you have several options: mobile app, web forms, or QR codes. The mobile app works offline and syncs when connected. Would you like guidance on any specific method?",
            suggestions=[
                "Mobile app setup",
                "Share web form",
                "Generate QR code",
                "Offline collection"
            ],
            actions=[
                {"type": "navigate", "target": "/data-collection", "label": "Data Collection Hub"},
                {"type": "show_tutorial", "topic": "data_collection", "label": "Collection Tutorial"}
            ],
            confidence=0.9
        )
    
    def _handle_analytics(
        self,
        message: str,
        entities: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> AssistantResponse:
        """Handle analytics and reporting queries."""
        return AssistantResponse(
            message="Our analytics dashboard provides powerful insights into your data. You can create visualizations, generate reports, and set up automated analysis. What type of analysis are you looking for?",
            suggestions=[
                "View dashboard",
                "Create visualization",
                "Generate report",
                "Export data"
            ],
            actions=[
                {"type": "navigate", "target": "/analytics", "label": "Open Analytics"},
                {"type": "show_tutorial", "topic": "analytics", "label": "Analytics Guide"}
            ],
            confidence=0.9
        )
    
    def _handle_onboarding(self, user_id: str, context: Dict[str, Any]) -> AssistantResponse:
        """Handle onboarding requests."""
        with self.SessionLocal() as db:
            progress = db.query(OnboardingProgress).filter(
                OnboardingProgress.user_id == user_id
            ).first()
            
            if not progress:
                # Create new onboarding progress
                progress = OnboardingProgress(
                    id=str(uuid.uuid4()),
                    user_id=user_id
                )
                db.add(progress)
                db.commit()
            
            current_step = progress.current_step
            
            return AssistantResponse(
                message=f"Let's continue your onboarding! You're currently on step: {current_step.replace('_', ' ').title()}. I'll guide you through each step to get you up and running quickly.",
                suggestions=[
                    "Continue onboarding",
                    "Skip to specific step",
                    "Watch overview video",
                    "Get help"
                ],
                actions=[
                    {"type": "continue_onboarding", "step": current_step, "label": "Continue"},
                    {"type": "show_onboarding_overview", "label": "Overview"}
                ],
                context={"current_step": current_step, "progress": progress.completion_percentage},
                confidence=0.95
            )
    
    def _handle_troubleshooting(self, message: str, context: Dict[str, Any]) -> AssistantResponse:
        """Handle troubleshooting requests."""
        # Search knowledge base for solutions
        results = self.search_knowledge_base(message, category="troubleshooting", limit=3)
        
        if results:
            solution = results[0]
            return AssistantResponse(
                message=f"I found a solution for your issue: {solution['content'][:200]}... Would you like me to show you the complete solution?",
                suggestions=[
                    "Show full solution",
                    "Try different solution",
                    "Contact support",
                    "Report bug"
                ],
                actions=[
                    {"type": "show_knowledge", "id": solution['id'], "label": "View Solution"},
                    {"type": "contact_support", "label": "Get Help"}
                ],
                confidence=0.8
            )
        else:
            return AssistantResponse(
                message="I understand you're experiencing an issue. Let me help you troubleshoot. Can you provide more details about what's not working?",
                suggestions=[
                    "Form not loading",
                    "Data not syncing",
                    "Export problems",
                    "Login issues"
                ],
                actions=[
                    {"type": "diagnostic_wizard", "label": "Run Diagnostics"},
                    {"type": "contact_support", "label": "Contact Support"}
                ],
                confidence=0.7
            )
    
    def _handle_help_request(self, message: str, context: Dict[str, Any]) -> AssistantResponse:
        """Handle general help requests."""
        # Search knowledge base
        results = self.search_knowledge_base(message, limit=5)
        
        if results:
            return AssistantResponse(
                message="I found some helpful information for you. Here are the most relevant topics:",
                suggestions=[result['title'] for result in results[:4]],
                actions=[
                    {"type": "show_knowledge", "id": result['id'], "label": result['title']}
                    for result in results[:3]
                ],
                context={"search_results": results},
                confidence=0.8
            )
        else:
            return AssistantResponse(
                message="I'm here to help! What would you like assistance with?",
                suggestions=[
                    "Getting started",
                    "Creating forms",
                    "Collecting data",
                    "Viewing analytics"
                ],
                actions=[
                    {"type": "show_help_center", "label": "Help Center"},
                    {"type": "start_tutorial", "label": "Interactive Tutorial"}
                ],
                confidence=0.7
            )
    
    def _handle_general_query(self, message: str, context: Dict[str, Any]) -> AssistantResponse:
        """Handle general queries using knowledge base search."""
        results = self.search_knowledge_base(message, limit=3)
        
        if results and results[0].get('score', 0) > 0.3:
            best_result = results[0]
            return AssistantResponse(
                message=f"Based on your question, I think this might help: {best_result['content'][:200]}...",
                suggestions=[
                    "Show more details",
                    "Search for something else",
                    "Ask a different question",
                    "Get human help"
                ],
                actions=[
                    {"type": "show_knowledge", "id": best_result['id'], "label": "Read More"}
                ],
                confidence=best_result.get('score', 0)
            )
        else:
            return AssistantResponse(
                message="I'm not sure I understand your question completely. Could you rephrase it or be more specific? I'm here to help with forms, data collection, and analytics.",
                suggestions=[
                    "Ask about forms",
                    "Ask about data collection",
                    "Ask about analytics",
                    "Get help"
                ],
                actions=[
                    {"type": "show_help_topics", "label": "Browse Help Topics"}
                ],
                confidence=0.3
            )
    
    def search_knowledge_base(
        self,
        query: str,
        category: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search knowledge base using vector similarity."""
        try:
            if not self.knowledge_vectors or not self.knowledge_data:
                return []
            
            # Vectorize query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.knowledge_vectors).flatten()
            
            # Get top results
            top_indices = similarities.argsort()[-limit:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    result = self.knowledge_data[idx].copy()
                    result['score'] = float(similarities[idx])
                    
                    # Filter by category if specified
                    if not category or result['category'] == category:
                        results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Knowledge base search error: {str(e)}")
            return []
    
    def _get_or_create_conversation(self, user_id: str) -> str:
        """Get existing conversation or create new one."""
        try:
            with self.SessionLocal() as db:
                # Look for active conversation
                conversation = db.query(Conversation).filter(
                    Conversation.user_id == user_id,
                    Conversation.status == ConversationStatus.ACTIVE.value
                ).first()
                
                if not conversation:
                    # Create new conversation
                    conversation = Conversation(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        title="New Conversation"
                    )
                    db.add(conversation)
                    db.commit()
                
                return conversation.id
                
        except Exception as e:
            self.logger.error(f"Conversation creation error: {str(e)}")
            return str(uuid.uuid4())
    
    def _save_message(
        self,
        conversation_id: str,
        message_type: str,
        content: str,
        intent: str = None,
        entities: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None,
        response_time_ms: int = None
    ):
        """Save message to database."""
        try:
            with self.SessionLocal() as db:
                message = Message(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    message_type=message_type,
                    content=content,
                    intent=intent,
                    entities=entities or [],
                    metadata=metadata or {},
                    response_time_ms=response_time_ms
                )
                
                db.add(message)
                
                # Update conversation
                conversation = db.query(Conversation).filter(
                    Conversation.id == conversation_id
                ).first()
                
                if conversation:
                    conversation.total_messages += 1
                    conversation.updated_at = datetime.utcnow()
                
                db.commit()
                
        except Exception as e:
            self.logger.error(f"Message save error: {str(e)}")
    
    def run(self, host='0.0.0.0', port=5007, debug=False):
        """Run the virtual assistant application."""
        self.socketio.run(self.app, host=host, port=port, debug=debug)


# Create global instance
virtual_assistant = VirtualAssistant()

