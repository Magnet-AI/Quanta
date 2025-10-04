#!/usr/bin/env python3
"""
Main PDF Processing Program
Processes all PDFs in test_pdf folder and saves outputs to individual folders in output/
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the processing modules
from src.runner import process_pdf, setup_logging
import cv2
import numpy as np

def setup_logging_config():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('pdf_processing.log')
        ]
    )

def get_pdf_files(test_pdf_dir: str) -> List[str]:
    """Get all PDF files from test_pdf directory"""
    pdf_files = []
    test_pdf_path = Path(test_pdf_dir)
    
    if not test_pdf_path.exists():
        logging.error(f"Test PDF directory not found: {test_pdf_dir}")
        return pdf_files
    
    for file_path in test_pdf_path.glob("*.pdf"):
        pdf_files.append(str(file_path))
    
    return sorted(pdf_files)

def create_output_folder(pdf_path: str, base_output_dir: str) -> str:
    """Create output folder for a specific PDF"""
    pdf_name = Path(pdf_path).stem  # Get filename without extension
    output_dir = os.path.join(base_output_dir, pdf_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def process_pdf_debug(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """Process PDF in debug mode - generate layout overlays instead of extracting images"""
    from src.runner import process_pdf
    
    # Process normally first
    result = process_pdf(pdf_path, output_dir)
    
    # Generate debug overlays for each page
    for page_data in result['pages']:
        page_num = page_data['page_num']
        img_page = page_data['img_page']
        
        # Create overlay image
        overlay = img_page.copy()
        
        # Draw columns
        for col_x0, col_x1 in page_data.get('columns', []):
            cv2.rectangle(overlay, (col_x0, 0), (col_x1, overlay.shape[0]), (255, 0, 0), 3)
        
        # Draw text blocks
        for block in page_data.get('text_blocks', []):
            bbox = block.get('bbox_px', [0, 0, 0, 0])
            cv2.rectangle(overlay, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        
        # Draw figures
        for figure in page_data.get('figures', []):
            bbox = figure.bbox_px
            cv2.rectangle(overlay, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 0, 255), 3)
            cv2.putText(overlay, f"Fig", (bbox[0], bbox[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Draw tables
        for table in page_data.get('tables', []):
            bbox = table.bbox_px
            cv2.rectangle(overlay, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 255, 0), 3)
            cv2.putText(overlay, f"Table", (bbox[0], bbox[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Save debug overlay
        debug_path = os.path.join(output_dir, f"page_{page_num+1:02d}_layout_debug.png")
        cv2.imwrite(debug_path, overlay)
        logging.info(f"Saved debug overlay: {debug_path}")
    
    return result

def process_all_pdfs(debug_mode=False):
    """Main function to process all PDFs in test_pdf folder"""
    setup_logging_config()
    
    # Configuration
    test_pdf_dir = "test_pdf"
    base_output_dir = "output"
    
    if debug_mode:
        logging.info("🔍 DEBUG MODE: Will generate layout overlays instead of extracting images")
    
    # Get all PDF files
    pdf_files = get_pdf_files(test_pdf_dir)
    
    if not pdf_files:
        logging.error(f"No PDF files found in {test_pdf_dir} directory")
        return
    
    logging.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF
    total_figures = 0
    total_tables = 0
    processed_count = 0
    
    for i, pdf_path in enumerate(pdf_files, 1):
        try:
            pdf_name = Path(pdf_path).name
            logging.info(f"\n{'='*60}")
            logging.info(f"Processing PDF {i}/{len(pdf_files)}: {pdf_name}")
            logging.info(f"{'='*60}")
            
            # Create output folder for this PDF
            output_dir = create_output_folder(pdf_path, base_output_dir)
            
            # Process the PDF
            if debug_mode:
                result = process_pdf_debug(pdf_path, output_dir)
            else:
                result = process_pdf(pdf_path, output_dir)
            
            # Count results
            pdf_figures = sum(len(p.get('figures', [])) for p in result['pages'])
            pdf_tables = sum(len(p.get('tables', [])) for p in result['pages'])
            
            total_figures += pdf_figures
            total_tables += pdf_tables
            processed_count += 1
            
            logging.info(f"✅ Completed {pdf_name}")
            logging.info(f"   Pages processed: {len(result['pages'])}")
            logging.info(f"   Figures found: {pdf_figures}")
            logging.info(f"   Tables found: {pdf_tables}")
            logging.info(f"   Output saved to: {output_dir}")
            
        except Exception as e:
            logging.error(f"❌ Error processing {pdf_name}: {e}")
            continue
    
    # Final summary
    logging.info(f"\n{'='*60}")
    logging.info(f"PROCESSING COMPLETE")
    logging.info(f"{'='*60}")
    logging.info(f"PDFs processed: {processed_count}/{len(pdf_files)}")
    logging.info(f"Total figures extracted: {total_figures}")
    logging.info(f"Total tables extracted: {total_tables}")
    logging.info(f"Output directory: {base_output_dir}/")

def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF Layout Analysis and Extraction Tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (show layout overlays)")
    parser.add_argument("--mode", choices=["extract", "debug"], default="extract", 
                       help="Processing mode: extract images or show debug overlays")
    
    args = parser.parse_args()
    debug_mode = args.debug or args.mode == "debug"
    
    print("🚀 Starting PDF Processing Pipeline")
    if debug_mode:
        print("🔍 DEBUG MODE: Generating layout overlays")
    else:
        print("📸 EXTRACT MODE: Extracting figures and tables")
    print("=" * 50)
    
    # Check if test_pdf directory exists
    if not os.path.exists("test_pdf"):
        print("❌ Error: test_pdf directory not found!")
        print("Please create test_pdf directory and add PDF files to process.")
        sys.exit(1)
    
    # Check if there are any PDF files
    pdf_files = get_pdf_files("test_pdf")
    if not pdf_files:
        print("❌ Error: No PDF files found in test_pdf directory!")
        print("Please add PDF files to the test_pdf directory.")
        sys.exit(1)
    
    print(f"📁 Found {len(pdf_files)} PDF files to process:")
    for pdf_file in pdf_files:
        print(f"   - {Path(pdf_file).name}")
    
    print(f"\n📤 Output will be saved to: output/")
    print("=" * 50)
    
    # Process all PDFs
    process_all_pdfs(debug_mode=debug_mode)

if __name__ == "__main__":
    main()
