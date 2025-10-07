"""
Train a model to improve table/figure detection accuracy
"""
import json
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DetectionTrainer:
    def __init__(self, model_dir="models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        # Initialize model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        self.is_trained = False
        self.feature_names = None
    
    def load_training_data(self, features_file: str):
        """Load training features from file"""
        with open(features_file, 'r') as f:
            self.training_data = json.load(f)
        
        logger.info(f"Loaded {len(self.training_data)} training samples")
        
        # Show data distribution
        labels = [item['label'] for item in self.training_data]
        unique_labels, counts = np.unique(labels, return_counts=True)
        logger.info("Data distribution:")
        for label, count in zip(unique_labels, counts):
            logger.info(f"  {label}: {count}")
    
    def prepare_features(self):
        """Prepare features for training"""
        # Extract features and labels
        X = []
        y = []
        
        for item in self.training_data:
            # Extract all numeric features
            features = []
            for key, value in item.items():
                if key not in ['label', 'pdf_path', 'page_num'] and isinstance(value, (int, float)):
                    features.append(value)
                elif key not in ['label', 'pdf_path', 'page_num'] and isinstance(value, (list, tuple)):
                    # Handle lists/tuples by taking mean or first element
                    if len(value) > 0 and isinstance(value[0], (int, float)):
                        features.append(np.mean(value))
                    else:
                        features.append(0)
            
            X.append(features)
            y.append(item['label'])
        
        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)
        
        # Store feature names for later use
        self.feature_names = [key for key in self.training_data[0].keys() 
                             if key not in ['label', 'pdf_path', 'page_num']]
        
        logger.info(f"Prepared {X.shape[0]} samples with {X.shape[1]} features")
        
        return X, y
    
    def train(self, test_size=0.2):
        """Train the model"""
        X, y = self.prepare_features()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        logger.info(f"Training set: {X_train.shape[0]} samples")
        logger.info(f"Test set: {X_test.shape[0]} samples")
        
        # Train model
        logger.info("Training model...")
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate on test set
        y_pred = self.model.predict(X_test)
        
        logger.info("Test set performance:")
        logger.info(f"Accuracy: {self.model.score(X_test, y_test):.3f}")
        
        # Detailed classification report
        logger.info("\nClassification Report:")
        logger.info(classification_report(y_test, y_pred))
        
        # Confusion matrix
        logger.info("\nConfusion Matrix:")
        logger.info(confusion_matrix(y_test, y_pred))
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5)
        logger.info(f"\nCross-validation scores: {cv_scores}")
        logger.info(f"Mean CV score: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Save model
        model_path = self.model_dir / "detection_classifier.pkl"
        joblib.dump(self.model, model_path)
        logger.info(f"Model saved to {model_path}")
        
        # Save feature names
        feature_names_path = self.model_dir / "feature_names.json"
        with open(feature_names_path, 'w') as f:
            json.dump(self.feature_names, f, indent=2)
        
        return self.model.score(X_test, y_test)
    
    def get_feature_importance(self):
        """Get feature importance from trained model"""
        if not self.is_trained:
            logger.warning("Model not trained yet")
            return None
        
        importance = self.model.feature_importances_
        feature_importance = list(zip(self.feature_names, importance))
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        
        logger.info("Top 10 most important features:")
        for i, (feature, imp) in enumerate(feature_importance[:10]):
            logger.info(f"  {i+1}. {feature}: {imp:.3f}")
        
        return feature_importance

def main():
    """Main training script"""
    trainer = DetectionTrainer()
    
    # Load training data
    features_file = "data/processed/training_features.json"
    if not Path(features_file).exists():
        logger.error(f"Training features file not found: {features_file}")
        logger.error("Run feature extraction first: python utils/feature_extractor.py")
        return
    
    trainer.load_training_data(features_file)
    
    # Train model
    accuracy = trainer.train()
    
    # Show feature importance
    trainer.get_feature_importance()
    
    logger.info(f"Training completed with {accuracy:.3f} accuracy")

if __name__ == "__main__":
    main()
