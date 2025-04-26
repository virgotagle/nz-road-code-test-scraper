# -*- coding: utf-8 -*-
"""
Database helper module for managing the SQLAlchemy engine, session, and schema.

Provides a convenient way to initialize the database schema and obtain
transactional sessions using a context manager.
"""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .config import ROAD_CODE_TEST_DB_URL
from .exceptions import DBHelperError
from .logging import get_logger
from .model import Base  # Import the base class for metadata

logger = get_logger(__name__)


class DBHelper:
    """
    Handles database connection, session management, and schema initialization.

    Uses SQLAlchemy to interact with the database defined in the configuration.
    """

    def __init__(self, db_url: str = ROAD_CODE_TEST_DB_URL) -> None:
        """
        Initialize the DBHelper.

        Creates the SQLAlchemy engine and session factory.

        :param db_url: The database connection URL. Defaults to the one in config.
        :type db_url: str
        """
        # Create the SQLAlchemy engine. `echo=False` disables SQL logging.
        self.engine = create_engine(db_url, echo=False)
        # Create a configured "Session" class. Instances of this class represent
        # individual database sessions.
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"DBHelper initialized for database: {db_url}")

    def initialize_schema(self) -> None:
        """
        Create all tables defined in the SQLAlchemy models (subclasses of Base).

        This method uses the engine to create tables based on the metadata
        associated with the `Base` declarative base class from `model.py`.
        It only creates tables that do not already exist.
        """
        try:
            # `Base.metadata` contains information about all mapped tables.
            Base.metadata.create_all(self.engine)
            logger.info("Database schema initialized successfully.")
        except SQLAlchemyError as e:
            logger.error("Failed to initialize database schema", exc_info=True)
            # Propagate the error for handling upstream if necessary
            raise DBHelperError("Failed to initialize database schema") from e

    @contextmanager
    def create_session(self) -> Iterator[Session]:
        """
        Provide a transactional database session via a context manager.

        Ensures the session is committed on successful completion or rolled back
        on exception, and closed afterwards.

        :yield: An active SQLAlchemy Session object.
        :rtype: Iterator[Session]
        :raises DBHelperError: If a database error occurs during the session commit.
        """
        logger.debug("Creating new DB session")
        # Instantiate a new session from the factory
        session = self.Session()
        try:
            # Yield the session to the 'with' block
            yield session
            # If the 'with' block completes without error, commit the transaction
            session.commit()
            logger.debug("DB session committed successfully")
        except SQLAlchemyError as e:
            # If any SQLAlchemy error occurs within the 'with' block, roll back
            logger.error("DB error occurred, rolling back transaction", exc_info=True)
            session.rollback()
            # Wrap the original exception in a custom DBHelperError
            raise DBHelperError(f"Session error: {e}") from e
        finally:
            # Always close the session, whether commit or rollback occurred
            session.close()
            logger.debug("DB session closed")
