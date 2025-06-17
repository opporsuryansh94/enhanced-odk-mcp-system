"""
Multilingual support utilities for ODK MCP System.
"""

import os
import json
import re
from typing import Dict, List, Tuple, Union, Optional, Any

from ..config import AI_CONFIG
from ..utils.logging import setup_logger


class MultilingualSupport:
    """
    Multilingual support for text processing.
    
    This class provides methods for language detection, translation,
    and multilingual text processing.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the multilingual support.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["nlp"]["multilingual"]
        self.logger = setup_logger("multilingual")
        self.resources = self._load_resources()
        self.translation_model = None
        self.language_detection_model = None
    
    def detect_language(self, text: str) -> Dict[str, Union[str, float]]:
        """
        Detect the language of a text.
        
        Args:
            text: Text to analyze.
            
        Returns:
            Dictionary with detected language code and confidence.
        """
        if not text:
            return {"language": self.config["default_language"], "confidence": 1.0}
        
        if not self.config["enabled"]:
            return {"language": self.config["default_language"], "confidence": 1.0}
        
        try:
            # Initialize language detection model if not already initialized
            if self.language_detection_model is None:
                self._initialize_language_detection_model()
            
            # Detect language
            if hasattr(self.language_detection_model, "predict_lang"):
                # fasttext model
                predictions = self.language_detection_model.predict_lang(text)
                language = predictions[0].replace("__label__", "")
                confidence = float(predictions[1])
            elif hasattr(self.language_detection_model, "predict"):
                # langid model
                language, confidence = self.language_detection_model.predict(text)
            else:
                # fallback to simple n-gram based detection
                language, confidence = self._detect_language_ngram(text)
            
            return {"language": language, "confidence": confidence}
        except Exception as e:
            self.logger.error(f"Error detecting language: {e}")
            return {"language": self.config["default_language"], "confidence": 0.0}
    
    def translate(self, text: str, target_language: str, source_language: str = None) -> Dict[str, str]:
        """
        Translate text to the target language.
        
        Args:
            text: Text to translate.
            target_language: Target language code.
            source_language: Source language code. If None, it will be detected.
            
        Returns:
            Dictionary with translated text and detected source language.
        """
        if not text:
            return {"translated_text": "", "source_language": source_language or self.config["default_language"]}
        
        if not self.config["enabled"]:
            return {"translated_text": text, "source_language": source_language or self.config["default_language"]}
        
        try:
            # Detect source language if not provided
            if source_language is None:
                detection_result = self.detect_language(text)
                source_language = detection_result["language"]
            
            # If source and target languages are the same, return the original text
            if source_language == target_language:
                return {"translated_text": text, "source_language": source_language}
            
            # Initialize translation model if not already initialized
            if self.translation_model is None:
                self._initialize_translation_model()
            
            # Translate text
            if hasattr(self.translation_model, "translate"):
                # transformers model
                translated_text = self.translation_model.translate(text, source_lang=source_language, target_lang=target_language)
            else:
                # fallback to simple dictionary-based translation
                translated_text = self._translate_simple(text, source_language, target_language)
            
            return {"translated_text": translated_text, "source_language": source_language}
        except Exception as e:
            self.logger.error(f"Error translating text: {e}")
            return {"translated_text": text, "source_language": source_language or self.config["default_language"]}
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Get a list of supported languages.
        
        Returns:
            List of dictionaries with language code and name.
        """
        if not self.config["enabled"]:
            return [{"code": self.config["default_language"], "name": "English"}]
        
        try:
            languages = []
            
            # Get languages from resources
            for code, data in self.resources.get("languages", {}).items():
                languages.append({
                    "code": code,
                    "name": data.get("name", code)
                })
            
            # If no languages found, return default language
            if not languages:
                languages = [{"code": self.config["default_language"], "name": "English"}]
            
            return languages
        except Exception as e:
            self.logger.error(f"Error getting supported languages: {e}")
            return [{"code": self.config["default_language"], "name": "English"}]
    
    def get_stopwords(self, language: str) -> List[str]:
        """
        Get stopwords for a specific language.
        
        Args:
            language: Language code.
            
        Returns:
            List of stopwords.
        """
        if not self.config["enabled"]:
            return []
        
        try:
            # Get stopwords from resources
            stopwords = self.resources.get("stopwords", {}).get(language, [])
            
            return stopwords
        except Exception as e:
            self.logger.error(f"Error getting stopwords: {e}")
            return []
    
    def _initialize_language_detection_model(self) -> None:
        """
        Initialize the language detection model.
        """
        try:
            # Try to load fasttext
            try:
                import fasttext
                self.language_detection_model = fasttext.load_model("lid.176.bin")
                self.logger.info("Loaded fasttext language detection model")
                return
            except Exception:
                pass
            
            # Try to load langid
            try:
                import langid
                self.language_detection_model = langid
                self.logger.info("Loaded langid language detection model")
                return
            except Exception:
                pass
            
            # Fallback to simple n-gram based detection
            self.logger.info("Using simple n-gram based language detection")
        except Exception as e:
            self.logger.error(f"Error initializing language detection model: {e}")
    
    def _initialize_translation_model(self) -> None:
        """
        Initialize the translation model.
        """
        try:
            # Try to load transformers
            try:
                from transformers import MarianMTModel, MarianTokenizer
                
                # Create a simple wrapper class
                class TranslationModel:
                    def __init__(self):
                        self.models = {}
                        self.tokenizers = {}
                    
                    def translate(self, text, source_lang, target_lang):
                        model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"
                        
                        # Load model and tokenizer if not already loaded
                        if model_name not in self.models:
                            try:
                                self.tokenizers[model_name] = MarianTokenizer.from_pretrained(model_name)
                                self.models[model_name] = MarianMTModel.from_pretrained(model_name)
                            except Exception:
                                return text
                        
                        # Translate text
                        tokenizer = self.tokenizers[model_name]
                        model = self.models[model_name]
                        
                        inputs = tokenizer(text, return_tensors="pt", padding=True)
                        outputs = model.generate(**inputs)
                        translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
                        
                        return translated_text
                
                self.translation_model = TranslationModel()
                self.logger.info("Loaded transformers translation model")
                return
            except Exception:
                pass
            
            # Fallback to simple dictionary-based translation
            self.logger.info("Using simple dictionary-based translation")
        except Exception as e:
            self.logger.error(f"Error initializing translation model: {e}")
    
    def _detect_language_ngram(self, text: str) -> Tuple[str, float]:
        """
        Detect language using n-gram frequency profiles.
        
        Args:
            text: Text to analyze.
            
        Returns:
            Tuple of (language_code, confidence).
        """
        # Simple n-gram based language detection
        # This is a fallback method when no language detection library is available
        
        # Get language profiles
        profiles = self.resources.get("language_profiles", {})
        
        if not profiles:
            return self.config["default_language"], 0.0
        
        # Generate n-grams from text
        text = text.lower()
        ngrams = []
        
        # Generate character trigrams
        for i in range(len(text) - 2):
            ngrams.append(text[i:i+3])
        
        # Count n-gram frequencies
        ngram_counts = {}
        for ngram in ngrams:
            ngram_counts[ngram] = ngram_counts.get(ngram, 0) + 1
        
        # Calculate similarity with each language profile
        similarities = {}
        
        for language, profile in profiles.items():
            similarity = 0
            
            for ngram, count in ngram_counts.items():
                if ngram in profile:
                    similarity += count * profile[ngram]
            
            similarities[language] = similarity
        
        # Find language with highest similarity
        if not similarities:
            return self.config["default_language"], 0.0
        
        best_language = max(similarities, key=similarities.get)
        
        # Calculate confidence
        total_similarity = sum(similarities.values())
        confidence = similarities[best_language] / total_similarity if total_similarity > 0 else 0.0
        
        return best_language, confidence
    
    def _translate_simple(self, text: str, source_language: str, target_language: str) -> str:
        """
        Translate text using a simple dictionary-based approach.
        
        Args:
            text: Text to translate.
            source_language: Source language code.
            target_language: Target language code.
            
        Returns:
            Translated text.
        """
        # Simple dictionary-based translation
        # This is a fallback method when no translation library is available
        
        # Get translation dictionary
        translation_dict = self.resources.get("translations", {}).get(f"{source_language}-{target_language}", {})
        
        if not translation_dict:
            return text
        
        # Tokenize text
        tokens = re.findall(r'\b\w+\b|\W+', text)
        
        # Translate tokens
        translated_tokens = []
        
        for token in tokens:
            if token.lower() in translation_dict:
                # Preserve case
                if token.isupper():
                    translated_tokens.append(translation_dict[token.lower()].upper())
                elif token[0].isupper():
                    translated = translation_dict[token.lower()]
                    translated_tokens.append(translated[0].upper() + translated[1:])
                else:
                    translated_tokens.append(translation_dict[token.lower()])
            else:
                translated_tokens.append(token)
        
        # Combine tokens
        translated_text = ''.join(translated_tokens)
        
        return translated_text
    
    def _load_resources(self) -> Dict:
        """
        Load language resources from file.
        
        Returns:
            Dictionary with language resources.
        """
        resources_path = self.config["resources_path"]
        
        # Default resources
        default_resources = {
            "languages": {
                "en": {"name": "English"},
                "es": {"name": "Spanish"},
                "fr": {"name": "French"},
                "de": {"name": "German"}
            },
            "stopwords": {
                "en": [
                    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
                    "which", "this", "that", "these", "those", "then", "just", "so", "than",
                    "such", "when", "while", "to", "in", "on", "at", "by", "for", "with"
                ]
            },
            "language_profiles": {},
            "translations": {}
        }
        
        try:
            if os.path.exists(resources_path):
                with open(resources_path, 'r', encoding='utf-8') as f:
                    resources = json.load(f)
                return resources
        except Exception as e:
            self.logger.error(f"Error loading language resources: {e}")
        
        return default_resources

