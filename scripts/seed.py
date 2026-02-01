#!/usr/bin/env python3
"""Seed script to populate the database with sample data."""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.task import Task, TaskStatus, TaskPriority


def create_users(db) -> list[User]:
    """Create sample users."""
    users_data = [
        {
            "email": "admin@example.com",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G5j0zH9E7WvWGq",  # password: admin123
            "full_name": "Admin User",
            "is_active": True,
        },
        {
            "email": "john@example.com",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G5j0zH9E7WvWGq",  # password: admin123
            "full_name": "John Doe",
            "is_active": True,
        },
        {
            "email": "jane@example.com",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G5j0zH9E7WvWGq",  # password: admin123
            "full_name": "Jane Smith",
            "is_active": True,
        },
        {
            "email": "inactive@example.com",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G5j0zH9E7WvWGq",  # password: admin123
            "full_name": "Inactive User",
            "is_active": False,
        },
    ]

    users = []
    for data in users_data:
        existing = db.query(User).filter(User.email == data["email"]).first()
        if existing:
            print(f"  User '{data['email']}' already exists, skipping")
            users.append(existing)
        else:
            user = User(**data)
            db.add(user)
            db.flush()
            print(f"  Created user: {data['email']}")
            users.append(user)

    return users


def create_tasks(db, users: list[User]) -> list[Task]:
    """Create sample tasks."""
    admin, john, jane, _ = users

    tasks_data = [
        {
            "title": "Set up project scaffolding",
            "description": "Initialize the FastAPI project with proper directory structure and dependencies.",
            "status": TaskStatus.DONE,
            "priority": TaskPriority.HIGH,
            "owner_id": admin.id,
            "assignee_id": admin.id,
        },
        {
            "title": "Implement user authentication",
            "description": "Add JWT-based authentication with login, register, and token refresh endpoints.",
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.HIGH,
            "owner_id": admin.id,
            "assignee_id": john.id,
        },
        {
            "title": "Create task CRUD endpoints",
            "description": "Implement create, read, update, delete operations for tasks.",
            "status": TaskStatus.TODO,
            "priority": TaskPriority.HIGH,
            "owner_id": admin.id,
            "assignee_id": jane.id,
        },
        {
            "title": "Add task filtering and search",
            "description": "Allow filtering tasks by status, priority, and assignee. Add full-text search on title.",
            "status": TaskStatus.TODO,
            "priority": TaskPriority.MEDIUM,
            "owner_id": john.id,
            "assignee_id": None,
        },
        {
            "title": "Write unit tests",
            "description": "Add comprehensive tests for services and endpoints.",
            "status": TaskStatus.TODO,
            "priority": TaskPriority.MEDIUM,
            "owner_id": admin.id,
            "assignee_id": None,
        },
        {
            "title": "Set up CI/CD pipeline",
            "description": "Configure GitHub Actions for automated testing and deployment.",
            "status": TaskStatus.TODO,
            "priority": TaskPriority.LOW,
            "owner_id": admin.id,
            "assignee_id": None,
        },
        {
            "title": "Add API documentation",
            "description": "Enhance OpenAPI docs with examples and descriptions.",
            "status": TaskStatus.REVIEW,
            "priority": TaskPriority.LOW,
            "owner_id": jane.id,
            "assignee_id": jane.id,
        },
        {
            "title": "Fix pagination bug",
            "description": "Tasks list returns wrong count when filtering by status.",
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.URGENT,
            "owner_id": john.id,
            "assignee_id": john.id,
        },
    ]

    tasks = []
    for data in tasks_data:
        existing = db.query(Task).filter(Task.title == data["title"]).first()
        if existing:
            print(f"  Task '{data['title'][:40]}...' already exists, skipping")
            tasks.append(existing)
        else:
            task = Task(**data)
            db.add(task)
            db.flush()
            print(f"  Created task: {data['title'][:40]}...")
            tasks.append(task)

    return tasks


def seed():
    """Main seed function."""
    print("Starting database seed...")
    db = SessionLocal()

    try:
        print("\nCreating users...")
        users = create_users(db)

        print("\nCreating tasks...")
        create_tasks(db, users)

        db.commit()
        print("\nSeed completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"\nError during seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()