from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from core.data_table import LLM_HCD_Label, List_Output_Label, List_Student_HCD_Label
from core.postprocessing import FinalProcessing
from core.preprocessing import PreProcessor
from core.processing import Processing
from database.db import (
    fetch_unlabeld_activity,
    label_activity,
    get_activity_annotations,
)
from dotenv import load_dotenv

load_dotenv()


class ClassificationResponse(BaseModel):
    student_labels: List_Student_HCD_Label
    llm_labels: list[LLM_HCD_Label]
    final_labels: List_Output_Label


class RootResponse(BaseModel):
    message: str
    endpoints: dict[str, str]


class UnlabeledActivityResponse(BaseModel):
    rowid: int | None
    Activity: str | None


class LabelActivityRequest(BaseModel):
    rowid: int
    HCD_Space: str
    HCD_Subspace: str
    Reason: str
    Annotator: str


class LabelActivityResponse(BaseModel):
    success: bool
    message: str
    inserted_new: bool = False


class ActivityAnnotation(BaseModel):
    rowid: int
    Activity: str
    HCD_Space: str
    HCD_Subspace: str
    Reason: str
    Annotator: str


class ActivityGroup(BaseModel):
    activity: str
    count: int
    annotations: list[ActivityAnnotation]


class ActivityAnnotationsResponse(BaseModel):
    total_activities: int
    groups: list[ActivityGroup]


app = FastAPI(title="SIIP HCD Classifier API", version="0.1.0")

preprocessor = PreProcessor()
processor = Processing()
final_processor = FinalProcessing()


def _validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    content_type = (file.content_type or "").lower()
    if not content_type:
        content_type = (
            "application/pdf" if file.filename.lower().endswith(".pdf") else ""
        )

    if content_type not in {
        "application/pdf",
        "application/octet-stream",
    } and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")


async def _persist_upload(file: UploadFile) -> Path:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    suffix = Path(file.filename or "uploaded.pdf").suffix or ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        path = Path(tmp.name)
        tmp.write(contents)

    await file.close()
    return path


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse(
        message="SIIP HCD Classifier API",
        endpoints={
            "health": "/health",
            "classify": "/classify",
            "fetch-unlabeled": "/fetch-unlabeled",
            "label-activity": "/label-activity",
            "activity-annotations": "/activity-annotations",
            "docs": "/docs",
        },
    )


@app.post("/classify", response_model=ClassificationResponse)
async def classify_pdf(file: UploadFile = File(...)) -> ClassificationResponse:
    _validate_upload(file)
    temp_path: Path | None = None

    try:
        temp_path = await _persist_upload(file)
        student_labels = await asyncio.to_thread(
            preprocessor.invoke, temp_path.as_posix()
        )
        llm_labels = await processor.aclassify_table(student_labels)
        final_labels = await final_processor.afinal_eval(student_labels, llm_labels)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temp_path is not None:
            try:
                os.remove(temp_path)
            except FileNotFoundError:
                pass

    return ClassificationResponse(
        student_labels=student_labels,
        llm_labels=llm_labels,
        final_labels=final_labels,
    )


@app.get("/fetch-unlabeled", response_model=UnlabeledActivityResponse)
async def fetch_unlabeled() -> UnlabeledActivityResponse:
    """Fetch one unlabeled activity from the database."""
    activity = await fetch_unlabeld_activity()

    if activity is None:
        return UnlabeledActivityResponse(rowid=None, Activity=None)

    return UnlabeledActivityResponse(
        rowid=activity.get("rowid"), Activity=activity.get("Activity")
    )


@app.post("/label-activity", response_model=LabelActivityResponse)
async def label_activity_endpoint(
    request: LabelActivityRequest,
) -> LabelActivityResponse:
    """
    Label an activity with HCD classification.

    If the target row was already labeled by another annotator, a new duplicate
    row is automatically inserted so both annotations are preserved.
    The response field `inserted_new` will be True in that case.
    """
    result = await label_activity(
        activity_id=request.rowid,
        HCD_Space=request.HCD_Space,
        HCD_Subspace=request.HCD_Subspace,
        reason=request.Reason,
        annotator=request.Annotator,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail="Failed to label activity")

    inserted_new = result["inserted_new"]
    if inserted_new:
        msg = (
            f"Activity {request.rowid} was already labeled. "
            f"A new duplicate entry has been created for annotator '{request.Annotator}'."
        )
    else:
        msg = f"Activity {request.rowid} labeled successfully by '{request.Annotator}'."

    return LabelActivityResponse(success=True, message=msg, inserted_new=inserted_new)


@app.get("/activity-annotations", response_model=ActivityAnnotationsResponse)
async def activity_annotations() -> ActivityAnnotationsResponse:
    """
    Return all labeled activities grouped by Activity text.

    Fetches every labeled row and groups them by their Activity value.
    Each group shows all annotations for that activity (from different
    annotators / auto-duplicated entries), making comparison easy.
    """
    rows = await get_activity_annotations()

    # Group by Activity text
    groups_map: dict[str, list[ActivityAnnotation]] = {}
    for row in rows:
        key = row.get("Activity", "")
        ann = ActivityAnnotation(
            rowid=row.get("rowid"),
            Activity=key,
            HCD_Space=row.get("HCD_Space", ""),
            HCD_Subspace=row.get("HCD_Subspace", ""),
            Reason=row.get("Reason", ""),
            Annotator=row.get("Annotator", ""),
        )
        groups_map.setdefault(key, []).append(ann)

    groups = [
        ActivityGroup(activity=act, count=len(anns), annotations=anns)
        for act, anns in groups_map.items()
    ]

    return ActivityAnnotationsResponse(
        total_activities=len(groups),
        groups=groups,
    )
