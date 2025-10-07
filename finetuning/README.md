# PDF Extraction Finetuning System

This folder contains the finetuning system for improving PDF table and figure detection accuracy.

## Folder Structure

```
finetuning/
├── data/                    # Training data
│   ├── raw/                # Raw extracted data
│   ├── processed/          # Processed training data
│   └── validation/         # Validation data
├── models/                 # Saved models
├── scripts/                # Finetuning scripts
├── utils/                  # Utility functions
└── results/                # Results and logs
```

## Quick Start

1. Run `python scripts/extract_annotations.py` to extract annotations from your PDFs
2. Run `python scripts/train_model.py` to finetune the model
3. Run `python scripts/test_model.py` to test improvements

## Color Legend

- 🔴 RED = Tables
- 🟢 GREEN = Figures/Technical Drawings
- 🔵 BLUE = Text Blocks
