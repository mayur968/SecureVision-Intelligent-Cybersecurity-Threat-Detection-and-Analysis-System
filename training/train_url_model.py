"""
Train URL phishing detection model.

This script trains a machine learning model to detect phishing URLs
using extracted features.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import joblib
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.url_features import URLFeatureExtractor
from config import Config


def load_data(data_path):
    """Load URL dataset from CSV."""
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} URLs")
    print(f"  - Safe URLs: {len(df[df['label'] == 0])}")
    print(f"  - Phishing URLs: {len(df[df['label'] == 1])}")
    return df


def extract_features_from_dataset(df, feature_extractor):
    """Extract features from all URLs in dataset."""
    print("\nExtracting features from URLs...")
    
    features_list = []
    valid_indices = []
    
    for idx, row in df.iterrows():
        try:
            url = row['url']
            features = feature_extractor.extract_features(url)
            features_list.append(list(features.values()))
            valid_indices.append(idx)
        except Exception as e:
            print(f"Error processing URL {idx}: {e}")
    
    # Create feature matrix
    X = np.array(features_list)
    y = df.loc[valid_indices, 'label'].values
    
    print(f"Extracted {X.shape[1]} features from {X.shape[0]} URLs")
    
    return X, y


def train_and_evaluate_models(X_train, X_test, y_train, y_test):
    """Train and compare multiple models."""
    print("\n" + "="*60)
    print("Training and evaluating models...")
    print("="*60)
    
    models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42)
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


def save_model(model, model_path):
    """Save trained model to disk."""
    print(f"\nSaving model to {model_path}...")
    joblib.dump(model, model_path)
    print("Model saved successfully!")


def main():
    """Main training pipeline."""
    print("\n" + "="*60)
    print("SecureVision - URL Phishing Detection Model Training")
    print("="*60)
    
    # Ensure models directory exists
    Config.MODELS_DIR.mkdir(exist_ok=True)
    
    # Initialize feature extractor (skip WHOIS during training to avoid timeouts)
    feature_extractor = URLFeatureExtractor(skip_whois=True)
    
    # Load data
    df = load_data(Config.URL_DATA_PATH)
    
    # Extract features
    X, y = extract_features_from_dataset(df, feature_extractor)
    
    # Split data
    print("\nSplitting data (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    
    # Train and evaluate models
    best_model, best_model_name, results = train_and_evaluate_models(
        X_train, X_test, y_train, y_test
    )
    
    # Save the best model
    save_model(best_model, Config.URL_MODEL_PATH)
    
    # Save feature names for reference
    feature_names_path = Config.MODELS_DIR / 'url_feature_names.txt'
    with open(feature_names_path, 'w') as f:
        for name in feature_extractor.get_feature_names():
            f.write(f"{name}\n")
    print(f"Feature names saved to {feature_names_path}")
    
    print("\n" + "="*60)
    print("Training completed successfully!")
    print("="*60)
    print(f"\nModel saved to: {Config.URL_MODEL_PATH}")
    print(f"Best model: {best_model_name}")
    print("\nNOTE: This is a demo dataset for development/testing.")
    print("For production use, train with a larger, real-world dataset.")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
