"""Tests for bulk status update endpoint."""

import pytest

from app.core.security import hash_password
from app.db.models.task import Task, TaskPriority, TaskStatus
from app.db.models.user import User


@pytest.fixture
def other_user(db):
    """Create another user for permission tests."""
    user = User(
        email="other@example.com",
        hashed_password=hash_password("otherpass123"),
        full_name="Other User",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_tasks(db, test_user):
    """Create multiple test tasks owned by test_user."""
    tasks = []
    for i in range(3):
        task = Task(
            title=f"Test Task {i + 1}",
            description=f"Description for task {i + 1}",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            owner_id=test_user.id,
        )
        db.add(task)
        tasks.append(task)
    db.commit()
    for task in tasks:
        db.refresh(task)
    return tasks


@pytest.fixture
def other_user_task(db, other_user):
    """Create a task owned by other_user."""
    task = Task(
        title="Other User Task",
        description="Task owned by another user",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        owner_id=other_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def test_bulk_update_success(client, auth_headers, test_tasks):
    """Test successful bulk update of multiple tasks."""
    task_ids = [task.id for task in test_tasks]

    response = client.post(
        "/api/v1/tasks/bulk-status",
        headers=auth_headers,
        json={
            "task_ids": task_ids,
            "target_status": "in_progress",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["successful"] == 3
    assert data["failed"] == 0
    assert len(data["results"]) == 3

    for result in data["results"]:
        assert result["success"] is True
        assert result["previous_status"] == "todo"
        assert result["new_status"] == "in_progress"
        assert result["error"] is None


def test_bulk_update_partial_failure(client, auth_headers, db, test_user):
    """Test bulk update where some tasks fail validation (invalid transition)."""
    # Create tasks with different statuses
    task_todo = Task(
        title="Todo Task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        owner_id=test_user.id,
    )
    task_in_progress = Task(
        title="In Progress Task",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.MEDIUM,
        owner_id=test_user.id,
    )
    db.add_all([task_todo, task_in_progress])
    db.commit()
    db.refresh(task_todo)
    db.refresh(task_in_progress)

    # Try to transition both to DONE - only IN_PROGRESS -> REVIEW -> DONE is valid
    # TODO -> DONE is invalid
    response = client.post(
        "/api/v1/tasks/bulk-status",
        headers=auth_headers,
        json={
            "task_ids": [task_todo.id, task_in_progress.id],
            "target_status": "review",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1

    # Check results
    results_by_id = {r["task_id"]: r for r in data["results"]}

    # TODO -> REVIEW should fail (invalid transition)
    assert results_by_id[task_todo.id]["success"] is False
    assert "Invalid transition" in results_by_id[task_todo.id]["error"]

    # IN_PROGRESS -> REVIEW should succeed
    assert results_by_id[task_in_progress.id]["success"] is True
    assert results_by_id[task_in_progress.id]["new_status"] == "review"


def test_bulk_update_invalid_ids(client, auth_headers, test_tasks):
    """Test bulk update with non-existent task IDs."""
    valid_id = test_tasks[0].id
    invalid_ids = [99999, 99998]

    response = client.post(
        "/api/v1/tasks/bulk-status",
        headers=auth_headers,
        json={
            "task_ids": [valid_id] + invalid_ids,
            "target_status": "in_progress",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["successful"] == 1
    assert data["failed"] == 2

    results_by_id = {r["task_id"]: r for r in data["results"]}

    # Valid task should succeed
    assert results_by_id[valid_id]["success"] is True

    # Invalid IDs should fail with "not found" error
    for invalid_id in invalid_ids:
        assert results_by_id[invalid_id]["success"] is False
        assert "not found" in results_by_id[invalid_id]["error"]


def test_bulk_update_no_permission(client, auth_headers, test_tasks, other_user_task):
    """Test bulk update when user doesn't own some tasks."""
    # Include a task owned by test_user and one owned by other_user
    own_task_id = test_tasks[0].id
    other_task_id = other_user_task.id

    response = client.post(
        "/api/v1/tasks/bulk-status",
        headers=auth_headers,
        json={
            "task_ids": [own_task_id, other_task_id],
            "target_status": "in_progress",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1

    results_by_id = {r["task_id"]: r for r in data["results"]}

    # Own task should succeed
    assert results_by_id[own_task_id]["success"] is True

    # Other user's task should fail with permission denied
    assert results_by_id[other_task_id]["success"] is False
    assert "Permission denied" in results_by_id[other_task_id]["error"]
