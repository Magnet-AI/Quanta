"""
Main script to run the complete finetuning process
"""
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_finetuning():
    """Run the complete finetuning process"""
    
    logger.info("🚀 Starting PDF Extraction Finetuning Process")
    logger.info("=" * 60)
    
    # Step 1: Extract annotations from your PDFs
    logger.info("📄 Step 1: Extracting visual annotations from annotated PDFs...")
    try:
        from utils.visual_annotation_extractor import VisualAnnotationExtractor
        
        extractor = VisualAnnotationExtractor()
        annotations = extractor.extract_all_pdfs("../dataset/annotated_pdfs")
        
        # Save annotations
        Path("data/raw").mkdir(parents=True, exist_ok=True)
        import json
        with open("data/raw/extracted_annotations.json", "w") as f:
            json.dump(annotations, f, indent=2)
        
        logger.info(f"✅ Extracted {len(annotations)} annotations")
        
        # Show summary
        label_counts = {}
        for ann in annotations:
            label = ann['label']
            label_counts[label] = label_counts.get(label, 0) + 1
        
        logger.info("📊 Annotation summary:")
        for label, count in label_counts.items():
            logger.info(f"   {label}: {count}")
            
    except Exception as e:
        logger.error(f"❌ Error extracting annotations: {e}")
        return False
    
    # Step 2: Extract features
    logger.info("\n🔍 Step 2: Extracting ML features...")
    try:
        from utils.feature_extractor import FeatureExtractor
        
        extractor = FeatureExtractor()
        
        # Load annotations
        with open("data/raw/extracted_annotations.json", "r") as f:
            annotations = json.load(f)
        
        # Extract features for each annotation
        all_features = []
        for i, ann in enumerate(annotations):
            logger.info(f"   Processing annotation {i+1}/{len(annotations)}")
            
            # Basic features
            basic_features = extractor.extract_features_from_annotation(ann)
            
            # Visual features
            visual_features = extractor.extract_visual_features(ann, ann['pdf_path'])
            
            # Text features
            text_features = extractor.extract_text_features(ann, ann['pdf_path'])
            
            # Combine all features
            combined_features = {
                **basic_features,
                **visual_features,
                **text_features,
                'label': ann['label'],
                'pdf_path': ann['pdf_path'],
                'page_num': ann['page_num']
            }
            
            all_features.append(combined_features)
        
        # Save features (convert numpy types to Python types for JSON serialization)
        import numpy as np
        
        def convert_numpy_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj
        
        all_features = convert_numpy_types(all_features)
        
        Path("data/processed").mkdir(parents=True, exist_ok=True)
        with open("data/processed/training_features.json", "w") as f:
            json.dump(all_features, f, indent=2)
        
        logger.info(f"✅ Extracted features for {len(all_features)} annotations")
        
    except Exception as e:
        logger.error(f"❌ Error extracting features: {e}")
        return False
    
    # Step 3: Train model
    logger.info("\n🤖 Step 3: Training ML model...")
    try:
        from scripts.train_model import DetectionTrainer
        
        trainer = DetectionTrainer()
        trainer.load_training_data("data/processed/training_features.json")
        
        accuracy = trainer.train()
        
        logger.info(f"✅ Model trained with {accuracy:.3f} accuracy")
        
        # Show feature importance
        trainer.get_feature_importance()
        
    except Exception as e:
        logger.error(f"❌ Error training model: {e}")
        return False
    
    # Step 4: Test on original PDF
    logger.info("\n🧪 Step 4: Testing enhanced detection...")
    try:
        from scripts.integrate_model import enhance_pdf_processing
        
        # Test on tps51633.pdf (the problematic one)
        test_pdf = "../test_pdf/tps51633.pdf"
        if Path(test_pdf).exists():
            result = enhance_pdf_processing(test_pdf, "enhanced_output")
            
            logger.info("📊 Enhanced detection results:")
            logger.info(f"   Figures: {result['enhanced_totals']['figures']}")
            logger.info(f"   Tables: {result['enhanced_totals']['tables']}")
            
            # Show page-by-page results
            for i, page in enumerate(result['pages']):
                fig_count = len(page.get('figures', []))
                table_count = len(page.get('tables', []))
                logger.info(f"   Page {i+1}: {fig_count} figures, {table_count} tables")
                
                # Highlight page 11 (the problematic one)
                if i == 10:  # Page 11 (0-indexed)
                    logger.info(f"   🎯 Page 11 (problematic): {fig_count} figures, {table_count} tables")
        else:
            logger.warning(f"Test PDF not found: {test_pdf}")
        
    except Exception as e:
        logger.error(f"❌ Error testing enhanced detection: {e}")
        return False
    
    logger.info("\n🎉 Finetuning process completed successfully!")
    logger.info("=" * 60)
    
    return True

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
PDF Extraction Finetuning System

This script will:
1. Extract annotations from your colored PDFs
2. Extract ML features from the annotations
3. Train a model to improve detection accuracy
4. Test the enhanced system

Usage:
    python run_finetuning.py

Requirements:
    - Annotated PDFs in ../dataset/annotated_pdfs/
    - Original PDFs in ../test_pdf/
""")
        return
    
    success = run_finetuning()
    
    if success:
        print("\n✅ Finetuning completed successfully!")
        print("📁 Check the 'enhanced_output' folder for results")
        print("🔧 The trained model is saved in 'models/detection_classifier.pkl'")
    else:
        print("\n❌ Finetuning failed. Check the logs above for errors.")

if __name__ == "__main__":
    main()
