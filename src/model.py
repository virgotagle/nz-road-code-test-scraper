# -*- coding: utf-8 -*-
"""
Defines the SQLAlchemy database models for the NZ Road Code Test data.

These models represent the structure of the database tables (chapters, questions, answers)
and their relationships.
"""


from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text  # Core SQLAlchemy types

# declarative_base is the standard base class for modern SQLAlchemy models
from sqlalchemy.orm import declarative_base, relationship  # ORM components

# Pydantic is used for schema validation, not directly in the model definition here.
# from pydantic import BaseModel # BaseModel is Pydantic, not needed for SQLAlchemy models


# Create a base class for declarative class definitions.
# All model classes will inherit from this base.
Base = declarative_base()


# === SQLAlchemy Models ===


class Answer(Base):
    """
    SQLAlchemy model representing a single answer option for a question.

    Maps to the 'answers' table in the database.
    """

    __tablename__ = "answers"  # The name of the database table

    # Define table columns with their types and constraints
    id = Column(Integer, primary_key=True)  # Primary key, likely auto-incrementing
    answer = Column(String, nullable=False)  # The text content of the answer
    is_correct_answer = Column(Boolean, default=False)  # Flag indicating if this is the correct answer
    explanation = Column(Text, nullable=True)  # Explanation text (often populated after test completion)

    # Foreign key constraint: Links this answer to a question in the 'questions' table
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)

    # Define the relationship back to the Question model.
    # `back_populates` ensures bidirectional relationship management.
    question = relationship("Question", back_populates="answers")


class Question(Base):
    """
    SQLAlchemy model representing a single test question.

    Maps to the 'questions' table in the database.
    """

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)  # Primary key
    question = Column(String, nullable=False)  # The text of the question
    image_url = Column(String, nullable=True)  # URL of an associated image (if any)
    # Store image as base64 string directly in DB (can increase DB size significantly)
    image_base64 = Column(Text, nullable=True)  # Using Text for potentially long base64 strings

    # Foreign key constraint: Links this question to a chapter in the 'chapters' table
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)

    # Define the one-to-many relationship to Answer models.
    # `cascade="all, delete-orphan"` means associated answers are deleted if the question is deleted.
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")
    # Define the relationship back to the Chapter model.
    chapter = relationship("Chapter", back_populates="questions")

    def __repr__(self):
        """Provide a developer-friendly string representation."""
        return f"<Question(id={self.id}, question='{self.question[:30]}...')>"


class Chapter(Base):
    """
    SQLAlchemy model representing a chapter or section of the road code test.

    Maps to the 'chapters' table in the database.
    """

    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True)  # Primary key
    title = Column(String, nullable=False)  # Title of the chapter/test
    intro = Column(Text, nullable=True)  # Introductory text for the chapter (allow NULL)

    # Define the one-to-many relationship to Question models.
    # `cascade="all, delete-orphan"` means associated questions (and their answers) are deleted
    # if the chapter is deleted.
    questions = relationship("Question", back_populates="chapter", cascade="all, delete-orphan")

    def __repr__(self):
        """Provide a developer-friendly string representation."""
        return f"<Chapter(id={self.id}, title='{self.title}')>"


# Example of how to create the engine and schema (usually done in db_helper.py or main script)
# if __name__ == "__main__":
#     from .config import ROAD_CODE_TEST_DB_URL
#     engine = create_engine(ROAD_CODE_TEST_DB_URL)
#     Base.metadata.create_all(engine)
#     print("Database tables created (if they didn't exist).")
