"""Task CRUD endpoints."""

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DBSession
from app.db.models.task import TaskPriority, TaskStatus
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.task import (
    TaskAssign,
    TaskBulkStatusUpdate,
    TaskBulkStatusUpdateResponse,
    TaskCreate,
    TaskFilter,
    TaskResponse,
    TaskTransition,
    TaskUpdate,
)
from app.services import task_query_service, task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get(
    "",
    response_model=PaginatedResponse[TaskResponse],
    summary="List tasks with filtering and pagination",
)
def list_tasks(
    db: DBSession,
    current_user: CurrentUser,
    status: TaskStatus | None = Query(default=None, description="Filter by status"),
    priority: TaskPriority | None = Query(default=None, description="Filter by priority"),
    assignee_id: int | None = Query(default=None, description="Filter by assignee ID"),
    owner_id: int | None = Query(default=None, description="Filter by owner ID"),
    search: str | None = Query(
        default=None, max_length=100, description="Search in title and description"
    ),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[TaskResponse]:
    """List tasks with optional filtering, search, and pagination.

    Supports filtering by status, priority, assignee, and owner.
    Search parameter performs case-insensitive matching on title and description.
    """
    filters = TaskFilter(
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        owner_id=owner_id,
        search=search,
    )
    pagination = PaginationParams(page=page, per_page=per_page)

    return task_query_service.list_tasks(db, filters, pagination)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_task(
    task_data: TaskCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> TaskResponse:
    """Create a new task.

    The authenticated user becomes the owner of the task.
    """
    task = task_service.create_task(db, task_data, current_user)
    return TaskResponse.model_validate(task)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task by ID",
)
def get_task(
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> TaskResponse:
    """Get a task by its ID.

    Requires authentication.
    """
    task = task_service.get_task_by_id(db, task_id)
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> TaskResponse:
    """Update a task.

    Only the owner or assignee can update the task.
    """
    task = task_service.get_task_by_id(db, task_id)
    updated_task = task_service.update_task(db, task, task_data, current_user)
    return TaskResponse.model_validate(updated_task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
def delete_task(
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a task.

    Only the owner or assignee can delete the task.
    """
    task = task_service.get_task_by_id(db, task_id)
    task_service.delete_task(db, task, current_user)


@router.post(
    "/{task_id}/assign",
    response_model=TaskResponse,
    summary="Assign a task to a user",
)
def assign_task(
    task_id: int,
    assign_data: TaskAssign,
    db: DBSession,
    current_user: CurrentUser,
) -> TaskResponse:
    """Assign or unassign a task.

    Set assignee_id to a user ID to assign, or null to unassign.
    Only the owner or current assignee can change the assignment.
    """
    task = task_service.get_task_by_id(db, task_id)
    updated_task = task_service.assign_task(db, task, assign_data.assignee_id, current_user)
    return TaskResponse.model_validate(updated_task)


@router.post(
    "/{task_id}/transition",
    response_model=TaskResponse,
    summary="Transition task status",
)
def transition_task(
    task_id: int,
    transition_data: TaskTransition,
    db: DBSession,
    current_user: CurrentUser,
) -> TaskResponse:
    """Transition a task to a new status.

    Valid transitions follow the task workflow:
    - TODO -> IN_PROGRESS
    - IN_PROGRESS -> DONE, BLOCKED
    - BLOCKED -> IN_PROGRESS
    - DONE -> IN_PROGRESS (reopen)

    Only the owner or assignee can transition the task.
    """
    task = task_service.get_task_by_id(db, task_id)
    updated_task = task_service.transition_task_status(
        db, task, transition_data.target_status, current_user
    )
    return TaskResponse.model_validate(updated_task)


@router.post(
    "/bulk-status",
    response_model=TaskBulkStatusUpdateResponse,
    summary="Bulk update task statuses",
)
def bulk_update_status(
    request: TaskBulkStatusUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> TaskBulkStatusUpdateResponse:
    """Update status of multiple tasks at once.

    Validates:
    - All task IDs exist
    - User has permission for each task
    - All transitions are valid

    Returns detailed results for each task.
    """
    return task_service.bulk_update_status(db, request, current_user)


@router.delete(
    "/{task_id}/force",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Force delete a task",
)
def force_delete_task(
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Force delete a task.

    Only the owner or assignee can delete the task.
    """
    task = task_service.get_task_by_id(db, task_id)
    task_service._check_task_permission(task, current_user)
    db.delete(task)
    db.commit()
