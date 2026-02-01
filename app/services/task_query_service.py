"""Task query service for listing and filtering tasks.

NOTE: This service intentionally has an N+1 query problem for demonstration.
The fix will be applied in Phase 11 to showcase performance optimization.
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.task import Task
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.task import TaskFilter, TaskResponse


def list_tasks(
    db: Session,
    filters: TaskFilter,
    pagination: PaginationParams,
) -> PaginatedResponse[TaskResponse]:
    """List tasks with filtering, search, and pagination.

    INTENTIONAL N+1 QUERY: This implementation fetches tasks first,
    then accesses owner and assignee relationships lazily, causing
    additional queries for each task. This will be fixed in Phase 11.

    Args:
        db: Database session.
        filters: Filter criteria.
        pagination: Pagination parameters.

    Returns:
        Paginated list of tasks.
    """
    query = db.query(Task)

    # Apply filters
    if filters.status:
        query = query.filter(Task.status == filters.status)

    if filters.priority:
        query = query.filter(Task.priority == filters.priority)

    if filters.assignee_id:
        query = query.filter(Task.assignee_id == filters.assignee_id)

    if filters.owner_id:
        query = query.filter(Task.owner_id == filters.owner_id)

    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term),
            )
        )

    # Get total count
    total_items = query.count()

    # Apply pagination and ordering
    tasks = (
        query.order_by(Task.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.per_page)
        .all()
    )

    # INTENTIONAL N+1: Converting to response triggers lazy loading
    # of owner and assignee for each task, causing N additional queries
    task_responses = []
    for task in tasks:
        # Accessing task.owner and task.assignee causes lazy loading
        task_response = TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            owner_id=task.owner_id,
            assignee_id=task.assignee_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
            owner={
                "id": task.owner.id,
                "email": task.owner.email,
                "full_name": task.owner.full_name,
            } if task.owner else None,
            assignee={
                "id": task.assignee.id,
                "email": task.assignee.email,
                "full_name": task.assignee.full_name,
            } if task.assignee else None,
        )
        task_responses.append(task_response)

    return PaginatedResponse.create(
        items=task_responses,
        total_items=total_items,
        page=pagination.page,
        per_page=pagination.per_page,
    )


def get_task_with_relations(db: Session, task_id: int) -> Task | None:
    """Get a single task with its relationships loaded.

    Args:
        db: Database session.
        task_id: The task's ID.

    Returns:
        The Task object with owner and assignee loaded, or None.
    """
    # For single task, N+1 isn't a problem, but we still load eagerly
    # for consistency with the fixed version we'll implement later
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        # Trigger lazy loading (will be 2 extra queries)
        _ = task.owner
        _ = task.assignee
    return task
