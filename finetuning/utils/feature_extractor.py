"""
Extract ML features from annotations and detections
"""
import numpy as np
import cv2
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF
from pathlib import Path
import logging

class FeatureExtractor:
    def __init__(self):
        self.dpi = 150  # Match your system's DPI
    
    def extract_features_from_annotation(self, annotation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract ML features from an annotation
        
        Args:
            annotation: Annotation data from PDF
            
        Returns:
            Dictionary of features
        """
        bbox = annotation['bbox_px']
        x0, y0, x1, y1 = bbox
        width = x1 - x0
        height = y1 - y0
        
        # Basic geometric features
        features = {
            'area': width * height,
            'aspect_ratio': width / height if height > 0 else 0,
            'width': width,
            'height': height,
            'center_x': (x0 + x1) / 2,
            'center_y': (y0 + y1) / 2,
            'perimeter': 2 * (width + height),
            'compactness': (width * height) / (width + height) ** 2 if (width + height) > 0 else 0,
        }
        
        # Position features (normalized)
        page_width = annotation.get('page_width', 1275)  # Default page width
        page_height = annotation.get('page_height', 1650)  # Default page height
        
        features.update({
            'relative_x': features['center_x'] / page_width,
            'relative_y': features['center_y'] / page_height,
            'relative_width': width / page_width,
            'relative_height': height / page_height,
            'relative_area': features['area'] / (page_width * page_height),
        })
        
        return features
    
    def extract_visual_features(self, annotation: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
        """
        Extract visual features from the annotated region
        
        Args:
            annotation: Annotation data
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary of visual features
        """
        try:
            # Load PDF and render the specific page
            doc = fitz.open(pdf_path)
            page = doc[annotation['page_num']]
            
            # Render page to image
            mat = fitz.Matrix(self.dpi/72, self.dpi/72)
            pix = page.get_pixmap(matrix=mat)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            
            if img.shape[2] == 4:  # RGBA
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
            elif img.shape[2] == 1:  # Grayscale
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            
            # Crop the annotated region
            bbox = annotation['bbox_px']
            x0, y0, x1, y1 = bbox
            crop = img[y0:y1, x0:x1]
            
            if crop.size == 0:
                doc.close()
                return {}
            
            # Extract visual features
            visual_features = self._analyze_image_region(crop)
            
            doc.close()
            return visual_features
            
        except Exception as e:
            logging.warning(f"Error extracting visual features: {e}")
            return {}
    
    def _analyze_image_region(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze visual features of an image region"""
        if img.size == 0:
            return {}
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        features = {}
        
        # Edge density
        edges = cv2.Canny(gray, 50, 150)
        features['edge_density'] = np.sum(edges > 0) / (img.shape[0] * img.shape[1])
        
        # Line detection
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
        features['line_count'] = len(lines) if lines is not None else 0
        features['line_density'] = features['line_count'] / (img.shape[0] * img.shape[1])
        
        # Contour analysis
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        features['contour_count'] = len(contours)
        
        # Texture analysis
        features['texture_energy'] = self._calculate_texture_energy(gray)
        features['texture_contrast'] = self._calculate_texture_contrast(gray)
        
        # Color analysis
        features['color_variance'] = np.var(img.reshape(-1, 3), axis=0).mean()
        
        # Brightness
        features['mean_brightness'] = np.mean(gray)
        features['brightness_std'] = np.std(gray)
        
        return features
    
    def _calculate_texture_energy(self, gray: np.ndarray) -> float:
        """Calculate texture energy using local binary patterns"""
        if gray.size == 0:
            return 0.0
        
        # Simple texture energy calculation
        kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
        filtered = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        return np.mean(filtered ** 2)
    
    def _calculate_texture_contrast(self, gray: np.ndarray) -> float:
        """Calculate texture contrast"""
        if gray.size == 0:
            return 0.0
        
        # Calculate local contrast
        kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]])
        filtered = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        return np.std(filtered)
    
    def extract_text_features(self, annotation: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
        """
        Extract text-based features from the annotated region
        
        Args:
            annotation: Annotation data
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary of text features
        """
        try:
            # Load PDF and get text from the page
            doc = fitz.open(pdf_path)
            page = doc[annotation['page_num']]
            
            # Get text blocks in the annotated region
            bbox_px = annotation['bbox_px']
            # Convert pixels to points
            dpi = 150
            x0_pt = bbox_px[0] * (72 / dpi)
            y0_pt = bbox_px[1] * (72 / dpi)
            x1_pt = bbox_px[2] * (72 / dpi)
            y1_pt = bbox_px[3] * (72 / dpi)
            rect = fitz.Rect(x0_pt, y0_pt, x1_pt, y1_pt)
            
            # Get text in the region
            text_dict = page.get_text("dict", clip=rect)
            
            # Extract text features
            text_features = self._analyze_text_content(text_dict)
            
            doc.close()
            return text_features
            
        except Exception as e:
            logging.warning(f"Error extracting text features: {e}")
            return {}
    
    def _analyze_text_content(self, text_dict: Dict) -> Dict[str, Any]:
        """Analyze text content for features"""
        features = {}
        
        # Count text blocks and characters
        total_chars = 0
        total_words = 0
        text_blocks = 0
        font_sizes = []
        
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                text_blocks += 1
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span.get("text", "")
                        total_chars += len(text)
                        total_words += len(text.split())
                        font_sizes.append(span.get("size", 0))
        
        features.update({
            'text_block_count': text_blocks,
            'total_characters': total_chars,
            'total_words': total_words,
            'avg_font_size': np.mean(font_sizes) if font_sizes else 0,
            'font_size_std': np.std(font_sizes) if font_sizes else 0,
            'char_density': total_chars / max(1, text_blocks),
            'word_density': total_words / max(1, text_blocks),
        })
        
        # Check for specific patterns
        all_text = " ".join([
            span.get("text", "") 
            for block in text_dict.get("blocks", []) 
            for line in block.get("lines", []) 
            for span in line.get("spans", [])
        ])
        
        features.update(self._analyze_text_patterns(all_text))
        
        return features
    
    def _analyze_text_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze text for specific patterns"""
        import re
        
        features = {}
        
        # Dimension patterns
        dimension_patterns = [
            r'\(\d+\.?\d*\)',  # (0.715)
            r'\(\d+\.?\d*\s*[A-Za-z]+\)',  # (R0.05) TYP
            r'\d+X\s*\(\d+\.?\d*\)',  # 32X (0.55)
        ]
        
        dimension_count = 0
        for pattern in dimension_patterns:
            dimension_count += len(re.findall(pattern, text))
        
        features['dimension_patterns'] = dimension_count
        
        # Technical keywords
        tech_keywords = [
            'stencil', 'design', 'vqfn', 'quad', 'flatpack', 'lead', 'metal',
            'laser', 'cutting', 'apertures', 'trapezoidal', 'rounded', 'corners',
            'ipc-7525', 'texas', 'instruments', 'example', 'based', 'thick',
            'printed', 'scale', 'continued', 'notes', 'symm', 'typ', 'max',
            'height', 'width', 'diameter', 'radius', 'exposed', 'pad', 'solder',
            'paste', 'coverage', 'area', 'package', 'mm', 'dimensions'
        ]
        
        tech_keyword_count = sum(1 for keyword in tech_keywords if keyword.lower() in text.lower())
        features['tech_keywords'] = tech_keyword_count
        
        # Table keywords
        table_keywords = [
            'status', 'material', 'package', 'qty', 'rohs', 'lead', 'msl', 'temp',
            'part', 'number', 'type', 'pins', 'carrier', 'finish', 'rating', 'reflow',
            'active', 'production', 'vqfn', 'rsm', 'nipdau', 'level-1', 'unlimited',
            'orderable', 'ball', 'peak', 'op', 'marking', 'addendum', 'information'
        ]
        
        table_keyword_count = sum(1 for keyword in table_keywords if keyword.lower() in text.lower())
        features['table_keywords'] = table_keyword_count
        
        # Text length patterns
        features['avg_word_length'] = np.mean([len(word) for word in text.split()]) if text.split() else 0
        features['text_length'] = len(text)
        
        return features

def main():
    """Test the feature extractor"""
    extractor = FeatureExtractor()
    
    # Load annotations
    import json
    with open("data/raw/extracted_annotations.json", "r") as f:
        annotations = json.load(f)
    
    print(f"Processing {len(annotations)} annotations...")
    
    # Extract features for each annotation
    all_features = []
    for i, ann in enumerate(annotations):
        print(f"Processing annotation {i+1}/{len(annotations)}")
        
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
    
    # Save features
    output_file = "data/processed/training_features.json"
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(all_features, f, indent=2)
    
    print(f"Extracted features for {len(all_features)} annotations")
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()
