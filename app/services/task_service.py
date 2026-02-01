"""Task service for task CRUD operations, assignment, and status transitions."""

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
)
from app.db.models.task import VALID_TRANSITIONS, Task, TaskStatus
from app.db.models.user import User
from app.schemas.task import (
    TaskBulkStatusUpdate,
    TaskBulkStatusUpdateResponse,
    TaskBulkUpdateResult,
    TaskCreate,
    TaskUpdate,
)
from app.services.user_service import get_user_by_id


def get_task_by_id(db: Session, task_id: int) -> Task:
    """Get a task by ID.

    Args:
        db: Database session.
        task_id: The task's ID.

    Returns:
        The Task object.

    Raises:
        NotFoundError: If the task doesn't exist.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise NotFoundError("Task", task_id)
    return task


def create_task(db: Session, task_data: TaskCreate, owner: User) -> Task:
    """Create a new task.

    Args:
        db: Database session.
        task_data: Task creation data.
        owner: The user creating the task.

    Returns:
        The created Task object.

    Raises:
        NotFoundError: If the assignee doesn't exist.
    """
    # Validate assignee if specified
    if task_data.assignee_id:
        get_user_by_id(db, task_data.assignee_id)

    task = Task(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        status=TaskStatus.TODO,
        owner_id=owner.id,
        assignee_id=task_data.assignee_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, task_data: TaskUpdate, user: User) -> Task:
    """Update a task.

    Args:
        db: Database session.
        task: The task to update.
        task_data: Update data.
        user: The user performing the update.

    Returns:
        The updated Task object.

    Raises:
        ForbiddenError: If the user doesn't have permission.
    """
    _check_task_permission(task, user)

    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.priority is not None:
        task.priority = task_data.priority

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task, user: User) -> None:
    """Delete a task.

    Args:
        db: Database session.
        task: The task to delete.
        user: The user performing the deletion.

    Raises:
        ForbiddenError: If the user doesn't have permission.
    """
    _check_task_permission(task, user)
    db.delete(task)
    db.commit()


def assign_task(db: Session, task: Task, assignee_id: int | None, user: User) -> Task:
    """Assign or unassign a task.

    Args:
        db: Database session.
        task: The task to assign.
        assignee_id: The user ID to assign, or None to unassign.
        user: The user performing the assignment.

    Returns:
        The updated Task object.

    Raises:
        ForbiddenError: If the user doesn't have permission.
        NotFoundError: If the assignee doesn't exist.
    """
    _check_task_permission(task, user)

    if assignee_id is not None:
        get_user_by_id(db, assignee_id)

    task.assignee_id = assignee_id
    db.commit()
    db.refresh(task)
    return task


def transition_task_status(db: Session, task: Task, target_status: TaskStatus, user: User) -> Task:
    """Transition a task to a new status.

    Args:
        db: Database session.
        task: The task to transition.
        target_status: The target status.
        user: The user performing the transition.

    Returns:
        The updated Task object.

    Raises:
        ForbiddenError: If the user doesn't have permission.
        InvalidTransitionError: If the transition is not allowed.
    """
    _check_task_permission(task, user)

    if task.status == target_status:
        return task  # No-op

    if not _is_valid_transition(task.status, target_status):
        raise InvalidTransitionError(task.status.value, target_status.value)

    task.status = target_status
    db.commit()
    db.refresh(task)
    return task


def bulk_update_status(
    db: Session, request: TaskBulkStatusUpdate, user: User
) -> TaskBulkStatusUpdateResponse:
    """Bulk update task statuses.

    Args:
        db: Database session.
        request: Bulk update request.
        user: The user performing the update.

    Returns:
        Response with success/failure details.
    """
    results: list[TaskBulkUpdateResult] = []
    successful = 0
    failed = 0

    for task_id in request.task_ids:
        try:
            task = get_task_by_id(db, task_id)
            _check_task_permission(task, user)

            previous_status = task.status

            if task.status == request.target_status:
                # No-op, still counts as success
                results.append(
                    TaskBulkUpdateResult(
                        task_id=task_id,
                        success=True,
                        previous_status=previous_status,
                        new_status=request.target_status,
                    )
                )
                successful += 1
                continue

            if not _is_valid_transition(task.status, request.target_status):
                results.append(
                    TaskBulkUpdateResult(
                        task_id=task_id,
                        success=False,
                        error=f"Invalid transition from '{task.status.value}' to '{request.target_status.value}'",
                        previous_status=previous_status,
                    )
                )
                failed += 1
                continue

            task.status = request.target_status
            results.append(
                TaskBulkUpdateResult(
                    task_id=task_id,
                    success=True,
                    previous_status=previous_status,
                    new_status=request.target_status,
                )
            )
            successful += 1

        except NotFoundError:
            results.append(
                TaskBulkUpdateResult(
                    task_id=task_id,
                    success=False,
                    error=f"Task {task_id} not found",
                )
            )
            failed += 1

        except ForbiddenError:
            results.append(
                TaskBulkUpdateResult(
                    task_id=task_id,
                    success=False,
                    error="Permission denied",
                )
            )
            failed += 1

    db.commit()

    return TaskBulkStatusUpdateResponse(
        total=len(request.task_ids),
        successful=successful,
        failed=failed,
        results=results,
    )


def _check_task_permission(task: Task, user: User) -> None:
    """Check if a user has permission to modify a task.

    A user can modify a task if they are the owner or assignee.

    Args:
        task: The task to check.
        user: The user to check permissions for.

    Raises:
        ForbiddenError: If the user doesn't have permission.
    """
    if task.owner_id != user.id and task.assignee_id != user.id:
        raise ForbiddenError("You don't have permission to modify this task")


def _is_valid_transition(current: TaskStatus, target: TaskStatus) -> bool:
    """Check if a status transition is valid."""
    if current == target:
        return True
    valid_targets = VALID_TRANSITIONS.get(current, [])
    return target in valid_targets
