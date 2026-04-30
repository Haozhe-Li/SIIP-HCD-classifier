# -*- coding: utf-8 -*-
"""Processing utilities built on top of the PreProcessor outputs (Few-Shot Version)."""

from __future__ import annotations

import asyncio
import os
import sys
import csv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.chat_models import init_chat_model

from core.data_table import List_Student_HCD_Label, LLM_HCD_Label
from core.model_config import DEFAULT_MODEL
from core.prompt import ACTIVITY_EVAL_SYS_PROMPT
from core.utils import KNOWN_SPACES, KNOWN_SUBSPACES, normalize_list


def load_few_shot_examples() -> str:
    """Loads one example per subspace from the exported CSV."""
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "all_annotated_data.csv",
    )
    examples_by_subspace = {}

    if not os.path.exists(csv_path):
        print(f"Warning: Few-shot CSV not found at {csv_path}")
        return ""

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_spaces = row.get("HCD_Space", "")
            raw_subspaces = row.get("HCD_Subspace", "")

            spaces = [
                x.strip()
                for x in raw_spaces.replace(" and ", ",").replace(" & ", ",").split(",")
                if x.strip()
            ]
            subspaces = [
                x.strip()
                for x in raw_subspaces.replace(" and ", ",")
                .replace(" & ", ",")
                .split(",")
                if x.strip()
            ]

            # Select unambiguous examples with 1 space and 1 subspace
            if len(spaces) == 1 and len(subspaces) == 1:
                space = spaces[0].lower()
                subspace = subspaces[0].lower()

                # Filter out unknown labels and only take the first good example for each subspace
                if (
                    space != "unknown"
                    and subspace != "unknown"
                    and subspace not in examples_by_subspace
                ):
                    examples_by_subspace[subspace] = row

    if not examples_by_subspace:
        return ""

    example_str = "\n\n## Few-Shot Examples\nHere are some high-quality examples of correct classifications to guide your labeling:\n\n"
    for sub, row in examples_by_subspace.items():
        activity = row["Activity"]
        space = row["HCD_Space"]
        reason = row["Reason"]

        example_str += f'**Activity**: "{activity}"\n'
        example_str += f'**Classification**:\n- HCD_Spaces: ["{space.lower()}"]\n- HCD_Subspaces: ["{sub}"]\n'
        if reason:
            example_str += f"**Reasoning**: {reason}\n"
        example_str += "---\n"

    return example_str


class ProcessingFewShot:
    """Post-processing helpers for activity evaluation using few-shot classification."""

    def __init__(self) -> None:
        """
        Initialize the Processing helper.

        Sets up the chat model using the default configuration and binds it to a structured output schema
        (`LLM_HCD_Label`) for consistent activity classification results. Also loads few-shot examples.
        """
        self._model = DEFAULT_MODEL
        self.bound_model = self._model.with_structured_output(LLM_HCD_Label)
        self.few_shot_examples = load_few_shot_examples()

    def _build_activity_prompt(self, activity: str) -> list[dict[str, str]]:
        system_prompt = ACTIVITY_EVAL_SYS_PROMPT + self.few_shot_examples
        return [
            {"role": "system", "content": system_prompt},
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
        # normalize model outputs
        response.HCD_Spaces = normalize_list(response.HCD_Spaces, KNOWN_SPACES)
        response.HCD_Subspaces = normalize_list(response.HCD_Subspaces, KNOWN_SUBSPACES)
        return response

    async def aclassify_activity(self, activity: str) -> LLM_HCD_Label:
        """Async variant of :py:meth:`classify_activity`."""
        resp = await self.bound_model.ainvoke(self._build_activity_prompt(activity))
        resp.HCD_Spaces = normalize_list(resp.HCD_Spaces, KNOWN_SPACES)
        resp.HCD_Subspaces = normalize_list(resp.HCD_Subspaces, KNOWN_SUBSPACES)
        return resp

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

    processor = ProcessingFewShot()
    preprocessor = PreProcessor()
    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "../data/progress_report_1.pdf",
    )

    extracted_table = preprocessor.invoke(pdf_path)

    print("\nLLM classification results (Few-Shot):")
    llm_labels = processor.classify_table(extracted_table)
    processor.display_list_data_table(llm_labels)
