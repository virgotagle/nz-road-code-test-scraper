# -*- coding: utf-8 -*-
"""
Defines Pydantic models for data validation and structuring.

These schemas represent the expected structure of the data extracted from the
Road Code test pages (chapters, questions, answers) and are used for parsing,
validation, and potentially serialization (though SQLAlchemy models handle DB).
Pydantic ensures data conforms to expected types and structures.
"""

from typing import List, Optional

from pydantic import BaseModel, RootModel  # Import Pydantic core components


class AnswerSchema(BaseModel):
    """
    Pydantic schema representing a single answer option for a question.

    Used to validate the structure of answer data extracted or prepared for insertion.
    """

    id: int  # Unique identifier for the answer
    answer: str  # The text content of the answer
    is_correct_answer: bool = False  # Flag indicating if this is the correct answer (defaults to False)
    explanation: Optional[str] = None  # Explanation text (optional, added later)

    # Pydantic automatically handles basic type validation (e.g., id is int, answer is str)


class QuestionSchema(BaseModel):
    """
    Pydantic schema representing a single Road Code test question.

    Includes nested validation for a list of AnswerSchema objects.
    """

    id: int  # Unique identifier for the question
    question: str  # The text of the question
    image_url: Optional[str] = None  # URL of an associated image (optional)
    image_base64: Optional[str] = None  # Base64 encoded image data (optional)
    answers: List[AnswerSchema]  # A list containing AnswerSchema objects

    # Pydantic will validate that 'answers' is a list and each item conforms to AnswerSchema


class ChapterSchema(BaseModel):
    """
    Pydantic schema representing a chapter or section of the Road Code test.

    Includes nested validation for a list of QuestionSchema objects.
    """

    id: int  # Unique identifier for the chapter
    title: str  # Title of the chapter/test
    intro: str  # Introductory text for the chapter
    questions: List[QuestionSchema]  # A list containing QuestionSchema objects

    # Pydantic will validate that 'questions' is a list and each item conforms to QuestionSchema


class RoadCodeTestSchema(RootModel):
    """
    Pydantic root model potentially representing the entire collection of chapters.

    Useful if the entire scraped data needs to be validated as a single list structure.
    """

    # Defines the root of the model as a list of ChapterSchema objects
    root: List[ChapterSchema]

    # Example Usage (not typically done in this file):
    # raw_data = [{"id": 1, "title": "...", "intro": "...", "questions": [...]}, ...]
    # validated_data = RoadCodeTestSchema(raw_data)
    # chapters_list = validated_data.root
