# -*- coding: utf-8 -*-
"""Processing utilities built on top of the PreProcessor outputs."""

from __future__ import annotations

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.chat_models import init_chat_model

from core.data_table import List_Student_HCD_Label, LLM_HCD_Label
from core.model_config import DEFAULT_MODEL
from core.prompt import ACTIVITY_EVAL_SYS_PROMPT


class Processing:
    """Post-processing helpers for activity evaluation."""

    def __init__(self) -> None:
        self._model = init_chat_model(DEFAULT_MODEL)
        self.bound_model = self._model.with_structured_output(LLM_HCD_Label)


    def classify_activity(self, activity: str) -> LLM_HCD_Label:
        """Classify a single activity description using the configured LLM."""
        response = self.bound_model.invoke(
            [
                {"role": "system", "content": ACTIVITY_EVAL_SYS_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Classify the following activity and explain your reasoning:\n\n"
                        f"{activity}"
                    ),
                },
            ]
        )
        return response

    def classify_table(
        self, table_data: List_Student_HCD_Label
    ) -> list[LLM_HCD_Label]:
        """Classify each activity entry produced by the preprocessing stage."""

        return [self.classify_activity(entry.activity) for entry in table_data.tables]


if __name__ == "__main__":
    from core.preprocessing import PreProcessor

    processor = Processing()
    preprocessor = PreProcessor()
    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "../data/progress_report_example_1.pdf",
    )

    extracted_table = preprocessor.invoke(pdf_path)

    print("\nLLM classification results:")
    llm_labels = processor.classify_table(extracted_table)
    print(llm_labels)
