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
from database.db import fetch_unlabeld_activity, label_activity


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
        rowid=activity.get("rowid"),
        Activity=activity.get("Activity")
    )


@app.post("/label-activity", response_model=LabelActivityResponse)
async def label_activity_endpoint(request: LabelActivityRequest) -> LabelActivityResponse:
    """Label an activity with HCD classification."""
    success = await label_activity(
        activity_id=request.rowid,
        HCD_Space=request.HCD_Space,
        HCD_Subspace=request.HCD_Subspace,
        reason=request.Reason,
        annotator=request.Annotator
    )
    
    if success:
        return LabelActivityResponse(
            success=True,
            message=f"Activity {request.rowid} labeled successfully"
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to label activity"
        )


