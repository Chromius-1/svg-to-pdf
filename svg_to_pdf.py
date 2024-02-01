import os
import re
import argparse
import multiprocessing as mp
from contextlib import redirect_stderr
from multiprocessing.managers import ListProxy
from io import BytesIO
from zipfile import ZipFile, is_zipfile
import _queue

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

from PyPDF2 import PdfMerger

BLANK_PDF_PAGE = b'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 595.276 841.890]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
186
%%EOF'''

def convert_svg_to_pdf(svg_queue: mp.Queue, output_list: ListProxy, number_of_pages: int) -> None:
    """Converts SVG data to PDF format and adds the results to the output list while there are tasks in the queue.

    Args:
        svg_queue (mp.Queue): A queue containing tuples (page_number, svg_data).
        output_list (Manager.ListProxy): A list to store the results as tuples (page_number, pdf_content).
        number_of_pages (int): The total number of SVG files being processed.

    Returns:
        None

    Raises:
        Exception: If an error occurs during the conversion of SVG to PDF, a task with an empty pdf_content will be added to the resulting list.
        _queue.Empty: Queue.get_nowait() sometimes throws an Empty exception. Read more this https://mail.python.org/pipermail/python-list/2002-July/150826.html
        All exceptions of the Empty type are hidden.
    """
    while svg_queue.qsize() > 0:
        progress = f"Progress: {number_of_pages - svg_queue.qsize()}/{number_of_pages}"
        print(progress, end='\r')
    
        try:
            page_number, svg_data = svg_queue.get_nowait()
        except _queue.Empty:
            continue

        try:
            with redirect_stderr(None): #This context hides non-critical errors of svglib transformations
                drawing = svg2rlg(BytesIO(svg_data))
            pdf_content = renderPDF.drawToString(drawing)
        except Exception as e:
            print(f"Error converting SVG to PDF: {e}")
            pdf_content = BLANK_PDF_PAGE
        output_list.append((page_number, pdf_content))
        print(" " * len(progress), end='\r')


def process_files(path_to_files:str, svg_queue: mp.Queue, pattern: str = None) -> (str, int):
    """
    Reads SVG files in a directory or zip archive into RAM.

    This function takes the path to a directory or a zip archive containing SVG files,
    reads the contents of each SVG file into memory, and adds the file data along with
    its corresponding page number to a multiprocessing mp.Queue.

    Args:
        path_to_files (str): The path to the directory or zip archive containing SVG files.
        svg_queue (mp.Queue): A multiprocessing mp.Queue used to store tuples
            containing page number and SVG file data.
        pattern (str, optional): Regular expression pattern to extract page numbers from file names.
            Defaults to r'\\d+'.

    Raises:
        TypeError: Raised if the provided path is neither a directory nor a zip archive.

    Returns:
        tuple: pdf filename and the total number of SVG files processed
    """
    if not pattern:
        pattern = r'\d+'

    pattern = re.compile(pattern)

    def page_number(file_name:str, pattern: str) -> int:
        """
        Extracts the page number from the file name using a regular expression pattern. The last match with the regular expression in the file name string is returned

        Args:
            file_name (str): The name of the SVG file.
            pattern (str): A regular expression template for extracting page numbers.    

        Returns:
        int or str: The number of the extracted page.
        """
        try:
            page_number = int(re.findall(pattern, file_name)[-1])
        except IndexError as e:
            page_number = 0
            print(f"Could not determine sequence number for file {file_name} with pattern {pattern.pattern}. The page will be placed at index 0 :")
        return page_number

    if os.path.isdir(path_to_files):
        pdf_file_name = os.path.basename(path_to_files) + '.pdf'
        for root, dirs, files in os.walk(path_to_files):
            for file in files:
                if file.endswith(".svg"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'rb') as svg_file:
                        svg_data = svg_file.read()
                        svg_queue.put((page_number(file, pattern), svg_data))

    elif is_zipfile(path_to_files):
        pdf_file_name = os.path.splitext(os.path.basename(path_to_files))[0] + '.pdf'
        with ZipFile(path_to_files, 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file.lower().endswith(".svg"):
                    svg_queue.put((page_number(file, pattern), zip_ref.read(file)))
    else:
        raise TypeError("Directory or zip file is required.")
    number_of_svg_files = svg_queue.qsize()
    return (pdf_file_name, number_of_svg_files)


def write_pdf(output_list, file_name='svg_to_pdf.pdf'):
    """
    Combines a list of SVG data into a single PDF file.

    This function takes a list of tuples containing page numbers and corresponding SVG data,
    sorts them by page number, and merges the SVG data into a single PDF file using PyPDF2.

    Args:
        output_list (list): List of tuples containing page number and SVG data.
        file_name (str, optional): Name of the output PDF file. Defaults to 'svg_to_pdf.pdf'.

    Returns:
        None
    """
    if output_list:
        error_page = []
        output_list.sort()
        merger = PdfMerger()
        for i, pdf in output_list:
            try:
                merger.append(BytesIO(pdf))
                if pdf == BLANK_PDF_PAGE:
                    error_page.append(i)
            except Exception as e:
                print(f'Error PDF Merger in page {i}:{e}')
                error_page.append(i)
        merger.write(file_name)
        merger.close()

        if error_page:
            print(f"File {file_name} was created with errors. Processed {len(output_list)} svg files pages. Of these, {len(error_page)} pages with numbers {error_page} have been replaced with blank A4 pages")
        else:
            print(f"File {file_name} was created successfully. Processed {len(output_list)} svg files")


def main(path_to_svg:str = None, pattern_page_number: str = None):
    """
    Main function to convert SVG files in a zip archive or directory to a single PDF file.

    Args:
        path_to_svg (str): Path to the directory or zip archive containing SVG files.
        pattern_page_number (str, optional): Regular expression pattern to extract page numbers from file names.
            Defaults to r'\\d+'.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description='Convert SVG files in a zip archive or directory to a single PDF file.')
    parser.add_argument('path_to_svg', help='Path to the directory or zip archive containing SVG files.')
    parser.add_argument('--pattern', default=r'\d+', help='Regular expression pattern to extract page numbers from file names. By default, the last group of digits in the file name "\\d+"')
    args = parser.parse_args()

    if not path_to_svg:
        path_to_svg = args.path_to_svg
    if not pattern_page_number:
        pattern_page_number = args.pattern

    mp_manager = mp.Manager()
    svg_queue = mp.Queue()
    output_list = mp_manager.list()

    pdf_file_name, number_of_svg_files = process_files(path_to_svg, svg_queue, pattern_page_number)

    processes = []
    number_of_CPUs = mp.cpu_count()
    for _ in range(number_of_CPUs):
        p = mp.Process(target=convert_svg_to_pdf, args=(svg_queue, output_list,number_of_svg_files))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    write_pdf(output_list, pdf_file_name)

if __name__ == "__main__":
    main()