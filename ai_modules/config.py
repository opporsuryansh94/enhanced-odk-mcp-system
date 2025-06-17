"""
Enhanced global configuration for AI modules in ODK MCP System.
Includes support for external AI APIs, advanced analytics, and subscription-aware features.
"""

import os
import json
from typing import Dict, Any

# Enhanced configuration with new AI capabilities
AI_CONFIG = {
    # General settings
    "enabled": True,
    "debug_mode": False,
    "subscription_aware": True,  # New: Enable subscription-based feature limits
    
    # Logging settings
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "file_logging_enabled": True,
        "log_dir": "logs",
        "ai_event_logging_enabled": True,
        "ai_event_file_logging_enabled": True
    },
    
    # Validation settings
    "validation": {
        "strict_mode": False,
        "sanitize_inputs": True
    },
    
    # External AI API settings
    "external_apis": {
        "openai": {
            "enabled": False,
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "model": "gpt-3.5-turbo",
            "max_tokens": 1000,
            "temperature": 0.7,
            "timeout": 30
        },
        "claude": {
            "enabled": False,
            "api_key": os.environ.get("CLAUDE_API_KEY"),
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "timeout": 30
        },
        "huggingface": {
            "enabled": True,
            "api_key": os.environ.get("HUGGINGFACE_API_KEY"),
            "inference_endpoint": "https://api-inference.huggingface.co/models/",
            "timeout": 30
        }
    },
    
    # NLP settings
    "nlp": {
        # Text embedding settings
        "embeddings": {
            "model_type": "sentence_transformers",
            "model_name": "all-MiniLM-L6-v2",
            "embedding_dim": 384,
            "use_cache": True,
            "cache_path": "data/embeddings_cache.pkl",
            "cache_save_threshold": 100
        },
        
        # Text analysis settings
        "text_analysis": {
            "max_keywords": 10,
            "min_keyword_length": 3,
            "stopwords_path": "data/stopwords.json",
            "sentiment_analysis": True,
            "language_detection": True
        },
        
        # Multilingual settings
        "multilingual": {
            "enabled": True,
            "default_language": "en",
            "supported_languages": ["en", "es", "fr", "hi", "sw", "ar"],
            "resources_path": "data/language_resources.json",
            "auto_translate": True
        }
    },
    
    # Enhanced anomaly detection settings
    "anomaly_detection": {
        "enabled": True,
        "methods": ["isolation_forest", "local_outlier_factor", "one_class_svm", "statistical", "deep_learning"],
        "default_method": "isolation_forest",
        "threshold": 0.95,
        "min_samples": 20,
        "model_path": "data/anomaly_detection_models.pkl",
        "real_time_detection": True,
        "batch_processing": True,
        "alert_threshold": 0.9,
        "subscription_limits": {
            "starter": {"max_detections_per_month": 1000},
            "pro": {"max_detections_per_month": 10000},
            "enterprise": {"max_detections_per_month": -1}  # Unlimited
        }
    },
    
    # Enhanced data insights settings
    "data_insights": {
        "enabled": True,
        "max_insights": 10,
        "min_correlation": 0.5,
        "max_categorical_values": 20,
        "time_series_analysis": True,
        "predictive_analytics": True,
        "trend_analysis": True,
        "pattern_recognition": True,
        "auto_insights": True,
        "insight_types": [
            "correlation",
            "trend",
            "outlier",
            "pattern",
            "prediction",
            "summary",
            "recommendation"
        ],
        "subscription_limits": {
            "starter": {"max_insights_per_month": 100},
            "pro": {"max_insights_per_month": 1000},
            "enterprise": {"max_insights_per_month": -1}  # Unlimited
        }
    },
    
    # Enhanced form recommendations settings
    "form_recommendations": {
        "enabled": True,
        "use_persistent_storage": True,
        "embeddings_path": "data/form_embeddings.pkl",
        "min_similarity": 0.7,
        "max_recommendations": 5,
        "ai_powered_suggestions": True,
        "smart_skip_logic": True,
        "field_type_suggestions": True,
        "validation_suggestions": True,
        "subscription_limits": {
            "starter": {"max_recommendations_per_month": 50},
            "pro": {"max_recommendations_per_month": 500},
            "enterprise": {"max_recommendations_per_month": -1}  # Unlimited
        }
    },
    
    # Enhanced RAG settings
    "rag": {
        "enabled": True,
        "knowledge_base_path": "data/knowledge_base",
        "index_path": "data/knowledge_base_index",
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "max_results": 5,
        "vector_store": "faiss",  # Options: faiss, chroma, pinecone
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "reranking_enabled": True,
        "context_window": 4000,
        "subscription_limits": {
            "starter": {"max_queries_per_month": 100},
            "pro": {"max_queries_per_month": 1000},
            "enterprise": {"max_queries_per_month": -1}  # Unlimited
        }
    },
    
    # New: Smart form builder AI settings
    "smart_form_builder": {
        "enabled": True,
        "csv_analysis": True,
        "field_type_detection": True,
        "validation_suggestions": True,
        "skip_logic_generation": True,
        "form_optimization": True,
        "template_matching": True,
        "subscription_limits": {
            "starter": {"max_ai_suggestions_per_month": 50},
            "pro": {"max_ai_suggestions_per_month": 500},
            "enterprise": {"max_ai_suggestions_per_month": -1}  # Unlimited
        }
    },
    
    # New: Virtual assistant settings
    "virtual_assistant": {
        "enabled": True,
        "chatbot_model": "local",  # Options: local, openai, claude
        "knowledge_base_integration": True,
        "context_aware": True,
        "multilingual_support": True,
        "response_caching": True,
        "learning_enabled": True,
        "subscription_limits": {
            "starter": {"max_queries_per_month": 100},
            "pro": {"max_queries_per_month": 1000},
            "enterprise": {"max_queries_per_month": -1}  # Unlimited
        }
    },
    
    # New: Advanced analytics settings
    "advanced_analytics": {
        "enabled": True,
        "statistical_tests": True,
        "machine_learning": True,
        "deep_learning": False,  # Disabled by default due to resource requirements
        "time_series_forecasting": True,
        "clustering": True,
        "classification": True,
        "regression": True,
        "feature_engineering": True,
        "auto_ml": False,  # Disabled by default
        "subscription_limits": {
            "starter": {"max_analyses_per_month": 50},
            "pro": {"max_analyses_per_month": 500},
            "enterprise": {"max_analyses_per_month": -1}  # Unlimited
        }
    },
    
    # New: Performance and resource settings
    "performance": {
        "max_concurrent_tasks": 5,
        "task_timeout": 300,  # 5 minutes
        "memory_limit_mb": 1024,  # 1GB
        "cpu_limit_percent": 80,
        "cache_size_mb": 256,
        "batch_size": 100,
        "parallel_processing": True
    },
    
    # New: Security settings for AI modules
    "security": {
        "input_sanitization": True,
        "output_filtering": True,
        "rate_limiting": True,
        "audit_logging": True,
        "data_encryption": True,
        "secure_model_storage": True,
        "api_key_rotation": True
    }
}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from a file.
    
    Args:
        config_path: Path to configuration file. If None, uses the default configuration.
        
    Returns:
        Configuration dictionary.
    """
    global AI_CONFIG
    
    # Use default configuration if no path provided
    if not config_path:
        return AI_CONFIG
    
    # Load configuration from file
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Merge with default configuration
            AI_CONFIG = _merge_configs(AI_CONFIG, config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
    
    return AI_CONFIG


def save_config(config: Dict[str, Any], config_path: str) -> bool:
    """
    Save configuration to a file.
    
    Args:
        config: Configuration dictionary.
        config_path: Path to save configuration file.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Save configuration to file
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False


def get_subscription_limits(feature: str, plan: str) -> Dict[str, Any]:
    """
    Get subscription limits for a specific feature and plan.
    
    Args:
        feature: Feature name (e.g., 'anomaly_detection', 'data_insights')
        plan: Subscription plan (e.g., 'starter', 'pro', 'enterprise')
        
    Returns:
        Dictionary with subscription limits for the feature.
    """
    if feature in AI_CONFIG and "subscription_limits" in AI_CONFIG[feature]:
        return AI_CONFIG[feature]["subscription_limits"].get(plan, {})
    return {}


def check_subscription_limit(feature: str, plan: str, usage_key: str, current_usage: int) -> bool:
    """
    Check if current usage is within subscription limits.
    
    Args:
        feature: Feature name
        plan: Subscription plan
        usage_key: Usage key (e.g., 'max_detections_per_month')
        current_usage: Current usage count
        
    Returns:
        True if within limits, False otherwise.
    """
    limits = get_subscription_limits(feature, plan)
    if usage_key in limits:
        limit = limits[usage_key]
        if limit == -1:  # Unlimited
            return True
        return current_usage < limit
    return True  # No limit defined, allow usage


def _merge_configs(default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge user configuration with default configuration.
    
    Args:
        default_config: Default configuration dictionary.
        user_config: User configuration dictionary.
        
    Returns:
        Merged configuration dictionary.
    """
    merged_config = default_config.copy()
    
    for key, value in user_config.items():
        if key in merged_config and isinstance(merged_config[key], dict) and isinstance(value, dict):
            merged_config[key] = _merge_configs(merged_config[key], value)
        else:
            merged_config[key] = value
    
    return merged_config


# Initialize configuration
config_path = os.environ.get("ODK_MCP_AI_CONFIG_PATH")
if config_path:
    load_config(config_path)

