"""
Export functionality - JSON/CSV output and debug overlays
"""
import json
import csv
import os
import numpy as np
import cv2
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

def write_page_outputs(page_num: int, page_data: Dict[str, Any], 
                      output_dir: str, debug: bool = False) -> Dict[str, Any]:
    """
    Write all outputs for a single page with organized directory structure
    
    Args:
        page_num: Page number (0-indexed)
        page_data: Dictionary containing all page data
        output_dir: Output directory
        debug: Whether to generate debug outputs
        
    Returns:
        Dictionary with output file paths
    """
    page_name = f"page_{page_num + 1:02d}"  # Zero-padded page numbers
    outputs = {}
    
    # Create page-specific directory structure
    page_dir = os.path.join(output_dir, page_name)
    figures_dir = os.path.join(page_dir, "figures")
    tables_dir = os.path.join(page_dir, "tables")
    text_dir = os.path.join(page_dir, "text")
    
    os.makedirs(page_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)
    os.makedirs(tables_dir, exist_ok=True)
    os.makedirs(text_dir, exist_ok=True)
    
    # Write figure images to figures directory
    if 'figures' in page_data and page_data['figures']:
        for i, figure in enumerate(page_data['figures']):
            fig_filename = f"figure_{i+1:02d}.png"
            fig_path = os.path.join(figures_dir, fig_filename)
            crop_figure_image(page_data['img_page'], figure, fig_path)
            figure.image_path = fig_path
            outputs[f'figure_{i+1}'] = fig_path
    
    # Write table CSV files to tables directory (no PNG images)
    if 'tables' in page_data and page_data['tables']:
        for i, table in enumerate(page_data['tables']):
            # Table CSV only
            table_csv_filename = f"table_{i+1:02d}.csv"
            table_csv_path = os.path.join(tables_dir, table_csv_filename)
            save_table_csv(table, table_csv_path)
            outputs[f'table_{i+1}_csv'] = table_csv_path
    
    # Write Mistral text blocks to text directory
    if 'mistral_text_blocks' in page_data and page_data['mistral_text_blocks']:
        text_filename = "text_blocks.txt"
        text_path = os.path.join(text_dir, text_filename)
        
        with open(text_path, 'w', encoding='utf-8') as f:
            for i, text_block in enumerate(page_data['mistral_text_blocks']):
                f.write(f"Text Block {i+1}:\n")
                # Handle both dict and list formats
                if isinstance(text_block, dict):
                    f.write(f"{text_block.get('text', '')}\n")
                    f.write(f"BBox: {text_block.get('bbox_px', [0,0,0,0])}\n")
                else:
                    f.write(f"{text_block}\n")
                    f.write(f"BBox: [0,0,0,0]\n")
                f.write("-" * 50 + "\n")
        
        outputs['text'] = text_path
    
    # Write full page image to page directory
    page_img_path = os.path.join(page_dir, f"{page_name}.png")
    save_page_image(page_data['img_page'], page_img_path)
    outputs['page_image'] = page_img_path
    
    return outputs

def save_page_image(img: np.ndarray, output_path: str) -> None:
    """
    Save full page image
    
    Args:
        img: Full page image
        output_path: Path to save image
    """
    # Convert RGB to BGR for OpenCV
    if len(img.shape) == 3 and img.shape[2] == 3:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img
    
    # Save image
    cv2.imwrite(output_path, img_bgr)

def write_page_json(page_data: Dict[str, Any], output_path: str) -> None:
    """
    Write page data as JSON file
    
    Args:
        page_data: Dictionary containing page data
        output_path: Path to save JSON file
    """
    # Convert page data to JSON-serializable format
    json_data = {
        "page_size": page_data.get('page_size', {}),
        "columns": page_data.get('columns', []),
        "title": page_data.get('title', ''),
        "sections": [],
        "figures": [],
        "tables": [],
        "captions": [],
        "text_blocks": []
    }
    
    # Add sections
    if 'sections' in page_data:
        for section in page_data['sections']:
            json_data['sections'].append({
                "heading": section.heading,
                "paragraphs": section.paragraphs
            })
    
    # Add figures
    if 'figures' in page_data:
        for i, figure in enumerate(page_data['figures']):
            fig_data = {
                "bbox_px": figure.bbox_px,
                "image": f"page_{page_data.get('page_num', 0) + 1}_fig_{i+1}.png",
                "caption": figure.caption.text if figure.caption else "",
                "source": figure.source
            }
            json_data['figures'].append(fig_data)
    
    # Add tables
    if 'tables' in page_data:
        for i, table in enumerate(page_data['tables']):
            table_data = {
                "bbox_px": table.bbox_px,
                "image": f"page_{page_data.get('page_num', 0) + 1}_table_{i+1}.png",
                "csv": f"page_{page_data.get('page_num', 0) + 1}_table_{i+1}.csv",
                "cells": table.cells,
                "caption": table.caption.text if table.caption else ""
            }
            json_data['tables'].append(table_data)
    
    # Add captions
    if 'captions' in page_data:
        for caption in page_data['captions']:
            json_data['captions'].append({
                "bbox_px": caption.bbox_px,
                "text": caption.text
            })
    
    # Add text blocks
    if 'text_blocks' in page_data:
        for block in page_data['text_blocks']:
            json_data['text_blocks'].append({
                "bbox_px": block.bbox_px,
                "text": block.text,
                "font_size": block.font_size,
                "is_bold": block.is_bold,
                "is_italic": block.is_italic,
                "is_heading": getattr(block, 'is_heading', False)
            })
    
    # Write JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

def crop_figure_image(img: np.ndarray, figure: Any, output_path: str) -> None:
    """
    Crop and save figure image
    
    Args:
        img: Full page image
        figure: Figure object
        output_path: Path to save cropped image
    """
    x0, y0, x1, y1 = figure.bbox_px
    
    # Ensure coordinates are within image bounds
    h, w = img.shape[:2]
    x0 = max(0, min(x0, w-1))
    y0 = max(0, min(y0, h-1))
    x1 = max(x0+1, min(x1, w))
    y1 = max(y0+1, min(y1, h))
    
    # Crop image
    cropped = img[y0:y1, x0:x1].copy()
    
    # Convert RGB to BGR for OpenCV
    if len(cropped.shape) == 3 and cropped.shape[2] == 3:
        cropped_bgr = cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR)
    else:
        cropped_bgr = cropped
    
    # Save image
    cv2.imwrite(output_path, cropped_bgr)

def crop_table_image(img: np.ndarray, table: Any, output_path: str) -> None:
    """
    Crop and save table image
    
    Args:
        img: Full page image
        table: Table object
        output_path: Path to save cropped image
    """
    x0, y0, x1, y1 = table.bbox_px
    
    # Ensure coordinates are within image bounds
    h, w = img.shape[:2]
    x0 = max(0, min(x0, w-1))
    y0 = max(0, min(y0, h-1))
    x1 = max(x0+1, min(x1, w))
    y1 = max(y0+1, min(y1, h))
    
    # Crop image
    cropped = img[y0:y1, x0:x1].copy()
    
    # Convert RGB to BGR for OpenCV
    if len(cropped.shape) == 3 and cropped.shape[2] == 3:
        cropped_bgr = cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR)
    else:
        cropped_bgr = cropped
    
    # Save image
    cv2.imwrite(output_path, cropped_bgr)

def save_table_csv(table: Any, output_path: str) -> None:
    """
    Save table data as CSV file
    
    Args:
        table: Table object
        output_path: Path to save CSV file
    """
    if not table.cells:
        return
    
    # Create 2D array
    data = [[""] * table.num_cols for _ in range(table.num_rows)]
    
    for cell in table.cells:
        r = cell['r']
        c = cell['c']
        text = cell['text']
        if r < table.num_rows and c < table.num_cols:
            data[r][c] = text
    
    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)

def create_debug_overlay(page_data: Dict[str, Any], output_path: str) -> None:
    """
    Create debug overlay image with color-coded regions
    
    Args:
        page_data: Dictionary containing page data
        output_path: Path to save overlay image
    """
    img = page_data['img_page'].copy()
    
    # Define colors (BGR format for OpenCV)
    colors = {
        'figure': (0, 255, 0),      # Green
        'table': (255, 0, 255),     # Purple
        'caption': (0, 165, 255),   # Orange
        'heading': (255, 255, 0),   # Teal
        'text': (255, 0, 0),        # Blue
        'column': (128, 128, 128)   # Gray
    }
    
    # Draw columns
    if 'columns' in page_data:
        for x0, x1 in page_data['columns']:
            cv2.rectangle(img, (x0, 0), (x1, img.shape[0]), colors['column'], 2)
    
    # Draw figures
    if 'figures' in page_data:
        for figure in page_data['figures']:
            x0, y0, x1, y1 = figure.bbox_px
            cv2.rectangle(img, (x0, y0), (x1, y1), colors['figure'], 2)
            cv2.putText(img, "FIG", (x0, y0-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors['figure'], 1)
    
    # Draw tables
    if 'tables' in page_data:
        for table in page_data['tables']:
            x0, y0, x1, y1 = table.bbox_px
            cv2.rectangle(img, (x0, y0), (x1, y1), colors['table'], 2)
            cv2.putText(img, "TBL", (x0, y0-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors['table'], 1)
    
    # Draw captions
    if 'captions' in page_data:
        for caption in page_data['captions']:
            x0, y0, x1, y1 = caption.bbox_px
            cv2.rectangle(img, (x0, y0), (x1, y1), colors['caption'], 2)
            cv2.putText(img, "CAP", (x0, y0-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors['caption'], 1)
    
    # Draw text blocks
    if 'text_blocks' in page_data:
        for i, block in enumerate(page_data['text_blocks']):
            x0, y0, x1, y1 = block.bbox_px
            color = colors['heading'] if getattr(block, 'is_heading', False) else colors['text']
            cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)
            # Add text label
            label = "H" if getattr(block, 'is_heading', False) else "T"
            cv2.putText(img, f"{label}{i+1}", (x0, y0-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Convert RGB to BGR for OpenCV
    if len(img.shape) == 3 and img.shape[2] == 3:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img
    
    # Save overlay image
    cv2.imwrite(output_path, img_bgr)

def write_audit_log(page_data: Dict[str, Any], output_path: str) -> None:
    """
    Write audit log for a page
    
    Args:
        page_data: Dictionary containing page data
        output_path: Path to save audit log
    """
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "page_num": page_data.get('page_num', 0),
        "page_size": page_data.get('page_size', {}),
        "num_columns": len(page_data.get('columns', [])),
        "num_text_blocks": len(page_data.get('text_blocks', [])),
        "num_figures": len(page_data.get('figures', [])),
        "num_tables": len(page_data.get('tables', [])),
        "num_captions": len(page_data.get('captions', [])),
        "num_sections": len(page_data.get('sections', [])),
        "is_scanned": page_data.get('is_scanned', False),
        "painted_image_area": page_data.get('painted_image_area', 0.0)
    }
    
    # Add figure detection stats
    if 'figures' in page_data:
        vector_figs = sum(1 for f in page_data['figures'] if f.source == 'vector')
        image_figs = sum(1 for f in page_data['figures'] if f.source == 'image')
        mixed_figs = sum(1 for f in page_data['figures'] if f.source == 'mixed')
        
        log_data['figure_stats'] = {
            "vector": vector_figs,
            "image": image_figs,
            "mixed": mixed_figs
        }
    
    # Add table detection stats
    if 'tables' in page_data:
        ruled_tables = sum(1 for t in page_data['tables'] if t.detection_method == 'ruled')
        borderless_tables = sum(1 for t in page_data['tables'] if t.detection_method == 'borderless')
        
        log_data['table_stats'] = {
            "ruled": ruled_tables,
            "borderless": borderless_tables
        }
    
    # Write log file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

def create_summary_report(all_pages_data: List[Dict[str, Any]], output_path: str) -> None:
    """
    Create a summary report for all pages with organized structure info
    
    Args:
        all_pages_data: List of page data dictionaries
        output_path: Path to save summary report
    """
    summary = {
        "extraction_info": {
            "total_pages": len(all_pages_data),
            "total_figures": 0,
            "total_tables": 0,
            "scanned_pages": 0
        },
        "directory_structure": {
            "page_XX/": "Page-specific folder containing all content for that page",
            "page_XX/figures/": "Figure images for this page",
            "page_XX/tables/": "Table CSV files for this page", 
            "page_XX/text/": "Text blocks for this page",
            "page_XX/page_XX.png": "Full page image"
        },
        "pages": []
    }
    
    for page_data in all_pages_data:
        page_num = page_data.get('page_num', 0) + 1
        figures = page_data.get('figures', [])
        tables = page_data.get('tables', [])
        
        page_summary = {
            "page_number": page_num,
            "figures_count": len(figures),
            "tables_count": len(tables),
            "figures": [f"figure_{i+1:02d}.png" for i in range(len(figures))],
            "tables": [f"table_{i+1:02d}.csv" for i in range(len(tables))],
            "page_image": f"page_{page_num:02d}.png",
            "page_directory": f"page_{page_num:02d}/"
        }
        
        summary["pages"].append(page_summary)
        summary["extraction_info"]["total_figures"] += len(figures)
        summary["extraction_info"]["total_tables"] += len(tables)
        
        if page_data.get('is_scanned', False):
            summary["extraction_info"]["scanned_pages"] += 1
    
    # Write summary report
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

def validate_outputs(outputs: Dict[str, Any]) -> bool:
    """
    Validate that all output files were created successfully
    
    Args:
        outputs: Dictionary of output file paths
        
    Returns:
        True if all outputs are valid
    """
    for key, path in outputs.items():
        if not os.path.exists(path):
            logging.error(f"Output file not found: {path}")
            return False
    
    return True

def cleanup_temp_files(temp_dir: str) -> None:
    """
    Clean up temporary files
    
    Args:
        temp_dir: Directory containing temporary files
    """
    if os.path.exists(temp_dir):
        import shutil
        shutil.rmtree(temp_dir)
        logging.info(f"Cleaned up temporary directory: {temp_dir}")
