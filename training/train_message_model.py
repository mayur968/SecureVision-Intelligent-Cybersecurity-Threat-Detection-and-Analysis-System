"""
Train Email/SMS phishing detection model.

This script trains a machine learning model to detect phishing messages
using TF-IDF and text features.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import joblib
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.text_preprocessing import TextPreprocessor
from config import Config


def load_data(data_path):
    """Load message dataset from CSV."""
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} messages")
    print(f"  - Safe messages: {len(df[df['label'] == 0])}")
    print(f"  - Phishing messages: {len(df[df['label'] == 1])}")
    return df


def preprocess_messages(messages, preprocessor):
    """Preprocess all messages."""
    print("\nPreprocessing messages...")
    cleaned = [preprocessor.preprocess(msg) for msg in messages]
    return cleaned


def create_tfidf_features(messages_train, messages_test):
    """Create TF-IDF features."""
    print("\nCreating TF-IDF features...")
    
    # Initialize TF-IDF vectorizer
    vectorizer = TfidfVectorizer(
        max_features=1000,
        min_df=2,
        max_df=0.8,
        ngram_range=(1, 2),  # Use unigrams and bigrams
        strip_accents='unicode',
        stop_words='english'
    )
    
    # Fit and transform training data
    X_train_tfidf = vectorizer.fit_transform(messages_train)
    
    # Transform test data
    X_test_tfidf = vectorizer.transform(messages_test)
    
    print(f"TF-IDF vocabulary size: {len(vectorizer.vocabulary_)}")
    print(f"Training matrix shape: {X_train_tfidf.shape}")
    print(f"Test matrix shape: {X_test_tfidf.shape}")
    
    return X_train_tfidf, X_test_tfidf, vectorizer


def train_and_evaluate_models(X_train, X_test, y_train, y_test):
    """Train and compare multiple models."""
    print("\n" + "="*60)
    print("Training and evaluating models...")
    print("="*60)
    
    models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=20)
    }
    
    best_model = None
    best_score = 0
    best_model_name = None
    
    results = []
    
    for name, model in models.items():
        print(f"\n{name}:")
        print("-" * 40)
        
        # Train
        model.fit(X_train, y_train)
        
        # Predict
        y_pred = model.predict(X_test)
        
        # Evaluate
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        
        print(f"Accuracy:  {accuracy:.4f}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall:    {recall:.4f}")
        print(f"F1-Score:  {f1:.4f}")
        
        results.append({
            'model': name,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1
        })
        
        # Track best model by F1 score
        if f1 > best_score:
            best_score = f1
            best_model = model
            best_model_name = name
    
    print("\n" + "="*60)
    print(f"Best Model: {best_model_name} (F1-Score: {best_score:.4f})")
    print("="*60)
    
    # Detailed classification report for best model
    y_pred_best = best_model.predict(X_test)
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred_best, target_names=['Safe', 'Phishing']))
    
    return best_model, best_model_name, results


def save_models(model, vectorizer, model_path, vectorizer_path):
    """Save trained model and vectorizer to disk."""
    print(f"\nSaving model to {model_path}...")
    joblib.dump(model, model_path)
    
    print(f"Saving vectorizer to {vectorizer_path}...")
    joblib.dump(vectorizer, vectorizer_path)
    
    print("Model and vectorizer saved successfully!")


def main():
    """Main training pipeline."""
    print("\n" + "="*60)
    print("SecureVision - Email/SMS Phishing Detection Model Training")
    print("="*60)
    
    # Ensure models directory exists
    Config.MODELS_DIR.mkdir(exist_ok=True)
    
    # Initialize preprocessor
    preprocessor = TextPreprocessor()
    
    # Load data
    df = load_data(Config.MESSAGE_DATA_PATH)
    
    # Preprocess messages
    messages_cleaned = preprocess_messages(df['message'].values, preprocessor)
    labels = df['label'].values
    
    # Split data
    print("\nSplitting data (80% train, 20% test)...")
    messages_train, messages_test, y_train, y_test = train_test_split(
        messages_cleaned, labels, test_size=0.2, random_state=42, stratify=labels
    )
    print(f"Training set: {len(messages_train)} messages")
    print(f"Test set: {len(messages_test)} messages")
    
    # Create TF-IDF features
    X_train, X_test, vectorizer = create_tfidf_features(messages_train, messages_test)
    
    # Train and evaluate models
    best_model, best_model_name, results = train_and_evaluate_models(
        X_train, X_test, y_train, y_test
    )
    
    # Save the best model and vectorizer
    save_models(best_model, vectorizer, Config.MESSAGE_MODEL_PATH, Config.MESSAGE_VECTORIZER_PATH)
    
    print("\n" + "="*60)
    print("Training completed successfully!")
    print("="*60)
    print(f"\nModel saved to: {Config.MESSAGE_MODEL_PATH}")
    print(f"Vectorizer saved to: {Config.MESSAGE_VECTORIZER_PATH}")
    print(f"Best model: {best_model_name}")
    print("\nNOTE: This is a demo dataset for development/testing.")
    print("For production use, train with a larger, real-world dataset.")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
