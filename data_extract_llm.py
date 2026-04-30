from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Iterable

import fitz
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from core.model_config import PARSING_MODEL
from database.insert_data import insert_activities

load_dotenv()


ACTIVITY_EXTRACTION_SYS_PROMPT = """
You are a precise data extraction assistant.

Task:
- Extract only the activity items from a single program report page.
- Activity items correspond to lines such as "Activity 1", "Activity 2", "Activity 3", etc.
- Return clean activity texts only (no numbering, no prefixes like "Activity 1:").

Rules:
- If the page has no activity section/items, return an empty list.
- Do not infer or hallucinate activities.
- Preserve wording from the page text as much as possible.
- Ignore all non-activity sections.
"""


# Utility: Parse engineering_weekly_activities_expanded.txt and insert all activities into D1
def insert_txt_activities_to_db(txt_path: str) -> dict[str, int | str]:
    """
    Parse a txt file with numbered activities and insert all into D1 database.
    Each line is treated as one activity.
    """
    from database.insert_data import insert_activities
    import re
    import os

    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"File not found: {txt_path}")

    activities = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Remove leading number and dot
            activity = re.sub(r"^\d+\.\s*", "", line)
            if activity:
                activities.append(activity)

    inserted_count = insert_activities(activities)
    return {
        "input_file": txt_path,
        "parsed_activities": len(activities),
        "inserted_activities": inserted_count,
    }


class ProgramReportActivities(BaseModel):
    activities: list[str] = Field(
        default_factory=list,
        description="List of activities extracted from one program report page.",
    )


class ProgramReportPageActivities(BaseModel):
    page: int = Field(..., description="1-based PDF page number")
    activities: list[str] = Field(
        default_factory=list,
        description="Clean activity list for this page",
    )


def _extract_page_text(page: fitz.Page) -> str:
    try:
        markdown_text = page.get_text("markdown").strip()
    except (AssertionError, RuntimeError, ValueError):
        markdown_text = ""

    if markdown_text:
        return markdown_text
    return page.get_text().strip()


def _normalize_activity(activity: str) -> str:
    return " ".join(activity.split()).strip()


def _extract_activities_from_single_page(extraction_model, page_text: str) -> list[str]:
    if not page_text:
        return []

    extracted = extraction_model.invoke(
        [
            {"role": "system", "content": ACTIVITY_EXTRACTION_SYS_PROMPT},
            {
                "role": "user",
                "content": (
                    "Extract activities from this single program report page. "
                    "Return only structured activities.\n\n"
                    f"Page Text:\n{page_text}"
                ),
            },
        ]
    )

    return [
        normalized
        for normalized in (_normalize_activity(item) for item in extracted.activities)
        if normalized
    ]


def extract_activities_from_pdf(
    pdf_path: str, max_pages: int | None = None
) -> list[ProgramReportPageActivities]:
    model = PARSING_MODEL
    extraction_model = model.with_structured_output(ProgramReportActivities)

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    page_results: list[ProgramReportPageActivities] = []

    with fitz.open(pdf_path) as document:
        total_pages = len(document)
        pages_to_process = (
            total_pages if max_pages is None else min(max_pages, total_pages)
        )

        for page_index, page in enumerate(document, start=1):
            if page_index > pages_to_process:
                break

            page_text = _extract_page_text(page)
            cleaned = _extract_activities_from_single_page(extraction_model, page_text)

            page_results.append(
                ProgramReportPageActivities(page=page_index, activities=cleaned)
            )

    return page_results


def save_activities_to_jsonl(
    page_results: list[ProgramReportPageActivities], output_file: str
) -> int:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with output_path.open("w", encoding="utf-8") as file:
        for result in page_results:
            file.write(
                json.dumps(
                    {"page": result.page, "activities": result.activities},
                    ensure_ascii=False,
                )
                + "\n"
            )
            total += len(result.activities)

    return total


def extract_activities_to_jsonl_incremental(
    pdf_path: str,
    output_file: str,
    max_pages: int | None = None,
    sleep_seconds: float = 5.0,
) -> dict[str, int | str]:
    """
    Extract activities page-by-page and write each page result immediately to JSONL.

    This is resilient to interruptions: completed pages stay in the output file.
    """
    if max_pages is not None and max_pages <= 0:
        raise ValueError("--max-pages must be a positive integer")
    if sleep_seconds < 0:
        raise ValueError("sleep_seconds must be >= 0")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    model = PARSING_MODEL
    extraction_model = model.with_structured_output(ProgramReportActivities)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pages_processed = 0
    total_activities = 0

    with fitz.open(pdf_path) as document:
        total_pages = len(document)
        pages_to_process = (
            total_pages if max_pages is None else min(max_pages, total_pages)
        )

        with output_path.open("w", encoding="utf-8") as file:
            for page_index, page in enumerate(document, start=1):
                if page_index > pages_to_process:
                    break

                page_text = _extract_page_text(page)
                cleaned = _extract_activities_from_single_page(
                    extraction_model, page_text
                )

                file.write(
                    json.dumps(
                        {"page": page_index, "activities": cleaned},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                file.flush()

                pages_processed += 1
                total_activities += len(cleaned)

                if sleep_seconds > 0:
                    print(
                        f"Processed page {page_index}/{pages_to_process} with {len(cleaned)} activities. Sleeping for {sleep_seconds} seconds..."
                    )
                    time.sleep(sleep_seconds)

    return {
        "output_file": output_file,
        "pages_processed": pages_processed,
        "total_activities": total_activities,
    }


def flatten_non_empty_activities(
    page_results: list[ProgramReportPageActivities],
) -> list[str]:
    activities: list[str] = []
    for result in page_results:
        for activity in result.activities:
            normalized = _normalize_activity(activity)
            if normalized:
                activities.append(normalized)
    return activities


def load_activities_from_jsonl(jsonl_path: str) -> list[str]:
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"File not found: {jsonl_path}")

    activities: list[str] = []
    with Path(jsonl_path).open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue

            try:
                data = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            raw_activities = data.get("activities", [])
            if not isinstance(raw_activities, Iterable) or isinstance(
                raw_activities, (str, bytes)
            ):
                continue

            for item in raw_activities:
                if not isinstance(item, str):
                    continue
                normalized = _normalize_activity(item)
                if normalized:
                    activities.append(normalized)

    return activities


def run_extract_pipeline(
    pdf_path: str,
    output_file: str,
    max_pages: int | None = None,
    sleep_seconds: float = 5.0,
) -> dict[str, int | str]:
    return extract_activities_to_jsonl_incremental(
        pdf_path=pdf_path,
        output_file=output_file,
        max_pages=max_pages,
        sleep_seconds=sleep_seconds,
    )


def run_insert_pipeline(input_file: str) -> dict[str, int | str]:
    all_activities = load_activities_from_jsonl(input_file)
    inserted_count = insert_activities(all_activities)
    return {
        "input_file": input_file,
        "loaded_activities": len(all_activities),
        "inserted_activities": inserted_count,
    }


def run_activity_pipeline(
    mode: str,
    *,
    pdf_path: str | None = None,
    output_file: str = "data/extracted_activities.jsonl",
    input_file: str = "data/extracted_activities.jsonl",
    max_pages: int | None = None,
    sleep_seconds: float = 5.0,
) -> dict[str, int | str]:
    """
    Unified function-based entry for manual parameter control.

    Args:
        mode: Either "extract" or "insert".
        pdf_path: Required when mode is "extract".
        output_file: Output JSONL path for extraction results.
        input_file: Input JSONL path for DB insertion.
        max_pages: Optional limit for extraction pages.
        sleep_seconds: Delay between pages to reduce rate-limit risk.

    Returns:
        dict with pipeline summary metrics.
    """
    normalized_mode = mode.strip().lower()

    if normalized_mode == "extract":
        if not pdf_path:
            raise ValueError("pdf_path is required when mode='extract'")
        return run_extract_pipeline(
            pdf_path=pdf_path,
            output_file=output_file,
            max_pages=max_pages,
            sleep_seconds=sleep_seconds,
        )

    if normalized_mode == "insert":
        return run_insert_pipeline(input_file=input_file)

    raise ValueError("mode must be 'extract' or 'insert'")


# Example:
# extract_result = run_activity_pipeline(
#     "extract",
#     pdf_path="data/MSE_494_100_Weekly_Progress_Reports_AI_Training.pdf",
#     output_file="data/extracted_activities.jsonl",
#     sleep_seconds=1,
# )
#
# insert_result = run_activity_pipeline(
#     "insert",
#     input_file="data/extracted_activities.jsonl",
# )


if __name__ == "__main__":
    insert_txt_activities_to_db("data/engineering_weekly_activities_expanded.txt")
