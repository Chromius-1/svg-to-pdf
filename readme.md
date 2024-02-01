# SVG to PDF Converter

This Python utility converts SVG files in a zip archive or directory into a single PDF file. It uses multiprocessing to parallelize the conversion process.
Before processing, the files are completely written to memory and only then converted to pdf.

## Features

- Converts SVG files to a single PDF file.
- Supports processing SVG files in a zip archive or directory.
- Utilizes multiprocessing for parallel conversion.
- Provides options for customizing the page number extraction using regular expressions.

## Prerequisites

- Python 3.6 or higher

## Dependencies:
   - svglib
   - reportlab
   - PyPDF2

## Conversion Process
1. **Input Files**: The utility reads SVG files from the specified directory or zip archive.

2. **Multiprocessing**: The converter uses multiple processes to parallelize the conversion of SVG files to PDF. Each process handles a subset of the files.

3. **SVG to PDF**: Each SVG file is converted to PDF using the svglib and reportlab libraries.

4. **Output PDF**: The resulting PDF files are merged into a single PDF file using the PyPDF2 library.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/chromius-1/svg-to-pdf.git
    ```

2. Change into the project directory:

    ```bash
    cd svg-to-pdf-converter
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the converter with the following command:

```bash
python svg_to_pdf_converter.py path/to/svg/files/in/zip/or/directory --pattern "\d+"
```
The `--pattern` parameter is designed to specify a regular expression for extracting the page number from the names of SVG files.