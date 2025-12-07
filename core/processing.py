# -*- coding: utf-8 -*-
"""Processing utilities built on top of the PreProcessor outputs."""

from __future__ import annotations

import asyncio
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
        """
        Initialize the Processing helper.

        Sets up the chat model using the default configuration and binds it to a structured output schema
        (`LLM_HCD_Label`) for consistent activity classification results.
        """
        self._model = init_chat_model(DEFAULT_MODEL)
        self.bound_model = self._model.with_structured_output(LLM_HCD_Label)

    @staticmethod
    def _build_activity_prompt(activity: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": ACTIVITY_EVAL_SYS_PROMPT},
            {
                "role": "user",
                "content": (
                    "Classify the following activity according to the HCD rubric:\n\n"
                    f"{activity}"
                ),
            },
        ]

    def classify_activity(self, activity: str) -> LLM_HCD_Label:
        """Classify a single activity description using the configured LLM."""
        response = self.bound_model.invoke(self._build_activity_prompt(activity))
        return response

    async def aclassify_activity(self, activity: str) -> LLM_HCD_Label:
        """Async variant of :py:meth:`classify_activity`."""
        return await self.bound_model.ainvoke(self._build_activity_prompt(activity))

    def display_list_data_table(self, table_data: list[LLM_HCD_Label]) -> None:
        """Display the extracted List_Student_HCD_Label in a readable format.

        Args:
            table_data (list[LLM_HCD_Label]): The extracted table data to display.
        """
        for idx, data_table in enumerate(table_data):
            print(f"Entry {idx + 1}:")
            print(f"  Activity: {data_table.activity}")
            print(f"  HCD Spaces: {', '.join(data_table.HCD_Spaces)}")
            print(f"  HCD Subspaces: {', '.join(data_table.HCD_Subspaces)}")
            print("-" * 40)

    def classify_table(self, table_data: List_Student_HCD_Label) -> list[LLM_HCD_Label]:
        """
        Classify each activity entry produced by the preprocessing stage.

        Args:
            table_data (List_Student_HCD_Label): The structured table data containing student activities to classify.

        Returns:
            list[LLM_HCD_Label]: A list of classification results for each activity entry.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.aclassify_table(table_data))

        # Fallback to sequential classification if already inside an event loop.
        return [self.classify_activity(entry.activity) for entry in table_data.tables]

    async def aclassify_table(
        self, table_data: List_Student_HCD_Label, max_concurrency: int = 4
    ) -> list[LLM_HCD_Label]:
        sem = asyncio.Semaphore(max_concurrency)

        async def classify(entry_activity: str) -> LLM_HCD_Label:
            async with sem:
                return await self.aclassify_activity(entry_activity)

        tasks = [classify(entry.activity) for entry in table_data.tables]
        return await asyncio.gather(*tasks)


if __name__ == "__main__":
    from core.preprocessing import PreProcessor

    processor = Processing()
    preprocessor = PreProcessor()
    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "../data/progress_report_1.pdf",
    )

    extracted_table = preprocessor.invoke(pdf_path)

    print("\nLLM classification results:")
    llm_labels = processor.classify_table(extracted_table)
    processor.display_list_data_table(llm_labels)
