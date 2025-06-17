"""
Text analysis utilities for ODK MCP System.
"""

import os
import json
import re
from typing import Dict, List, Tuple, Union, Optional, Any
from collections import Counter

from ..config import AI_CONFIG
from ..utils.logging import setup_logger


class TextAnalyzer:
    """
    Text analyzer for analyzing text content.
    
    This class provides methods to analyze text content, extract keywords,
    and perform other text analysis tasks.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the text analyzer.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["nlp"]["text_analysis"]
        self.logger = setup_logger("text_analyzer")
        self.stopwords = self._load_stopwords()
    
    def extract_keywords(self, text: str, max_keywords: int = None) -> List[str]:
        """
        Extract keywords from text.
        
        Args:
            text: Text to analyze.
            max_keywords: Maximum number of keywords to extract.
            
        Returns:
            List of keywords.
        """
        if not text:
            return []
        
        try:
            # Set default max_keywords
            if max_keywords is None:
                max_keywords = self.config["max_keywords"]
            
            # Tokenize text
            tokens = self._tokenize(text)
            
            # Remove stopwords and short words
            tokens = [token for token in tokens if token not in self.stopwords and len(token) >= self.config["min_keyword_length"]]
            
            # Count token frequencies
            token_counts = Counter(tokens)
            
            # Get top keywords
            keywords = [token for token, _ in token_counts.most_common(max_keywords)]
            
            return keywords
        except Exception as e:
            self.logger.error(f"Error extracting keywords: {e}")
            return []
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze.
            
        Returns:
            Dictionary with sentiment scores.
        """
        if not text:
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
        
        try:
            # Simple rule-based sentiment analysis
            # In a production system, this would use a more sophisticated approach
            positive_words = [
                "good", "great", "excellent", "amazing", "wonderful", "fantastic",
                "happy", "pleased", "satisfied", "positive", "awesome", "love",
                "like", "enjoy", "beneficial", "helpful", "useful", "effective"
            ]
            
            negative_words = [
                "bad", "terrible", "awful", "horrible", "poor", "negative",
                "unhappy", "disappointed", "dissatisfied", "hate", "dislike",
                "useless", "ineffective", "problem", "issue", "error", "bug"
            ]
            
            # Tokenize text
            tokens = self._tokenize(text.lower())
            
            # Count positive and negative words
            positive_count = sum(1 for token in tokens if token in positive_words)
            negative_count = sum(1 for token in tokens if token in negative_words)
            total_count = len(tokens)
            
            # Calculate sentiment scores
            if total_count > 0:
                positive_score = positive_count / total_count
                negative_score = negative_count / total_count
                neutral_score = 1.0 - positive_score - negative_score
            else:
                positive_score = 0.0
                negative_score = 0.0
                neutral_score = 1.0
            
            return {
                "positive": positive_score,
                "negative": negative_score,
                "neutral": neutral_score
            }
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text.
        
        Args:
            text: Text to analyze.
            
        Returns:
            Dictionary with entity types and values.
        """
        if not text:
            return {}
        
        try:
            # Simple rule-based entity extraction
            # In a production system, this would use a more sophisticated approach
            
            # Extract dates
            date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
            dates = re.findall(date_pattern, text)
            
            # Extract emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            
            # Extract URLs
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, text)
            
            # Extract phone numbers
            phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
            phones = re.findall(phone_pattern, text)
            
            return {
                "date": dates,
                "email": emails,
                "url": urls,
                "phone": phones
            }
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return {}
    
    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """
        Generate a summary of text.
        
        Args:
            text: Text to summarize.
            max_sentences: Maximum number of sentences in the summary.
            
        Returns:
            Summary text.
        """
        if not text:
            return ""
        
        try:
            # Split text into sentences
            sentences = self._split_sentences(text)
            
            if not sentences:
                return ""
            
            # If text is already short, return it as is
            if len(sentences) <= max_sentences:
                return text
            
            # Calculate sentence scores based on keyword frequency
            keywords = self.extract_keywords(text, max_keywords=20)
            sentence_scores = []
            
            for sentence in sentences:
                # Count keywords in sentence
                score = sum(1 for keyword in keywords if keyword.lower() in sentence.lower())
                sentence_scores.append((sentence, score))
            
            # Sort sentences by score
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Get top sentences
            top_sentences = [sentence for sentence, _ in sentence_scores[:max_sentences]]
            
            # Sort sentences by their original order
            top_sentences.sort(key=lambda s: sentences.index(s))
            
            # Combine sentences
            summary = " ".join(top_sentences)
            
            return summary
        except Exception as e:
            self.logger.error(f"Error summarizing text: {e}")
            return text[:200] + "..." if len(text) > 200 else text
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Args:
            text: Text to tokenize.
            
        Returns:
            List of tokens.
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        return tokens
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split.
            
        Returns:
            List of sentences.
        """
        # Split on sentence-ending punctuation followed by space or end of string
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        
        # Remove empty sentences
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
        
        return sentences
    
    def _load_stopwords(self) -> List[str]:
        """
        Load stopwords from file.
        
        Returns:
            List of stopwords.
        """
        stopwords_path = self.config["stopwords_path"]
        
        # Default stopwords
        default_stopwords = [
            "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
            "which", "this", "that", "these", "those", "then", "just", "so", "than",
            "such", "when", "while", "to", "in", "on", "at", "by", "for", "with",
            "about", "against", "between", "into", "through", "during", "before",
            "after", "above", "below", "from", "up", "down", "of", "off", "over",
            "under", "again", "further", "then", "once", "here", "there", "all",
            "any", "both", "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
            "can", "will", "just", "should", "now"
        ]
        
        try:
            if os.path.exists(stopwords_path):
                with open(stopwords_path, 'r', encoding='utf-8') as f:
                    stopwords = json.load(f)
                return stopwords
        except Exception as e:
            self.logger.error(f"Error loading stopwords: {e}")
        
        return default_stopwords

