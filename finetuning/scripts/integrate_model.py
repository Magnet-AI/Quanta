"""
Integrate the trained model into the existing PDF extraction system
"""
import sys
import os
from pathlib import Path

# Add the main project to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import joblib
import json
import numpy as np
from src.runner import process_pdf
from src.figures import Figure
from src.tables import Table
import logging

logger = logging.getLogger(__name__)

class EnhancedDetector:
    def __init__(self, model_path="finetuning/models/detection_classifier.pkl"):
        self.model_path = Path(model_path)
        self.model = None
        self.feature_names = None
        self.is_loaded = False
        
        self._load_model()
    
    def _load_model(self):
        """Load the trained model"""
        try:
            if self.model_path.exists():
                self.model = joblib.load(self.model_path)
                
                # Load feature names
                feature_names_path = self.model_path.parent / "feature_names.json"
                if feature_names_path.exists():
                    with open(feature_names_path, 'r') as f:
                        self.feature_names = json.load(f)
                
                self.is_loaded = True
                logger.info("Trained model loaded successfully")
            else:
                logger.warning(f"Model file not found: {self.model_path}")
                logger.warning("Using original detection system")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.warning("Using original detection system")
    
    def extract_features_for_detection(self, detection, page_data):
        """Extract features for a detection (figure or table)"""
        from finetuning.utils.feature_extractor import FeatureExtractor
        
        extractor = FeatureExtractor()
        
        # Convert detection to annotation format
        annotation = {
            'bbox_px': detection.bbox_px,
            'page_num': page_data.get('page_num', 0),
            'pdf_path': page_data.get('pdf_path', ''),
            'page_width': page_data['page_size']['px'][0],
            'page_height': page_data['page_size']['px'][1],
        }
        
        # Extract features
        basic_features = extractor.extract_features_from_annotation(annotation)
        visual_features = extractor.extract_visual_features(annotation, annotation['pdf_path'])
        text_features = extractor.extract_text_features(annotation, annotation['pdf_path'])
        
        # Combine features
        all_features = {**basic_features, **visual_features, **text_features}
        
        return all_features
    
    def predict_detection_type(self, detection, page_data):
        """Predict the type of a detection using the trained model"""
        if not self.is_loaded:
            # Fallback to original detection
            if isinstance(detection, Figure):
                return 'figure', 0.5
            elif isinstance(detection, Table):
                return 'table', 0.5
            else:
                return 'unknown', 0.0
        
        try:
            # Extract features
            features = self.extract_features_for_detection(detection, page_data)
            
            # Prepare feature vector in the same order as training
            feature_vector = []
            for feature_name in self.feature_names:
                value = features.get(feature_name, 0)
                if isinstance(value, (list, tuple)):
                    value = np.mean(value) if len(value) > 0 else 0
                feature_vector.append(value)
            
            # Make prediction
            prediction = self.model.predict([feature_vector])[0]
            confidence = max(self.model.predict_proba([feature_vector])[0])
            
            return prediction, confidence
            
        except Exception as e:
            logger.warning(f"Error in prediction: {e}")
            # Fallback to original detection
            if isinstance(detection, Figure):
                return 'figure', 0.5
            elif isinstance(detection, Table):
                return 'table', 0.5
            else:
                return 'unknown', 0.0
    
    def enhance_detections(self, page_data):
        """Enhance detections using the trained model"""
        enhanced_figures = []
        enhanced_tables = []
        
        # Process figures
        for figure in page_data.get('figures', []):
            prediction, confidence = self.predict_detection_type(figure, page_data)
            
            if prediction == 'figure' and confidence > 0.6:
                enhanced_figures.append(figure)
            elif prediction == 'table' and confidence > 0.6:
                # Convert figure to table
                table = self._convert_figure_to_table(figure)
                enhanced_tables.append(table)
            else:
                # Low confidence - keep original classification
                enhanced_figures.append(figure)
        
        # Process tables
        for table in page_data.get('tables', []):
            prediction, confidence = self.predict_detection_type(table, page_data)
            
            if prediction == 'table' and confidence > 0.6:
                enhanced_tables.append(table)
            elif prediction == 'figure' and confidence > 0.6:
                # Convert table to figure
                figure = self._convert_table_to_figure(table)
                enhanced_figures.append(figure)
            else:
                # Low confidence - keep original classification
                enhanced_tables.append(table)
        
        # Update page data
        page_data['figures'] = enhanced_figures
        page_data['tables'] = enhanced_tables
        
        return page_data
    
    def _convert_figure_to_table(self, figure):
        """Convert a Figure object to a Table object"""
        return Table(
            bbox_px=figure.bbox_px,
            cells=[],  # Empty cells for now
            detection_method='enhanced_from_figure'
        )
    
    def _convert_table_to_figure(self, table):
        """Convert a Table object to a Figure object"""
        return Figure(
            bbox_px=table.bbox_px,
            source='enhanced_from_table'
        )

def enhance_pdf_processing(pdf_path, output_dir):
    """Enhanced PDF processing with ML model"""
    detector = EnhancedDetector()
    
    # Process PDF with original system
    result = process_pdf(pdf_path, output_dir)
    
    # Enhance each page
    enhanced_pages = []
    for page_data in result['pages']:
        enhanced_page = detector.enhance_detections(page_data)
        enhanced_pages.append(enhanced_page)
    
    # Update result
    result['pages'] = enhanced_pages
    
    # Recalculate totals
    total_figures = sum(len(p.get('figures', [])) for p in enhanced_pages)
    total_tables = sum(len(p.get('tables', [])) for p in enhanced_pages)
    
    result['enhanced_totals'] = {
        'figures': total_figures,
        'tables': total_tables
    }
    
    return result

def main():
    """Test the enhanced detection"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test enhanced PDF processing")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--output", default="enhanced_output", help="Output directory")
    
    args = parser.parse_args()
    
    # Process PDF with enhanced detection
    result = enhance_pdf_processing(args.pdf_path, args.output)
    
    print(f"Enhanced processing results:")
    print(f"  Figures: {result['enhanced_totals']['figures']}")
    print(f"  Tables: {result['enhanced_totals']['tables']}")
    
    # Show page-by-page results
    for i, page in enumerate(result['pages']):
        print(f"  Page {i+1}: {len(page.get('figures', []))} figures, {len(page.get('tables', []))} tables")

if __name__ == "__main__":
    main()
