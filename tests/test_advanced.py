"""Advanced tests for pagination, filtering, search, and authorization."""

from datetime import timedelta

import pytest

from app.core.jwt import create_access_token
from app.core.security import hash_password
from app.db.models.task import Task, TaskPriority, TaskStatus
from app.db.models.user import User


# --- Pagination Edge Cases ---

class TestPaginationEdgeCases:
    """Tests for pagination edge cases."""

    def test_list_tasks_empty(self, client, auth_headers):
        """No tasks returns empty list with correct pagination metadata."""
        response = client.get("/api/v1/tasks", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["pagination"]["total_items"] == 0
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_pages"] == 0

    def test_list_tasks_last_page(self, client, db, test_user, auth_headers):
        """Verify last page returns remaining items correctly."""
        # Create 5 tasks
        for i in range(5):
            task = Task(
                title=f"Task {i}",
                description=f"Description {i}",
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                owner_id=test_user.id,
            )
            db.add(task)
        db.commit()

        # Request page 2 with 3 per page (should return 2 items)
        response = client.get(
            "/api/v1/tasks?page=2&per_page=3",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["pagination"]["total_items"] == 5
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["total_pages"] == 2

    def test_list_tasks_invalid_page(self, client, db, test_user, auth_headers):
        """Page beyond results returns empty list."""
        # Create 2 tasks
        for i in range(2):
            task = Task(
                title=f"Task {i}",
                description=f"Description {i}",
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                owner_id=test_user.id,
            )
            db.add(task)
        db.commit()

        # Request page 10 when only 1 page exists
        response = client.get(
            "/api/v1/tasks?page=10&per_page=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["pagination"]["total_items"] == 2
        assert data["pagination"]["page"] == 10


# --- Filter Combination Tests ---

class TestFilterCombinations:
    """Tests for filtering tasks."""

    def test_filter_by_status(self, client, db, test_user, auth_headers):
        """Filter tasks by status."""
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

        response = client.get(
            "/api/v1/tasks?status=todo",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_items"] == 1
        assert data["items"][0]["title"] == "Todo Task"
        assert data["items"][0]["status"] == "todo"

    def test_filter_by_priority(self, client, db, test_user, auth_headers):
        """Filter tasks by priority."""
        # Create tasks with different priorities
        task_low = Task(
            title="Low Priority",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            owner_id=test_user.id,
        )
        task_high = Task(
            title="High Priority",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            owner_id=test_user.id,
        )
        db.add_all([task_low, task_high])
        db.commit()

        response = client.get(
            "/api/v1/tasks?priority=high",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_items"] == 1
        assert data["items"][0]["title"] == "High Priority"
        assert data["items"][0]["priority"] == "high"

    def test_filter_combined(self, client, db, test_user, auth_headers):
        """Filter tasks by both status AND priority."""
        # Create tasks with various combinations
        task1 = Task(
            title="Todo High",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            owner_id=test_user.id,
        )
        task2 = Task(
            title="Todo Low",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            owner_id=test_user.id,
        )
        task3 = Task(
            title="In Progress High",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            owner_id=test_user.id,
        )
        db.add_all([task1, task2, task3])
        db.commit()

        response = client.get(
            "/api/v1/tasks?status=todo&priority=high",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_items"] == 1
        assert data["items"][0]["title"] == "Todo High"
        assert data["items"][0]["status"] == "todo"
        assert data["items"][0]["priority"] == "high"


# --- Search Tests ---

class TestSearch:
    """Tests for search functionality."""

    def test_search_by_title(self, client, db, test_user, auth_headers):
        """Search tasks by title."""
        task1 = Task(
            title="Important Meeting",
            description="Regular description",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            owner_id=test_user.id,
        )
        task2 = Task(
            title="Regular Task",
            description="Nothing special",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            owner_id=test_user.id,
        )
        db.add_all([task1, task2])
        db.commit()

        response = client.get(
            "/api/v1/tasks?search=Important",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_items"] == 1
        assert data["items"][0]["title"] == "Important Meeting"

    def test_search_by_description(self, client, db, test_user, auth_headers):
        """Search tasks by description."""
        task1 = Task(
            title="Task One",
            description="Contains special keyword",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            owner_id=test_user.id,
        )
        task2 = Task(
            title="Task Two",
            description="Nothing interesting here",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            owner_id=test_user.id,
        )
        db.add_all([task1, task2])
        db.commit()

        response = client.get(
            "/api/v1/tasks?search=special",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_items"] == 1
        assert data["items"][0]["title"] == "Task One"


# --- Auth Security Tests ---

class TestAuthSecurity:
    """Tests for authentication security."""

    def test_expired_token(self, client, db, test_user):
        """Expired token returns 401."""
        # Create a token that expired 1 hour ago
        expired_token = create_access_token(
            subject=test_user.id,
            expires_delta=timedelta(hours=-1)
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        response = client.get("/api/v1/tasks", headers=headers)

        assert response.status_code == 401

    def test_invalid_token_format(self, client):
        """Invalid token format returns 401."""
        headers = {"Authorization": "Bearer not.a.valid.jwt.token"}

        response = client.get("/api/v1/tasks", headers=headers)

        assert response.status_code == 401

    def test_missing_token(self, client):
        """Missing token returns 401."""
        response = client.get("/api/v1/tasks")

        assert response.status_code == 401


# --- Authorization Tests ---

class TestAuthorization:
    """Tests for task authorization."""

    @pytest.fixture
    def other_user(self, db):
        """Create another user for authorization tests."""
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
    def other_user_headers(self, client, other_user):
        """Get auth headers for the other user."""
        response = client.post("/api/v1/auth/login", json={
            "email": "other@example.com",
            "password": "otherpass123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def task_owned_by_test_user(self, db, test_user):
        """Create a task owned by test_user."""
        task = Task(
            title="Test User's Task",
            description="Owned by test user",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            owner_id=test_user.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def test_update_others_task_forbidden(
        self, client, task_owned_by_test_user, other_user_headers
    ):
        """Updating another user's task returns 403."""
        response = client.patch(
            f"/api/v1/tasks/{task_owned_by_test_user.id}",
            json={"title": "Hacked Title"},
            headers=other_user_headers
        )

        assert response.status_code == 403

    def test_delete_others_task_forbidden(
        self, client, task_owned_by_test_user, other_user_headers
    ):
        """Deleting another user's task returns 403."""
        response = client.delete(
            f"/api/v1/tasks/{task_owned_by_test_user.id}",
            headers=other_user_headers
        )

        assert response.status_code == 403
