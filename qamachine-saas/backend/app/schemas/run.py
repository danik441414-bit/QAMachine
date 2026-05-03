from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class RunArtifactOut(BaseModel):
    id:   str
    type: str
    name: str
    path: str
    size: int


class RunOut(BaseModel):
    id:            str
    chat_id:       str
    target_url:    str
    task:          str
    status:        str
    mode:          str | None
    step_count:    int
    issue_count:   int
    summary:       str | None
    report_path:   str | None
    error_message: str | None
    artifacts:     list[RunArtifactOut]
    created_at:    datetime
    started_at:    datetime | None
    completed_at:  datetime | None

    model_config = {"from_attributes": True}
