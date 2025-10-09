from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ExtractConfig:
    input_pdf: Path
    output_dir: Path
    pages: Optional[List[int]] = None  # 1-indexed page numbers if provided
    debug: bool = False


@dataclass
class ExtractPageArtifacts:
    page_number: int  # 1-indexed
    figure_paths: List[Path]
    table_csv_paths: List[Path]
    text_path: Optional[Path]
    page_image_path: Optional[Path]


@dataclass
class ExtractResult:
    pages: List[ExtractPageArtifacts]
    summary_path: Optional[Path]
    total_figures: int
    total_tables: int

