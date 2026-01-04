"""
Quanta PDF extraction SDK

Public API:
- extract_document(input_pdf, output_dir, debug=False) -> dict

Returns a dict compatible with the existing pipeline result, including per-page
artifacts and summary paths.
"""

from pathlib import Path
from typing import Any, Dict, List, Union

# Import from existing internal modules installed as top-level packages
# These modules already exist under src/core, src/detection, etc.
from core.pipeline_processor import process_pdf  # type: ignore
from .types import ExtractConfig, ExtractResult, ExtractPageArtifacts


def extract_document(
    input_pdf: Union[str, Path],
    output_dir: Union[str, Path],
    *,
    debug: bool = False,
) -> Dict[str, Any]:
    """Run the full extraction pipeline and return the result dict.

    Parameters
    ----------
    input_pdf: str | Path
        Path to the input PDF file.
    output_dir: str | Path
        Directory to write outputs (images, CSVs, text, summary.json).
    debug: bool
        If True, downstream consumers can choose to draw overlays separately.

    Returns
    -------
    dict
        Pipeline result structure produced by process_pdf.
    """
    input_path = str(input_pdf)
    output_path = str(output_dir)
    return process_pdf(input_path, output_path)


def extract(
    config: ExtractConfig,
) -> ExtractResult:
    """Typed convenience API wrapping extract_document.

    Builds a normalized ExtractResult with concrete artifact paths.
    """
    result = extract_document(str(config.input_pdf), str(config.output_dir), debug=config.debug)
    pages: List[ExtractPageArtifacts] = []
    total_figures = 0
    total_tables = 0

    for page in result.get("pages", []):
        page_num = int(page.get("page_num", 0)) + 1
        outputs = page.get("outputs", {})
        # Collect figure paths in sorted order
        figure_paths: List[Path] = []
        i = 1
        while True:
            key = f"figure_{i}"
            if key not in outputs:
                break
            figure_paths.append(Path(outputs[key]))
            i += 1

        # Collect table csv paths in sorted order
        table_csv_paths: List[Path] = []
        i = 1
        while True:
            key = f"table_{i}_csv"
            if key not in outputs:
                break
            table_csv_paths.append(Path(outputs[key]))
            i += 1

        text_path = Path(outputs["text"]) if "text" in outputs else None
        page_image_path = Path(outputs["page_image"]) if "page_image" in outputs else None

        pages.append(
            ExtractPageArtifacts(
                page_number=page_num,
                figure_paths=figure_paths,
                table_csv_paths=table_csv_paths,
                text_path=text_path,
                page_image_path=page_image_path,
            )
        )

        total_figures += len(figure_paths)
        total_tables += len(table_csv_paths)

    summary_path = Path(result["summary_path"]) if result.get("summary_path") else None
    return ExtractResult(
        pages=pages,
        summary_path=summary_path,
        total_figures=total_figures,
        total_tables=total_tables,
    )


__all__ = ["extract_document", "extract", "ExtractConfig", "ExtractResult", "ExtractPageArtifacts"]


