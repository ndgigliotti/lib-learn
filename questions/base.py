"""Base classes for question generation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from introspection.component import LibraryComponent


class QuestionType(Enum):
    """Types of questions that can be generated."""

    WRITE_SYNTAX = "write_syntax"
    FILL_BLANK = "fill_blank"
    PREDICT_OUTPUT = "predict_output"
    FIX_BUGGY = "fix_buggy"


@dataclass
class Question:
    """
    Represents a single learning question.

    Attributes:
        type: The type of question
        component: The library component this question is about
        prompt: The question text to show the user
        expected_answer: The correct answer
        hints: Progressive hints (easier hints first)
        difficulty: Difficulty level 1-5
        setup_code: Code to run before evaluating the user's answer
        validation_code: Optional code to validate the answer
        explanation: Explanation of the correct answer
    """

    type: QuestionType
    component: LibraryComponent
    prompt: str
    expected_answer: str
    hints: List[str] = field(default_factory=list)
    difficulty: int = 3
    setup_code: Optional[str] = None
    validation_code: Optional[str] = None
    explanation: str = ""

    def get_hint(self, index: int) -> Optional[str]:
        """
        Get a hint by index.

        Args:
            index: Zero-based hint index

        Returns:
            The hint string, or None if index is out of range
        """
        if 0 <= index < len(self.hints):
            return self.hints[index]
        return None

    @property
    def num_hints(self) -> int:
        """Return the number of available hints."""
        return len(self.hints)


class QuestionGenerator(ABC):
    """Abstract base class for question type generators."""

    @property
    @abstractmethod
    def question_type(self) -> QuestionType:
        """Return the type of question this generator creates."""
        pass

    @abstractmethod
    def generate(self, component: LibraryComponent) -> Question:
        """
        Generate a question for the given component.

        Args:
            component: The library component to create a question about

        Returns:
            A Question object

        Raises:
            ValueError: If a question cannot be generated for this component
        """
        pass

    @abstractmethod
    def can_generate(self, component: LibraryComponent) -> bool:
        """
        Check if this generator can create a question for this component.

        Args:
            component: The component to check

        Returns:
            True if a question can be generated
        """
        pass
