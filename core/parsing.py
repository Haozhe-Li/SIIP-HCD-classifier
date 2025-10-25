# -*- coding: utf-8 -*-
# Parsing Module with Docling
# Haozhe Li


import json

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


class Parser:
    """A Document Parser based on Docling"""

    def __init__(self) -> None:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.ocr_options.lang = ["es"]
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=4, device=AcceleratorDevice.AUTO
        )
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        self.doc_converter = doc_converter

    def parse(self, file_path: str) -> str:
        """Parse a document and return its markdown text

        Args:
            file_path (str): file path or URL to the document

        Returns:
            str: The extracted markdown text from the document
        """
        result = self.doc_converter.convert(file_path)
        return result.document.export_to_markdown()


# Example usage
if __name__ == "__main__":
    parser = Parser()
    url = "https://arxiv.org/pdf/2408.09869"
    res = parser.parse(url)
    print(res)
