"""Task-related schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models.task import VALID_TRANSITIONS, TaskPriority, TaskStatus
from app.schemas.user import UserBrief


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: int | None = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority | None = None


class TaskResponse(BaseModel):
    """Schema for task response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    owner_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime

    # Nested relationships (optional, for detailed responses)
    owner: UserBrief | None = None
    assignee: UserBrief | None = None


class TaskBrief(BaseModel):
    """Brief task info for list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TaskStatus
    priority: TaskPriority
    owner_id: int
    assignee_id: int | None
    created_at: datetime


class TaskFilter(BaseModel):
    """Schema for filtering tasks."""

    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    owner_id: int | None = None
    search: str | None = Field(default=None, max_length=100)


class TaskAssign(BaseModel):
    """Schema for assigning a task."""

    assignee_id: int | None = Field(description="User ID to assign, or null to unassign")


class TaskTransition(BaseModel):
    """Schema for transitioning task status."""

    target_status: TaskStatus

    @model_validator(mode="after")
    def validate_transition(self) -> "TaskTransition":
        """Validate that the target status is a valid enum value."""
        # The actual transition validation happens in the service layer
        # since we need the current status from the database
        return self


class TaskBulkStatusUpdate(BaseModel):
    """Schema for bulk status update request."""

    task_ids: list[int] = Field(min_length=1, max_length=100)
    target_status: TaskStatus


class TaskBulkUpdateResult(BaseModel):
    """Result of a single task in bulk update."""

    task_id: int
    success: bool
    error: str | None = None
    previous_status: TaskStatus | None = None
    new_status: TaskStatus | None = None


class TaskBulkStatusUpdateResponse(BaseModel):
    """Schema for bulk status update response."""

    total: int
    successful: int
    failed: int
    results: list[TaskBulkUpdateResult]


def validate_status_transition(current_status: TaskStatus, target_status: TaskStatus) -> bool:
    """Check if a status transition is valid.

    Args:
        current_status: The current task status.
        target_status: The desired target status.

    Returns:
        True if the transition is valid, False otherwise.
    """
    if current_status == target_status:
        return True  # No-op transitions are allowed

    valid_targets = VALID_TRANSITIONS.get(current_status, [])
    return target_status in valid_targets
