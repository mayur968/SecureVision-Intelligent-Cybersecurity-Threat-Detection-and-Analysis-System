"""Text preprocessing for email/SMS phishing detection."""

import re
import string
from typing import List


class TextPreprocessor:
    """Preprocess text messages for phishing detection."""
    
    def __init__(self):
        """Initialize text preprocessor."""
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.email_pattern = re.compile(r'\S+@\S+')
        self.phone_pattern = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
        
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Raw text string
            
        Returns:
            Cleaned text string
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace URLs with token
        text = self.url_pattern.sub(' URL ', text)
        
        # Replace emails with token
        text = self.email_pattern.sub(' EMAIL ', text)
        
        # Replace phone numbers with token
        text = self.phone_pattern.sub(' PHONE ', text)
        
        # Replace numbers with token
        text = re.sub(r'\d+', ' NUMBER ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def remove_punctuation(self, text: str) -> str:
        """Remove punctuation from text."""
        translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
        return text.translate(translator)
    
    def preprocess(self, text: str, remove_punct: bool = True) -> str:
        """
        Full preprocessing pipeline.
        
        Args:
            text: Raw text
            remove_punct: Whether to remove punctuation
            
        Returns:
            Preprocessed text
        """
        text = self.clean_text(text)
        
        if remove_punct:
            text = self.remove_punctuation(text)
        
        # Remove extra whitespace again
        text = ' '.join(text.split())
        
        return text
    
    def extract_text_features(self, text: str) -> dict:
        """
        Extract simple text features.
        
        Args:
            text: Text string
            
        Returns:
            Dictionary of text features
        """
        features = {
            'length': len(text),
            'word_count': len(text.split()),
            'has_url': 1 if self.url_pattern.search(text) else 0,
            'has_email': 1 if self.email_pattern.search(text) else 0,
            'has_phone': 1 if self.phone_pattern.search(text) else 0,
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'uppercase_ratio': sum(1 for c in text if c.isupper()) / len(text) if text else 0,
            'digit_ratio': sum(1 for c in text if c.isdigit()) / len(text) if text else 0,
        }
        
        return features
