"""Tests for bug fixes and performance improvements."""

from app.core.security import hash_password
from app.db.models.task import Task, TaskPriority, TaskStatus
from app.db.models.user import User


class TestForceDeleteAuthorization:
    """Tests for the force delete endpoint authorization fix."""

    def test_force_delete_unauthorized(self, client, db, test_user, auth_headers):
        """Test that force delete fails when user doesn't have permission.

        A user who is neither owner nor assignee should receive 403 Forbidden.
        """
        # Create another user who owns the task
        other_user = User(
            email="other@example.com",
            hashed_password=hash_password("otherpass123"),
            full_name="Other User",
            is_active=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        # Create a task owned by the other user
        task = Task(
            title="Other user's task",
            description="This task belongs to another user",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            owner_id=other_user.id,
            assignee_id=None,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Try to force delete as test_user (who is not owner or assignee)
        response = client.delete(
            f"/api/v1/tasks/{task.id}/force",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "permission" in response.json()["error"]["message"].lower()

        # Verify task still exists
        db.expire_all()
        task_still_exists = db.query(Task).filter(Task.id == task.id).first()
        assert task_still_exists is not None

    def test_force_delete_authorized_as_owner(self, client, db, test_user, auth_headers):
        """Test that force delete succeeds when user is the owner."""
        # Create a task owned by test_user
        task = Task(
            title="My task",
            description="This task belongs to test_user",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            owner_id=test_user.id,
            assignee_id=None,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

        # Force delete as owner
        response = client.delete(
            f"/api/v1/tasks/{task_id}/force",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify task is deleted
        db.expire_all()
        task_deleted = db.query(Task).filter(Task.id == task_id).first()
        assert task_deleted is None

    def test_force_delete_authorized_as_assignee(self, client, db, test_user, auth_headers):
        """Test that force delete succeeds when user is the assignee."""
        # Create another user who owns the task
        other_user = User(
            email="owner@example.com",
            hashed_password=hash_password("ownerpass123"),
            full_name="Owner User",
            is_active=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        # Create a task owned by other_user but assigned to test_user
        task = Task(
            title="Assigned task",
            description="This task is assigned to test_user",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            owner_id=other_user.id,
            assignee_id=test_user.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

        # Force delete as assignee
        response = client.delete(
            f"/api/v1/tasks/{task_id}/force",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify task is deleted
        db.expire_all()
        task_deleted = db.query(Task).filter(Task.id == task_id).first()
        assert task_deleted is None


class TestListTasksPerformance:
    """Tests for the N+1 query fix in list_tasks."""

    def test_list_tasks_returns_owner_and_assignee(self, client, db, test_user, auth_headers):
        """Test that list_tasks returns tasks with owner and assignee data."""
        # Create another user as assignee
        assignee_user = User(
            email="assignee@example.com",
            hashed_password=hash_password("assigneepass123"),
            full_name="Assignee User",
            is_active=True,
        )
        db.add(assignee_user)
        db.commit()
        db.refresh(assignee_user)

        # Create a task with owner and assignee
        task = Task(
            title="Task with both owner and assignee",
            description="Test task",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            owner_id=test_user.id,
            assignee_id=assignee_user.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # List tasks
        response = client.get(
            "/api/v1/tasks",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_items"] >= 1

        # Find our task
        tasks = data["items"]
        our_task = next(
            (t for t in tasks if t["title"] == "Task with both owner and assignee"), None
        )
        assert our_task is not None

        # Verify owner data is included
        assert our_task["owner"] is not None
        assert our_task["owner"]["id"] == test_user.id
        assert our_task["owner"]["email"] == test_user.email
        assert our_task["owner"]["full_name"] == test_user.full_name

        # Verify assignee data is included
        assert our_task["assignee"] is not None
        assert our_task["assignee"]["id"] == assignee_user.id
        assert our_task["assignee"]["email"] == assignee_user.email
        assert our_task["assignee"]["full_name"] == assignee_user.full_name

    def test_list_tasks_with_multiple_tasks(self, client, db, test_user, auth_headers):
        """Test that list_tasks handles multiple tasks correctly."""
        # Create multiple tasks
        for i in range(5):
            task = Task(
                title=f"Task {i}",
                description=f"Description {i}",
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                owner_id=test_user.id,
                assignee_id=None,
            )
            db.add(task)
        db.commit()

        # List tasks
        response = client.get(
            "/api/v1/tasks",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_items"] >= 5

        # All tasks should have owner data
        for task in data["items"]:
            assert task["owner"] is not None
            assert task["owner"]["id"] == test_user.id
