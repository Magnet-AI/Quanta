"""
Main CLI orchestrator for PDF extraction pipeline
"""
import argparse
import logging
import os
import sys
from typing import List, Dict, Any
from pathlib import Path

# Import all modules
from .pdf_handler import load_pdf_page_data, get_page_info
from ..detection.column_detector import detect_columns
from ..detection.text_detector import extract_text_blocks, group_lines_into_paragraphs, detect_headings
from ..detection.figure_detector import (
    detect_figures,
    crop_figure_image,
    expand_figures_content_aware,
    expand_figures_away_from_text,
)
from ..detection.table_detector import extract_tables, save_table_csv
from ..processing.caption_processor import link_captions
from ..processing.content_organizer import assemble_sections, determine_title
from .output_manager import write_page_outputs, create_summary_report, write_audit_log

def filter_figures_away_from_tables(figures: List[Any], tables: List[Any]) -> List[Any]:
    """
    Filter out figures that overlap significantly with table areas
    
    Args:
        figures: List of Figure objects
        tables: List of table objects
        
    Returns:
        Filtered list of figures
    """
    if not tables:
        return figures
    
    filtered_figures = []
    
    for figure in figures:
        fig_bbox = figure.bbox_px
        fig_x0, fig_y0, fig_x1, fig_y1 = fig_bbox
        
        # Check if figure overlaps with any table
        overlaps_with_table = False
        for table in tables:
            table_bbox = table.bbox_px
            table_x0, table_y0, table_x1, table_y1 = table_bbox
            
            # Calculate overlap
            overlap_x0 = max(fig_x0, table_x0)
            overlap_y0 = max(fig_y0, table_y0)
            overlap_x1 = min(fig_x1, table_x1)
            overlap_y1 = min(fig_y1, table_y1)
            
            if overlap_x0 < overlap_x1 and overlap_y0 < overlap_y1:
                # Calculate overlap area
                overlap_area = (overlap_x1 - overlap_x0) * (overlap_y1 - overlap_y0)
                fig_area = (fig_x1 - fig_x0) * (fig_y1 - fig_y0)
                
                # If more than 50% of figure overlaps with table, filter it out
                if fig_area > 0 and overlap_area / fig_area > 0.5:
                    overlaps_with_table = True
                    logging.info(f"Filtering figure {fig_bbox} that overlaps with table {table_bbox}")
                    break
        
        if not overlaps_with_table:
            filtered_figures.append(figure)
    
    logging.info(f"Filtered {len(figures) - len(filtered_figures)} figures that overlapped with tables")
    return filtered_figures

def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('pdf_extract.log')
        ]
    )

def process_page(pdf_path: str, page_num: int, output_dir: str) -> Dict[str, Any]:
    """
    Process a single page through the complete pipeline
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        output_dir: Output directory
        
    Returns:
        Dictionary containing page data and outputs
    """
    import time
    start_time = time.time()
    
    print(f"📄 Processing page {page_num + 1}...")
    
    # Step A: Load & Preflight
    print("  ⏳ Loading PDF data...")
    page_data = load_pdf_page_data(pdf_path, page_num)
    page_data['page_num'] = page_num
    
    # Step B: Column Detection
    print("  ⏳ Detecting columns...")
    columns = detect_columns(page_data['img_page'])
    page_data['columns'] = columns
    
    # Step C: Text Blocks
    print("  ⏳ Extracting text...")
    text_blocks = extract_text_blocks(page_data['raw_dict'])
    text_blocks = group_lines_into_paragraphs(text_blocks)
    text_blocks = detect_headings(text_blocks)
    
    # Filter text blocks to columns
    from ..detection.text_detector import filter_blocks_in_columns
    text_blocks = filter_blocks_in_columns(text_blocks, columns)
    page_data['text_blocks'] = text_blocks
    
    # Step D: Extract content using Mistral OCR for tables/text, custom for images
    print("  ⏳ Extracting content with Mistral OCR...")
    
    try:
        from ..extraction.mistral_service import MistralOCR
        mistral_ocr = MistralOCR()
        mistral_result = mistral_ocr.process_pdf_page(pdf_path, page_num + 1)
        
        mistral_tables = mistral_result.get("tables", [])
        mistral_text_blocks = mistral_result.get("text_blocks", [])
        print(f"    🔍 Mistral found {len(mistral_tables)} tables, {len(mistral_text_blocks)} text blocks")
        
        # Create tables from Mistral data (CSV only, no images needed)
        tables = []
        for i, mistral_table in enumerate(mistral_tables):
            from ..detection.table_detector import Table
            
            # Create cells from Mistral data
            cells = []
            for r, row in enumerate(mistral_table.get("rows", [])):
                for c, cell_text in enumerate(row):
                    cells.append({
                        "r": r,
                        "c": c,
                        "text": cell_text,
                        "bbox_px": [0, 0, 0, 0]
                    })
            
            # Use a default bbox since we don't need images
            page_w, page_h = page_data['page_size']['px']
            bbox_px = [page_w//4, page_h//4, 3*page_w//4, 3*page_h//4]
            
            table = Table(
                bbox_px=bbox_px,
                cells=cells,
                detection_method="mistral_ocr"
            )
            tables.append(table)
            print(f"    🔍 Created table {i+1} with {len(mistral_table.get('rows', []))} rows")
        
    except Exception as e:
        print(f"    ⚠️ Mistral OCR failed: {e}")
        tables = []
        mistral_text_blocks = []
    
    page_data['tables'] = tables
    page_data['mistral_text_blocks'] = mistral_text_blocks
    
    # Step E: Figure Detection (after tables to avoid detecting figures in table areas)
    print("  ⏳ Detecting figures...")
    figures = detect_figures(
        page_data['drawings'], 
        page_data['xobjects'], 
        columns, 
        page_data['page_size'],
        page_data['text_blocks']  # Pass text blocks for better boundary refinement
    )
    
    # Filter out figures that overlap with table areas
    figures = filter_figures_away_from_tables(figures, tables)
    page_data['figures'] = figures
    
    # Content-aware expand to prevent tight crops, avoiding text regions
    try:
        # First try edge-based growth, then whitespace-to-text growth for robustness
        expand_figures_content_aware(page_data['img_page'], figures, text_blocks)
        expand_figures_away_from_text(figures, text_blocks, page_data['page_size'])
    except Exception as e:
        logging.warning(f"Figure expansion skipped: {e}")
    
    # Step F: Caption Detection
    print("  ⏳ Linking captions...")
    captions = link_captions(text_blocks, figures, tables)
    page_data['captions'] = captions
    
    # Step G: Headings & Sections
    print("  ⏳ Assembling sections...")
    sections = assemble_sections(text_blocks, figures, tables, captions)
    page_data['sections'] = sections
    
    # Step H: Reading Order
    title = determine_title(text_blocks)
    page_data['title'] = title
    
    # Step I: Exports
    print("  ⏳ Writing outputs...")
    outputs = write_page_outputs(page_num, page_data, output_dir, debug=False)
    page_data['outputs'] = outputs
    
    elapsed = time.time() - start_time
    print(f"  ✅ Completed page {page_num + 1} in {elapsed:.1f}s")
    return page_data

def process_pdf(pdf_path: str, output_dir: str, pages: List[int] = None) -> Dict[str, Any]:
    """
    Process a PDF file through the complete pipeline
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory
        pages: List of page numbers to process (None for all pages)
        
    Returns:
        Dictionary containing all page data
    """
    logging.info(f"Processing PDF: {pdf_path}")
    
    # Get PDF info
    pdf_info = get_page_info(pdf_path)
    total_pages = pdf_info['num_pages']
    
    if pages is None:
        pages = list(range(total_pages))
    
    logging.info(f"Processing {len(pages)} pages out of {total_pages}")
    
    # Process each page
    all_pages_data = []
    for page_num in pages:
        try:
            page_data = process_page(pdf_path, page_num, output_dir)
            all_pages_data.append(page_data)
        except Exception as e:
            logging.error(f"Error processing page {page_num + 1}: {e}")
            continue
    
    # Create summary report
    summary_path = os.path.join(output_dir, "summary.json")
    create_summary_report(all_pages_data, summary_path)
    
    logging.info(f"Completed processing {len(all_pages_data)} pages")
    return {
        'pdf_info': pdf_info,
        'pages': all_pages_data,
        'summary_path': summary_path
    }

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="PDF extraction pipeline for structured layout analysis"
    )
    
    parser.add_argument(
        "pdf_path", 
        help="Path to input PDF file"
    )
    
    parser.add_argument(
        "-o", "--output", 
        default="outputs",
        help="Output directory (default: outputs)"
    )
    
    parser.add_argument(
        "-p", "--pages",
        help="Comma-separated list of page numbers to process (1-indexed, e.g., '1,3,5-7')"
    )
    
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Validate input file
    if not os.path.exists(args.pdf_path):
        logging.error(f"PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Parse page numbers
    pages = None
    if args.pages:
        pages = parse_page_numbers(args.pages)
        if not pages:
            logging.error("Invalid page numbers format")
            sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    try:
        # Process PDF
        result = process_pdf(args.pdf_path, args.output, pages)
        
        # Print summary
        print(f"\nProcessing complete!")
        print(f"PDF: {args.pdf_path}")
        print(f"Output directory: {args.output}")
        print(f"Pages processed: {len(result['pages'])}")
        print(f"Total figures: {sum(len(p.get('figures', [])) for p in result['pages'])}")
        print(f"Total tables: {sum(len(p.get('tables', [])) for p in result['pages'])}")
        print(f"Summary report: {result['summary_path']}")
        
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        sys.exit(1)

def parse_page_numbers(page_str: str) -> List[int]:
    """
    Parse page number string into list of page numbers
    
    Args:
        page_str: String like "1,3,5-7,10"
        
    Returns:
        List of page numbers (0-indexed)
    """
    pages = []
    
    for part in page_str.split(','):
        part = part.strip()
        
        if '-' in part:
            # Range like "5-7"
            start, end = part.split('-', 1)
            try:
                start_num = int(start) - 1  # Convert to 0-indexed
                end_num = int(end) - 1
                pages.extend(range(start_num, end_num + 1))
            except ValueError:
                return []
        else:
            # Single page number
            try:
                page_num = int(part) - 1  # Convert to 0-indexed
                pages.append(page_num)
            except ValueError:
                return []
    
    return sorted(set(pages))

def run_single_page(pdf_path: str, page_num: int, output_dir: str = "outputs", 
                   debug: bool = False) -> Dict[str, Any]:
    """
    Run pipeline on a single page (for testing)
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        output_dir: Output directory
        debug: Whether to generate debug outputs
        
    Returns:
        Dictionary containing page data
    """
    setup_logging("INFO")
    return process_page(pdf_path, page_num, output_dir, debug)

if __name__ == "__main__":
    main()
