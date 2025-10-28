# -*- coding: utf-8 -*-
# PreProcessing module for document parsing and information extraction

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from core.data_table import List_Student_HCD_Label
from core.model_config import DEFAULT_MODEL
from core.prompt import DATA_EXTRACTION_SYS_PROMPT

load_dotenv()


class PreProcessor:
    """A Preprocessor that parses documents and extract information"""

    def __init__(self) -> None:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=4, device=AcceleratorDevice.AUTO
        )
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        self.doc_converter = doc_converter
        model = init_chat_model(DEFAULT_MODEL)
        self.model_with_structure = model.with_structured_output(List_Student_HCD_Label)

    def _parse(self, file_path: str) -> str:
        """Parse a document and return its markdown text

        Args:
            file_path (str): file path or URL to the document

        Returns:
            str: The extracted markdown text from the document
        """
        result = self.doc_converter.convert(file_path)
        return result.document.export_to_markdown()

    def _extract_table_data(self, text: str) -> List_Student_HCD_Label:
        """Extract table data from the given text using LLM

        Args:
            text (str): The input text containing the progress report
        Returns:
            List_Student_HCD_Label: The extracted table data
        """
        response = self.model_with_structure.invoke(
            [
                {"role": "system", "content": DATA_EXTRACTION_SYS_PROMPT},
                {
                    "role": "user",
                    "content": f"Extract the table data from the following progress report:\n\n{text}",
                },
            ]
        )
        return response

    def invoke(self, file_path: str) -> List_Student_HCD_Label:
        """Process a document and extract table data

        Args:
            file_path (str): file path or URL to the document

        Returns:
            List_Student_HCD_Label: The extracted table data
        """
        markdown_text = self._parse(file_path)
        table_data = self._extract_table_data(markdown_text)
        return table_data

    def display_list_data_table(self, list_data_table: List_Student_HCD_Label) -> None:
        """Display the extracted List_Student_HCD_Label in a readable format.

        Args:
            list_data_table (List_Student_HCD_Label): The extracted table data to display.
        """
        for idx, data_table in enumerate(list_data_table.tables):
            print(f"Entry {idx + 1}:")
            print(f"  Activity: {data_table.activity}")
            print(f"  HCD Spaces: {', '.join(data_table.HCD_Spaces)}")
            print(f"  HCD Subspaces: {', '.join(data_table.HCD_Subspaces)}")
            print("-" * 40)


if __name__ == "__main__":
    # Example usage
    pre_processor = PreProcessor()
    res = pre_processor.invoke(
        os.path.join(
            os.path.dirname(__file__),
            "../data/progress_report_example_1.pdf",
        )
    )

    pre_processor.display_list_data_table(res)
