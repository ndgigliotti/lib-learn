"""Predict output question generator."""

import logging

from agents.base import BaseAgent
from introspection.component import LibraryComponent
from questions.base import Question, QuestionType, QuestionGenerator
from questions.prompts import SYSTEM_PROMPT_QUESTION_GEN, USER_PROMPT_PREDICT_OUTPUT

logger = logging.getLogger(__name__)


class PredictOutputGenerator(QuestionGenerator):
    """
    Generates "predict the output" questions.

    Example: "What does this code return? df.shape"
    """

    def __init__(self, agent: BaseAgent):
        """
        Initialize the generator.

        Args:
            agent: LLM agent for generating questions
        """
        self.agent = agent

    @property
    def question_type(self) -> QuestionType:
        return QuestionType.PREDICT_OUTPUT

    def can_generate(self, component: LibraryComponent) -> bool:
        """
        Check if we can generate a question for this component.

        Predict output works best for:
        - Functions with deterministic outputs
        - Not void/None-returning functions
        - Well-documented functions
        """
        if component.is_deprecated:
            return False
        if not component.has_documentation:
            return False

        # Check if it likely returns something
        docstring = component.docstring.lower()
        if "return" in docstring or "returns" in docstring:
            return True

        # Properties and getters are good candidates
        if component.name.startswith("get") or component.name.startswith("is_"):
            return True

        return True  # Default to allowing

    def generate(self, component: LibraryComponent) -> Question:
        """
        Generate a predict output question using LLM.

        Args:
            component: The library component to create a question about

        Returns:
            A Question object
        """
        library = component.parent_path.split(".")[0]
        system_prompt = SYSTEM_PROMPT_QUESTION_GEN.format(library=library)

        user_prompt = USER_PROMPT_PREDICT_OUTPUT.format(
            qualified_path=component.qualified_path,
            signature=component.signature,
            synopsis=component.synopsis,
        )

        messages = self.agent._build_messages(system_prompt, user_prompt)

        try:
            response = self.agent._call_llm_json(messages)

            code = response.get("code", "")
            prompt = f"What does this code output?\n```python\n{code}\n```"

            return Question(
                type=self.question_type,
                component=component,
                prompt=prompt,
                expected_answer=response.get("expected_output", ""),
                hints=response.get("hints", []),
                difficulty=response.get("difficulty", 2),
                setup_code=response.get("setup_code"),
                validation_code=code,
                explanation=response.get("explanation", ""),
            )

        except Exception as e:
            logger.warning("Failed to generate predict_output question: %s", str(e))
            return self._fallback_question(component)

    def _fallback_question(self, component: LibraryComponent) -> Question:
        """Generate a basic fallback question without LLM."""
        return Question(
            type=self.question_type,
            component=component,
            prompt=f"What would calling {component.qualified_path} typically return or do?\n\n{component.synopsis}",
            expected_answer="See documentation",
            hints=[component.synopsis],
            difficulty=2,
            explanation=component.synopsis,
        )
