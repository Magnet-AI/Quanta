# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Debug mode with visual overlay generation
- Professional documentation and examples
- MIT License and contributing guidelines
- Modern Python packaging with pyproject.toml
- Comprehensive error handling for PDF parsing
- Improved table detection algorithms
- Enhanced figure detection with better filtering

### Changed
- Improved accuracy for table detection
- More robust error handling for malformed PDFs
- Better figure filtering to reduce false positives
- Enhanced debug visualization with color-coded overlays

### Fixed
- Fixed "list index out of range" errors in table detection
- Resolved MuPDF format errors with proper exception handling
- Improved grid extraction with better validation
- Fixed figure detection parameters for better accuracy

## [1.0.0] - 2024-01-XX

### Added
- Initial release of PDF Layout Analysis Engine
- Multi-column layout detection
- Figure and table extraction
- Text block analysis and grouping
- Caption linking functionality
- Command-line interface
- Python API for integration
- Support for both ruled and borderless tables
- Vector graphics and image object detection
- Reading order determination
- Batch processing capabilities

### Features
- **Column Detection**: Automatic multi-column layout recognition using whitespace analysis
- **Figure Extraction**: Vector clustering and image XObject detection
- **Table Recognition**: Hough line transform for ruled tables, cell density analysis for borderless tables
- **Text Processing**: Connected component analysis with hierarchical grouping
- **Debug Mode**: Visual overlay generation for layout analysis
- **Error Handling**: Robust processing of various PDF formats and edge cases

### Technical Details
- Built with PyMuPDF for PDF processing
- Uses OpenCV for computer vision operations
- Implements DBSCAN clustering for vector graphics
- Applies Hough transform for line detection
- Uses projection profile analysis for column detection
- Supports Python 3.8+ with comprehensive type hints

---

## Version History

### v1.0.0 (Initial Release)
- Core layout analysis functionality
- Figure and table detection
- Multi-column processing
- Command-line interface
- Python API

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
