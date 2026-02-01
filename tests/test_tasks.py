"""Tests for task endpoints."""

from fastapi import status


class TestCreateTask:
    """Tests for task creation."""

    def test_create_task(self, client, auth_headers):
        """Test creating a new task."""
        response = client.post(
            "/api/v1/tasks",
            json={
                "title": "Test Task",
                "description": "A test task description",
                "priority": "high",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Test Task"
        assert data["description"] == "A test task description"
        assert data["priority"] == "high"
        assert data["status"] == "todo"


class TestGetTask:
    """Tests for getting a task."""

    def test_get_task(self, client, auth_headers):
        """Test getting a task by ID."""
        # Create a task first
        create_response = client.post(
            "/api/v1/tasks",
            json={"title": "Task to Get", "description": "Description"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        # Get the task
        response = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == "Task to Get"


class TestUpdateTask:
    """Tests for updating a task."""

    def test_update_task(self, client, auth_headers):
        """Test updating a task."""
        # Create a task first
        create_response = client.post(
            "/api/v1/tasks",
            json={"title": "Original Title", "description": "Original description"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        # Update the task
        response = client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"title": "Updated Title", "priority": "urgent"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["priority"] == "urgent"


class TestDeleteTask:
    """Tests for deleting a task."""

    def test_delete_task(self, client, auth_headers):
        """Test deleting a task."""
        # Create a task first
        create_response = client.post(
            "/api/v1/tasks", json={"title": "Task to Delete"}, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        # Delete the task
        response = client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify the task is gone
        get_response = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class TestListTasks:
    """Tests for listing tasks."""

    def test_list_tasks(self, client, auth_headers):
        """Test listing tasks with pagination."""
        # Create some tasks
        for i in range(3):
            client.post("/api/v1/tasks", json={"title": f"Task {i}"}, headers=auth_headers)

        # List tasks
        response = client.get("/api/v1/tasks", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 3
        assert "pagination" in data
        assert data["pagination"]["total_items"] == 3


class TestTransitionTask:
    """Tests for task status transitions."""

    def test_transition_task(self, client, auth_headers):
        """Test transitioning a task to a new status."""
        # Create a task (starts in TODO)
        create_response = client.post(
            "/api/v1/tasks", json={"title": "Task to Transition"}, headers=auth_headers
        )
        task_id = create_response.json()["id"]
        assert create_response.json()["status"] == "todo"

        # Transition to IN_PROGRESS
        response = client.post(
            f"/api/v1/tasks/{task_id}/transition",
            json={"target_status": "in_progress"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "in_progress"
