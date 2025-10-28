# -*- coding: utf-8 -*-
# Global data table structure for HCD classification

from pydantic import BaseModel, Field


class Student_HCD_Label(BaseModel):
    """Structured representation of a single activity row from the HCD table.

    Attributes:
        activity: Text describing the activity from the source table.
        HCD_Spaces: Ordered list of HCD spaces linked to the activity.
        HCD_Subspaces: Ordered list of HCD subspaces linked to the activity.
    """

    activity: str = Field(..., description="The Content in the Activity column")
    HCD_Spaces: list[str] = Field(
        ..., description="The Content in the corresponding activity's HCD Space column"
    )
    HCD_Subspaces: list[str] = Field(
        ...,
        description="The Content in the corresponding activity's HCD Subspace column",
    )


class List_Student_HCD_Label(BaseModel):
    """Container for multiple activity rows returned by the parser.

    Attributes:
        tables: Collection of extracted activity entries as `Student_HCD_Label` records.
    """

    tables: list[Student_HCD_Label] = Field(
        ..., description="List of extracted table data"
    )


class LLM_HCD_Label(BaseModel):
    """Structured representation of a single activity row from the HCD table.

    Attributes:
        activity: Text describing the activity from the source table.
        HCD_Spaces: Ordered list of HCD spaces linked to the activity.
        HCD_Subspaces: Ordered list of HCD subspaces linked to the activity.
        Reason: The reason for the assigned labels.
    """

    activity: str = Field(..., description="The Content in the Activity column")
    HCD_Spaces: list[str] = Field(
        ..., description="The Content in the corresponding activity's HCD Space column"
    )
    HCD_Subspaces: list[str] = Field(
        ...,
        description="The Content in the corresponding activity's HCD Subspace column",
    )
    Reason: str = Field(..., description="The reason for the assigned labels")


class Output_Label(BaseModel):
    """Structured representation of a single output label entry.

    Attributes:
        student_labeled_subspaces: The student's labeled HCD subspaces.
        result: 1 if correct, 0 if not enough evidence, -1 if incorrect.
    """

    student_labeled_subspaces: str = Field(
        ..., description="The student's labeled HCD subspaces"
    )
    result: int = Field(
        ..., description="1 if correct, 0 if not enough evidence, -1 if incorrect"
    )


class List_Output_Label(BaseModel):
    """Container for multiple output label entries.

    Attributes:
        labels: Collection of extracted output label entries as `Output_Label` records.
    """

    labels: list[Output_Label] = Field(
        ..., description="List of extracted output label data"
    )
