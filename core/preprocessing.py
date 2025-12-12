# -*- coding: utf-8 -*-
# PreProcessing module for document parsing and information extraction

import os
import sys

import fitz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from core.data_table import List_Student_HCD_Label
from core.utils import (
    KNOWN_SPACES,
    KNOWN_SUBSPACES,
    get_logger,
    normalize_list,
    timed,
)
from core.model_config import DEFAULT_MODEL
from core.prompt import DATA_EXTRACTION_SYS_PROMPT

load_dotenv()


class PreProcessor:
    """A Preprocessor that parses documents and extract information"""

    def __init__(self) -> None:
        model = init_chat_model(DEFAULT_MODEL)
        self.model_with_structure = model.with_structured_output(List_Student_HCD_Label)
        self._logger = get_logger(self.__class__.__name__)

    def _parse(self, file_path: str) -> str:
        """Parse a document and return its markdown text

        Args:
            file_path (str): file path or URL to the document

        Returns:
            str: The extracted markdown text from the document
        """
        with timed("preprocessing.parse_pdf"):
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            try:
                with fitz.open(file_path) as document:
                    pages_markdown = []
                    for page in document:
                        try:
                            markdown_text = page.get_text("markdown").strip()
                        except (AssertionError, RuntimeError, ValueError):
                            markdown_text = ""

                        if not markdown_text:
                            markdown_text = page.get_text().strip()

                        pages_markdown.append(markdown_text)
            except (AssertionError, RuntimeError, ValueError) as exc:
                raise ValueError(f"Failed to parse PDF: {file_path}") from exc

            return "\n\n".join(pages_markdown)

    def _extract_table_data(self, text: str) -> List_Student_HCD_Label:
        """Extract table data from the given text using LLM

        Args:
            text (str): The input text containing the progress report
        Returns:
            List_Student_HCD_Label: The extracted table data
        """
        with timed("preprocessing.llm_extract_table"):
            response = self.model_with_structure.invoke(
                [
                    {"role": "system", "content": DATA_EXTRACTION_SYS_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Extract the table data from the following progress report:\n\n"
                            f"{text}"
                        ),
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
        with timed("preprocessing.invoke"):
            markdown_text = self._parse(file_path)
            table_data = self._extract_table_data(markdown_text)
            with timed("preprocessing.normalize_labels"):
                # normalize spaces and subspaces to lowercase and fix typos
                for entry in table_data.tables:
                    entry.HCD_Spaces = normalize_list(entry.HCD_Spaces, KNOWN_SPACES)
                    entry.HCD_Subspaces = normalize_list(
                        entry.HCD_Subspaces, KNOWN_SUBSPACES
                    )
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
            "../data/progress_report_1.pdf",
        )
    )

    pre_processor.display_list_data_table(res)
