"""Answer validation for code execution."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from agents.base import BaseAgent
from agents.prompts import SYSTEM_PROMPT_VALIDATOR, USER_PROMPT_VALIDATE
from execution.sandbox import CodeSandbox, ExecutionResult
from questions.base import Question, QuestionType

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of answer validation."""

    is_correct: bool
    feedback: str
    expected_output: str
    actual_output: Optional[str]
    partial_credit: float  # 0.0 - 1.0


class AnswerValidator:
    """
    Validates user answers against expected results.

    Uses code execution for code answers, with optional LLM-based
    equivalence checking for ambiguous cases.
    """

    def __init__(self, sandbox: CodeSandbox, agent: Optional[BaseAgent] = None):
        """
        Initialize the validator.

        Args:
            sandbox: Code sandbox for execution
            agent: Optional LLM agent for semantic comparison
        """
        self.sandbox = sandbox
        self.agent = agent

    def validate(self, question: Question, user_answer: str) -> ValidationResult:
        """
        Validate the user's answer.

        Args:
            question: The question being answered
            user_answer: The user's answer

        Returns:
            ValidationResult with feedback
        """
        if question.type == QuestionType.FILL_BLANK:
            return self._validate_fill_blank(question, user_answer)
        elif question.type == QuestionType.PREDICT_OUTPUT:
            return self._validate_predict_output(question, user_answer)
        else:
            return self._validate_code(question, user_answer)

    def _validate_fill_blank(
        self,
        question: Question,
        user_answer: str,
    ) -> ValidationResult:
        """Validate a fill-in-the-blank answer."""
        user_answer = user_answer.strip()
        expected = question.expected_answer.strip()

        # Simple string comparison (case-sensitive)
        is_correct = user_answer == expected

        if is_correct:
            return ValidationResult(
                is_correct=True,
                feedback="Correct!",
                expected_output=expected,
                actual_output=user_answer,
                partial_credit=1.0,
            )
        else:
            # Check for close matches
            partial = self._compute_string_similarity(user_answer, expected)

            if partial > 0.8:
                feedback = f"Close! The correct answer is '{expected}'."
            else:
                feedback = f"Incorrect. The correct answer is '{expected}'."

            return ValidationResult(
                is_correct=False,
                feedback=feedback,
                expected_output=expected,
                actual_output=user_answer,
                partial_credit=partial,
            )

    def _validate_predict_output(
        self,
        question: Question,
        user_answer: str,
    ) -> ValidationResult:
        """Validate a predict-output answer."""
        user_answer = user_answer.strip()
        expected = question.expected_answer.strip()

        # Normalize whitespace and quotes for comparison
        user_normalized = self._normalize_output(user_answer)
        expected_normalized = self._normalize_output(expected)

        if user_normalized == expected_normalized:
            return ValidationResult(
                is_correct=True,
                feedback="Correct!",
                expected_output=expected,
                actual_output=user_answer,
                partial_credit=1.0,
            )

        # Try executing the code to get actual output
        if question.validation_code:
            result = self.sandbox.execute(
                question.validation_code,
                setup_code=question.setup_code,
            )

            if result.success:
                actual = result.stdout.strip() or repr(result.output)
                actual_normalized = self._normalize_output(actual)

                if user_normalized == actual_normalized:
                    return ValidationResult(
                        is_correct=True,
                        feedback="Correct!",
                        expected_output=actual,
                        actual_output=user_answer,
                        partial_credit=1.0,
                    )

        # Check for semantic equivalence with LLM if available
        if self.agent and self._might_be_equivalent(user_answer, expected):
            return self._llm_validate(question, user_answer, expected)

        partial = self._compute_string_similarity(user_normalized, expected_normalized)

        return ValidationResult(
            is_correct=False,
            feedback=f"Incorrect. Expected output:\n{expected}",
            expected_output=expected,
            actual_output=user_answer,
            partial_credit=partial,
        )

    def _validate_code(
        self,
        question: Question,
        user_answer: str,
    ) -> ValidationResult:
        """Validate a code answer by execution."""
        # Execute user's code
        user_result = self.sandbox.execute(
            user_answer,
            setup_code=question.setup_code,
        )

        if not user_result.success:
            return ValidationResult(
                is_correct=False,
                feedback=f"Your code raised an error:\n{user_result.exception}",
                expected_output=question.expected_answer,
                actual_output=None,
                partial_credit=0.0,
            )

        # Execute expected code to get expected output
        expected_result = self.sandbox.execute(
            question.expected_answer,
            setup_code=question.setup_code,
        )

        if not expected_result.success:
            # Expected code failed - this is a problem with the question
            logger.warning(
                "Expected code failed: %s",
                expected_result.exception,
            )
            # Be lenient - if user code ran, give partial credit
            return ValidationResult(
                is_correct=True,
                feedback="Your code ran successfully.",
                expected_output="(expected code error)",
                actual_output=user_result.stdout,
                partial_credit=0.8,
            )

        # Compare outputs
        user_output = self._get_output(user_result)
        expected_output = self._get_output(expected_result)

        if self._outputs_match(user_output, expected_output):
            return ValidationResult(
                is_correct=True,
                feedback="Correct! Your code produces the expected output.",
                expected_output=expected_output,
                actual_output=user_output,
                partial_credit=1.0,
            )

        # Outputs don't match - try LLM validation
        if self.agent:
            return self._llm_validate_code(
                question,
                user_answer,
                user_output,
                expected_output,
            )

        partial = self._compute_string_similarity(user_output, expected_output)

        return ValidationResult(
            is_correct=False,
            feedback=f"Your code ran but produced different output.\n\nExpected:\n{expected_output}\n\nGot:\n{user_output}",
            expected_output=expected_output,
            actual_output=user_output,
            partial_credit=partial,
        )

    def _llm_validate(
        self,
        question: Question,
        user_answer: str,
        expected: str,
    ) -> ValidationResult:
        """Use LLM to validate semantic equivalence."""
        prompt = f"""Compare these two answers:

User's answer: {user_answer}
Expected answer: {expected}

Are they semantically equivalent? Consider:
- Different formatting/whitespace
- Equivalent representations (e.g., '1.0' vs '1')

Respond with JSON: {{"equivalent": true/false, "explanation": "..."}}"""

        try:
            response = self.agent._call_llm_json([{"role": "user", "content": prompt}])

            if response.get("equivalent", False):
                return ValidationResult(
                    is_correct=True,
                    feedback="Correct! (Semantically equivalent)",
                    expected_output=expected,
                    actual_output=user_answer,
                    partial_credit=1.0,
                )
            else:
                return ValidationResult(
                    is_correct=False,
                    feedback=response.get("explanation", f"Expected: {expected}"),
                    expected_output=expected,
                    actual_output=user_answer,
                    partial_credit=0.0,
                )
        except Exception:
            # Fall back to simple comparison
            return ValidationResult(
                is_correct=False,
                feedback=f"Expected: {expected}",
                expected_output=expected,
                actual_output=user_answer,
                partial_credit=0.0,
            )

    def _llm_validate_code(
        self,
        question: Question,
        user_code: str,
        user_output: str,
        expected_output: str,
    ) -> ValidationResult:
        """Use LLM to validate code equivalence."""
        user_prompt = USER_PROMPT_VALIDATE.format(
            question_prompt=question.prompt,
            expected_code=question.expected_answer,
            expected_output=expected_output,
            user_code=user_code,
            actual_output=user_output,
        )

        try:
            messages = self.agent._build_messages(
                SYSTEM_PROMPT_VALIDATOR,
                user_prompt,
            )
            response = self.agent._call_llm_json(messages)

            is_correct = response.get("is_correct", False)
            partial_credit = response.get(
                "partial_credit", 0.0 if not is_correct else 1.0
            )
            feedback = response.get("feedback", "")

            return ValidationResult(
                is_correct=is_correct,
                feedback=feedback,
                expected_output=expected_output,
                actual_output=user_output,
                partial_credit=partial_credit,
            )
        except Exception as e:
            logger.warning("LLM validation failed: %s", str(e))
            return ValidationResult(
                is_correct=False,
                feedback=f"Output mismatch.\nExpected:\n{expected_output}\n\nGot:\n{user_output}",
                expected_output=expected_output,
                actual_output=user_output,
                partial_credit=0.0,
            )

    def _get_output(self, result: ExecutionResult) -> str:
        """Extract output string from execution result."""
        parts = []
        if result.stdout:
            parts.append(result.stdout.rstrip())
        if result.output is not None:
            parts.append(repr(result.output))
        return "\n".join(parts) if parts else ""

    def _outputs_match(self, a: str, b: str) -> bool:
        """Check if two outputs are equivalent."""
        a_norm = self._normalize_output(a)
        b_norm = self._normalize_output(b)
        return a_norm == b_norm

    def _normalize_output(self, s: str) -> str:
        """Normalize output for comparison."""
        # Strip whitespace
        s = s.strip()
        # Normalize quotes
        s = s.replace("'", '"')
        # Normalize float representations
        s = re.sub(r"\.0+\b", ".0", s)
        # Normalize whitespace
        s = " ".join(s.split())
        return s

    def _might_be_equivalent(self, a: str, b: str) -> bool:
        """Check if two strings might be semantically equivalent."""
        # Simple heuristic: if they're very similar in length
        len_diff = abs(len(a) - len(b))
        return len_diff < max(len(a), len(b)) * 0.3

    def _compute_string_similarity(self, a: str, b: str) -> float:
        """Compute a simple string similarity score."""
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0

        # Simple character-level similarity
        matches = sum(1 for c1, c2 in zip(a, b) if c1 == c2)
        return matches / max(len(a), len(b))
