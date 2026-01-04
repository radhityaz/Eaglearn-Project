# Repository Metrics Summary

## Overview

This document provides a structured summary of the repository's codebase metrics, focusing on static analysis and dependency surface. The metrics are collected to support reliability, maintainability, and API contract drift audits.

## Key Statistics

- **Total Files**: 11,030
- **Total Code Files**: 8,684
- **Total Size**: 729,472,912 bytes (729 MB)
- **Approximate Total LOC**: 5,105,474

## Per Directory Breakdown

| Directory | Files | Code Files | Size (bytes) | Approx LOC |
|-----------|-------|------------|--------------|------------|
| backend | 1 | 1 | 7,127 | 194 |
| frontend | 10,964 | 8,649 | 729,137,292 | 5,098,786 |
| prototypes | 21 | 8 | 73,649 | 1,409 |
| eaglearn-clone | 19 | 6 | 23,635 | 502 |
| copy/focus-coach | 12 | 7 | 47,815 | 828 |
| spec | 12 | 12 | 172,961 | 3,635 |
| docs | 0 | 0 | 0 | 0 |
| tests | 0 | 0 | 0 | 0 |
| benchmarks | 0 | 0 | 0 | 0 |
| models | 0 | 0 | 0 | 0 |
| proto | 1 | 1 | 10,433 | 120 |

## Extension Histogram

The following table shows the distribution of code files by extension:

| Extension | File Count | Approx LOC |
|-----------|------------|------------|
| .md | 689 | 80,510 |
| .html | 9 | 272,193 |
| .js | 5,575 | 839,450 |
| .ts | 1,583 | 227,967 |
| .json | 797 | 101,788 |
| .css | 9 | 2,501 |
| .py | 22 | 6,718 |

## Limitations and Assumptions

1. **Binary File Filtering**: The following file types were excluded from the analysis:
   - PDF files (`*.pdf`)
   - SVG icons in specific directories (`eaglearn-clone/assets/icons/`, `prototypes/figma-export/icons/`)
   - Image files (`*.png`, `*.jpg`, `*.jpeg`, `*.gif`) in screenshots directory
   - Other binary files (`*.zip`, `*.mp4`, `*.mov`, `*.webm`, `*.wav`)

2. **LOC Estimation**: Lines of code estimation is based on counting non-empty lines in text files. This is a rough approximation and doesn't account for comments, blank lines, or complexity.

3. **Directory Coverage**: The analysis covers all main directories mentioned in the CODEMAP: backend/, frontend/, prototypes/, eaglearn-clone/, copy/focus-coach/, spec/, docs/, tests/, benchmarks/, models/, proto/.

4. **Code Extensions**: Only common code file extensions were considered (.py, .js, .ts, .jsx, .tsx, .css, .html, .md, .json).

## Methodology

The metrics were collected through a Python script (`tools/repo_metrics.py`) that recursively explores the repository structure, applies exclusion filters, and calculates file counts, sizes, and approximate LOC using line counting techniques.