"""Session state management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time

from introspection.component import RankedComponent
from questions.base import Question
from execution.validator import ValidationResult


class SessionMode(Enum):
    """Current mode of the learning session."""

    LEARNING = "learning"  # Normal question/answer flow
    REPL = "repl"  # User is in REPL mode
    REVIEW = "review"  # Reviewing past answers


@dataclass
class AnswerRecord:
    """Record of a single question attempt."""

    question: Question
    user_answer: str
    result: ValidationResult
    time_taken: float  # seconds
    hints_used: int

    @property
    def is_correct(self) -> bool:
        return self.result.is_correct


@dataclass
class SessionState:
    """
    Mutable state for an active learning session.

    Tracks the current progress through a learning session.
    """

    library_path: str
    mode: SessionMode = SessionMode.LEARNING

    # Components discovered in this session
    ranked_components: List[RankedComponent] = field(default_factory=list)

    # Question tracking
    questions: List[Question] = field(default_factory=list)
    current_question_index: int = 0
    current_hint_index: int = 0

    # Answer history
    answers: List[AnswerRecord] = field(default_factory=list)

    # REPL history
    repl_history: List[str] = field(default_factory=list)

    # Timing
    session_start_time: float = field(default_factory=time.time)
    question_start_time: Optional[float] = None

    @property
    def current_question(self) -> Optional[Question]:
        """Get the current question, if any."""
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None

    @property
    def questions_answered(self) -> int:
        """Number of questions answered so far."""
        return len(self.answers)

    @property
    def questions_correct(self) -> int:
        """Number of questions answered correctly."""
        return sum(1 for a in self.answers if a.is_correct)

    @property
    def score_percentage(self) -> float:
        """Current score as a percentage."""
        if not self.answers:
            return 0.0
        return (self.questions_correct / len(self.answers)) * 100

    @property
    def session_duration(self) -> float:
        """Duration of the session in seconds."""
        return time.time() - self.session_start_time

    @property
    def is_complete(self) -> bool:
        """Check if all questions have been answered."""
        return self.current_question_index >= len(self.questions)

    def start_question(self):
        """Mark the start of answering a question."""
        self.question_start_time = time.time()
        self.current_hint_index = 0

    def get_next_hint(self) -> Optional[str]:
        """Get the next hint for the current question."""
        question = self.current_question
        if not question:
            return None

        hint = question.get_hint(self.current_hint_index)
        if hint:
            self.current_hint_index += 1
        return hint

    def record_answer(
        self,
        user_answer: str,
        result: ValidationResult,
    ) -> AnswerRecord:
        """Record an answer and advance to the next question."""
        question = self.current_question
        if not question:
            raise ValueError("No current question")

        time_taken = 0.0
        if self.question_start_time:
            time_taken = time.time() - self.question_start_time

        record = AnswerRecord(
            question=question,
            user_answer=user_answer,
            result=result,
            time_taken=time_taken,
            hints_used=self.current_hint_index,
        )

        self.answers.append(record)
        self.current_question_index += 1
        self.question_start_time = None

        return record

    def get_summary(self) -> dict:
        """Get a summary of the session."""
        return {
            "library": self.library_path,
            "total_questions": len(self.questions),
            "questions_answered": self.questions_answered,
            "questions_correct": self.questions_correct,
            "score_percentage": round(self.score_percentage, 1),
            "session_duration": round(self.session_duration, 1),
            "hints_used": sum(a.hints_used for a in self.answers),
        }
