# -*- coding: utf-8 -*-
# Global data table structure for HCD classification

from pydantic import BaseModel, Field


class DataTable(BaseModel):
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


class ListDataTable(BaseModel):
    """Container for multiple activity rows returned by the parser.

    Attributes:
        tables: Collection of extracted activity entries as `DataTable` records.
    """

    tables: list[DataTable] = Field(..., description="List of extracted table data")
