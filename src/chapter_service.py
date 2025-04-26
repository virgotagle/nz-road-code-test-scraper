# -*- coding: utf-8 -*-
"""
Service layer for interacting with Chapter data in the database.

Provides methods for inserting and retrieving Chapter, Question, and Answer
objects using SQLAlchemy, encapsulating database logic. Handles conversion
between Pydantic schemas and SQLAlchemy models.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from .exceptions import ChapterServiceError, exception_handler
from .logging import get_logger
from .model import Answer, Chapter, Question  # SQLAlchemy models
from .schema import AnswerSchema, ChapterSchema, QuestionSchema  # Pydantic schemas

logger = get_logger(__name__)


class ChapterService:
    """
    Service class to manage database operations for Chapters.

    Uses an active SQLAlchemy session provided during initialization to
    perform CRUD-like operations (primarily Create and Read).
    """

    def __init__(self, session: Session):
        """
        Initialize the ChapterService with a SQLAlchemy session.

        :param session: An active SQLAlchemy session object.
        :type session: Session
        """
        self.session = session

    @exception_handler(ChapterServiceError, logger, "Failed during batch chapter insert")
    def batch_insert_chapters(self, chapters: List[ChapterSchema]) -> None:
        """
        Insert multiple chapters into the database, skipping existing ones.

        Iterates through a list of ChapterSchema objects and attempts to insert
        each one using `insert_chapter`.

        :param chapters: A list of ChapterSchema objects to insert.
        :type chapters: List[ChapterSchema]
        :raises ChapterServiceError: If an unexpected error occurs during insertion.
        """
        # Process each chapter schema individually
        for chapter_schema in chapters:
            self.insert_chapter(chapter_schema)  # insert_chapter handles existence check

    @exception_handler(ChapterServiceError, logger, "Failed during single chapter insert")
    def insert_chapter(self, chapter_schema: ChapterSchema) -> bool:
        """
        Insert a single chapter and its related questions/answers if it doesn't already exist.

        Checks for chapter existence by ID before creating and adding the new chapter
        model hierarchy to the session.

        :param chapter_schema: The ChapterSchema object containing data to insert.
        :type chapter_schema: ChapterSchema
        :return: True if the chapter was inserted, False if it already existed.
        :rtype: bool
        :raises ChapterServiceError: If an unexpected error occurs during insertion.
        """
        chapter_id = chapter_schema.id
        # Prevent duplicates by checking if the chapter ID already exists
        if self.chapter_exists(chapter_id):
            logger.info(f"Chapter ID {chapter_id} already exists. Skipping insert.")
            return False

        # Convert schema to SQLAlchemy model
        chapter = self._create_chapter(chapter_schema)
        # Add the new chapter (and its cascaded questions/answers) to the session
        self.session.add(chapter)
        logger.info(f"Prepared chapter ID {chapter_id} for insertion.")
        # Note: Actual insertion happens on session commit managed by DBHelper context manager
        return True

    @exception_handler(ChapterServiceError, logger, "Failed to retrieve chapter")
    def get_chapter(self, chapter_id: int) -> Optional[Chapter]:
        """
        Retrieve a single chapter from the database by its primary key (ID).

        :param chapter_id: The ID of the chapter to retrieve.
        :type chapter_id: int
        :return: The Chapter model instance if found, otherwise None.
        :rtype: Optional[Chapter]
        :raises ChapterServiceError: If an unexpected error occurs during retrieval.
        """
        # Query the Chapter table for a record matching the given id
        return self.session.query(Chapter).filter_by(id=chapter_id).first()

    @exception_handler(ChapterServiceError, logger, "Failed to retrieve all chapters")
    def get_all_chapters(self) -> List[Chapter]:
        """
        Retrieve all chapters stored in the database.

        :return: A list of all Chapter model instances.
        :rtype: List[Chapter]
        :raises ChapterServiceError: If an unexpected error occurs during retrieval.
        """
        # Query the Chapter table for all records
        return self.session.query(Chapter).all()

    @exception_handler(ChapterServiceError, logger, "Failed during chapter existence check")
    def chapter_exists(self, chapter_id: int) -> bool:
        """
        Check if a chapter with the given ID exists in the database.

        Performs an efficient query checking only for the existence of the ID.

        :param chapter_id: The ID of the chapter to check.
        :type chapter_id: int
        :return: True if the chapter exists, False otherwise.
        :rtype: bool
        :raises ChapterServiceError: If an unexpected error occurs during the check.
        """
        # Query for the existence of the primary key, which is generally faster
        # than retrieving the whole object. `scalar()` returns the first element
        # of the first result or None.
        return self.session.query(Chapter.id).filter_by(id=chapter_id).scalar() is not None

    # Internal helper methods for converting Schemas to SQLAlchemy Models
    # These are typically not called directly from outside the class.

    def _create_chapter(self, schema: ChapterSchema) -> Chapter:
        """
        Convert a ChapterSchema into a SQLAlchemy Chapter model instance.

        Recursively converts nested QuestionSchema objects.

        :param schema: The ChapterSchema instance to convert.
        :type schema: ChapterSchema
        :return: A SQLAlchemy Chapter model instance.
        :rtype: Chapter
        """
        return Chapter(
            id=schema.id,
            title=schema.title,
            intro=schema.intro,
            # Create Question models from nested QuestionSchemas
            questions=[self._create_question(q) for q in schema.questions],
        )

    def _create_question(self, schema: QuestionSchema) -> Question:
        """
        Convert a QuestionSchema into a SQLAlchemy Question model instance.

        Recursively converts nested AnswerSchema objects.

        :param schema: The QuestionSchema instance to convert.
        :type schema: QuestionSchema
        :return: A SQLAlchemy Question model instance.
        :rtype: Question
        """
        return Question(
            id=schema.id,
            question=schema.question,
            image_url=schema.image_url,
            image_base64=schema.image_base64,
            # Create Answer models from nested AnswerSchemas
            answers=[self._create_answer(a) for a in schema.answers],
            # Note: chapter_id is set automatically via the relationship backref
        )

    def _create_answer(self, schema: AnswerSchema) -> Answer:
        """
        Convert an AnswerSchema into a SQLAlchemy Answer model instance.

        :param schema: The AnswerSchema instance to convert.
        :type schema: AnswerSchema
        :return: A SQLAlchemy Answer model instance.
        :rtype: Answer
        """
        return Answer(
            id=schema.id,
            answer=schema.answer,
            is_correct_answer=schema.is_correct_answer,
            explanation=schema.explanation,
            # Note: question_id is set automatically via the relationship backref
        )
