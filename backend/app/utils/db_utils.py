# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides database management functions and utilities for scaling operations.

This module offers functions for interacting with the SQLite database, including
creating the database schema and managing sessions.
"""

from collections.abc import Generator
from contextlib import contextmanager

from typing import Any

import structlog
from sqlmodel import Session, SQLModel, create_engine

# Initialize logger for this module
log = structlog.stdlib.get_logger(__name__)

# Database configuration
sqlite_url = "sqlite:///database/SQLite.db"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


# ========================================================== #
#                Generic Utility Functions                   #
# ========================================================== #


def create_database() -> None:
    """
    Create the database schema based on the defined SQLModel models.

    Process:
    -------
    -------
        - Uses the SQLModel.metadata.create_all() function to create the database schema based on the defined models.

    Args:
    ----
    ----
        - None.

    Returns:
    -------
    -------
        - None.

    Exceptions:
    ----------
    ----------
        - None.
    """
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope() -> Generator[Session, Any, None]:
    """
    Provides a transactional scope around a database session.

    Process:
    -------
    -------
        - Creates a new database session using the provided engine.
        - Yields the session to the caller, allowing for database operations within the context.
        - Automatically commits changes to the database if no exceptions occur.
        - Rolls back any changes if an exception is raised.
        - Closes the session regardless of whether changes were committed or rolled back.

    Args:
    ----
    ----
        - None.

    Returns:
    -------
    -------
        - Generator[Session, Any, None]: A generator that yields a database session within the transactional scope.

    Exceptions:
    ----------
    ----------
        - Exception: If an unexpected error occurs during the session.
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
