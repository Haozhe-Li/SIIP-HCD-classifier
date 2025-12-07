from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from core.data_table import LLM_HCD_Label, List_Output_Label, List_Student_HCD_Label
from core.postprocessing import FinalProcessing
from core.preprocessing import PreProcessor
from core.processing import Processing

logger = logging.getLogger(__name__)


class ClassificationResponse(BaseModel):
    student_labels: List_Student_HCD_Label
    llm_labels: list[LLM_HCD_Label]
    final_labels: List_Output_Label


class RootResponse(BaseModel):
    message: str
    endpoints: dict[str, str]


app = FastAPI(title="SIIP HCD Classifier API", version="0.1.0")

preprocessor = PreProcessor()
processor = Processing()
final_processor = FinalProcessing()


def _validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    content_type = (file.content_type or "").lower()
    if not content_type:
        content_type = "application/pdf" if file.filename.lower().endswith(".pdf") else ""

    if content_type not in {"application/pdf", "application/octet-stream"} and not file.filename.lower().endswith(".pdf"):
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
        student_labels = await preprocessor.ainvoke(temp_path.as_posix())
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
            except (PermissionError, OSError) as e:
                logger.warning(f"Failed to remove temporary file {temp_path}: {e}")

    return ClassificationResponse(
        student_labels=student_labels,
        llm_labels=llm_labels,
        final_labels=final_labels,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("gradio_gui:app", host="0.0.0.0", port=8001, reload=False)
