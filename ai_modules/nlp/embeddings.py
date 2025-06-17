"""
Text embedding utilities for ODK MCP System.
"""

import os
import pickle
from typing import Dict, List, Tuple, Union, Optional, Any

from ..config import AI_CONFIG
from ..utils.logging import setup_logger


class TextEmbedder:
    """
    Text embedder for generating embeddings from text.
    
    This class provides methods to generate embeddings from text using
    various embedding models.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the text embedder.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["nlp"]["embeddings"]
        self.logger = setup_logger("text_embedder")
        self.model = None
        self.cache = {}
        
        # Load cache if enabled
        if self.config["use_cache"]:
            self._load_cache()
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for a text.
        
        Args:
            text: Text to embed.
            
        Returns:
            Embedding vector.
        """
        # Check cache
        if self.config["use_cache"] and text in self.cache:
            return self.cache[text]
        
        try:
            # Initialize model if not already initialized
            if self.model is None:
                self._initialize_model()
            
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Cache embedding
            if self.config["use_cache"]:
                self.cache[text] = embedding
                self._save_cache_if_needed()
            
            return embedding
        except Exception as e:
            self.logger.error(f"Error embedding text: {e}")
            # Return zero vector as fallback
            return [0.0] * self.config["embedding_dim"]
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed.
            
        Returns:
            List of embedding vectors.
        """
        # Check which texts are not in cache
        if self.config["use_cache"]:
            texts_to_embed = [text for text in texts if text not in self.cache]
        else:
            texts_to_embed = texts
        
        try:
            # Initialize model if not already initialized
            if self.model is None and texts_to_embed:
                self._initialize_model()
            
            # Generate embeddings for texts not in cache
            if texts_to_embed:
                new_embeddings = self._generate_embeddings(texts_to_embed)
                
                # Cache embeddings
                if self.config["use_cache"]:
                    for text, embedding in zip(texts_to_embed, new_embeddings):
                        self.cache[text] = embedding
                    self._save_cache_if_needed()
            
            # Get embeddings from cache or new embeddings
            embeddings = []
            for text in texts:
                if self.config["use_cache"] and text in self.cache:
                    embeddings.append(self.cache[text])
                else:
                    # This should not happen, but just in case
                    idx = texts_to_embed.index(text)
                    embeddings.append(new_embeddings[idx])
            
            return embeddings
        except Exception as e:
            self.logger.error(f"Error embedding texts: {e}")
            # Return zero vectors as fallback
            return [[0.0] * self.config["embedding_dim"] for _ in texts]
    
    def _initialize_model(self) -> None:
        """
        Initialize the embedding model.
        """
        model_type = self.config["model_type"]
        model_name = self.config["model_name"]
        
        try:
            if model_type == "sentence_transformers":
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name)
            elif model_type == "transformers":
                from transformers import AutoModel, AutoTokenizer
                self.model = {
                    "model": AutoModel.from_pretrained(model_name),
                    "tokenizer": AutoTokenizer.from_pretrained(model_name)
                }
            elif model_type == "spacy":
                import spacy
                self.model = spacy.load(model_name)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
        except Exception as e:
            self.logger.error(f"Error initializing model: {e}")
            raise
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a text using the initialized model.
        
        Args:
            text: Text to embed.
            
        Returns:
            Embedding vector.
        """
        model_type = self.config["model_type"]
        
        if model_type == "sentence_transformers":
            embedding = self.model.encode(text)
            return embedding.tolist()
        elif model_type == "transformers":
            import torch
            
            # Tokenize text
            inputs = self.model["tokenizer"](text, return_tensors="pt", padding=True, truncation=True)
            
            # Generate embedding
            with torch.no_grad():
                outputs = self.model["model"](**inputs)
            
            # Use [CLS] token embedding as sentence embedding
            embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()
            return embedding.tolist()
        elif model_type == "spacy":
            doc = self.model(text)
            embedding = doc.vector
            return embedding.tolist()
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using the initialized model.
        
        Args:
            texts: List of texts to embed.
            
        Returns:
            List of embedding vectors.
        """
        model_type = self.config["model_type"]
        
        if model_type == "sentence_transformers":
            embeddings = self.model.encode(texts)
            return embeddings.tolist()
        elif model_type == "transformers":
            import torch
            
            embeddings = []
            for text in texts:
                # Tokenize text
                inputs = self.model["tokenizer"](text, return_tensors="pt", padding=True, truncation=True)
                
                # Generate embedding
                with torch.no_grad():
                    outputs = self.model["model"](**inputs)
                
                # Use [CLS] token embedding as sentence embedding
                embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()
                embeddings.append(embedding.tolist())
            
            return embeddings
        elif model_type == "spacy":
            embeddings = []
            for text in texts:
                doc = self.model(text)
                embedding = doc.vector
                embeddings.append(embedding.tolist())
            
            return embeddings
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def _load_cache(self) -> None:
        """
        Load the embedding cache from disk.
        """
        cache_path = self.config["cache_path"]
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    self.cache = pickle.load(f)
                self.logger.info(f"Loaded {len(self.cache)} embeddings from cache")
            except Exception as e:
                self.logger.error(f"Error loading embedding cache: {e}")
                self.cache = {}
    
    def _save_cache_if_needed(self) -> None:
        """
        Save the embedding cache to disk if the cache size exceeds the threshold.
        """
        if len(self.cache) % self.config["cache_save_threshold"] == 0:
            self._save_cache()
    
    def _save_cache(self) -> None:
        """
        Save the embedding cache to disk.
        """
        cache_path = self.config["cache_path"]
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(self.cache, f)
            self.logger.info(f"Saved {len(self.cache)} embeddings to cache")
        except Exception as e:
            self.logger.error(f"Error saving embedding cache: {e}")

