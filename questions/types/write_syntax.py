"""Write syntax from scratch question generator."""

import logging

from agents.base import BaseAgent
from introspection.component import LibraryComponent
from questions.base import Question, QuestionType, QuestionGenerator
from questions.prompts import SYSTEM_PROMPT_QUESTION_GEN, USER_PROMPT_WRITE_SYNTAX

logger = logging.getLogger(__name__)


class WriteSyntaxGenerator(QuestionGenerator):
    """
    Generates "write code from scratch" questions.

    Example: "Write code to create a DataFrame from this dict: {'a': [1,2], 'b': [3,4]}"
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
        return QuestionType.WRITE_SYNTAX

    def can_generate(self, component: LibraryComponent) -> bool:
        """
        Check if we can generate a question for this component.

        Write syntax questions work best for:
        - Functions/methods with clear purposes
        - Components with good documentation
        - Not deprecated components
        """
        if component.is_deprecated:
            return False
        if not component.has_documentation:
            return False
        if component.signature == "(...)":
            return False
        return True

    def generate(self, component: LibraryComponent) -> Question:
        """
        Generate a write syntax question using LLM.

        Args:
            component: The library component to create a question about

        Returns:
            A Question object
        """
        library = component.parent_path.split(".")[0]
        system_prompt = SYSTEM_PROMPT_QUESTION_GEN.format(library=library)

        user_prompt = USER_PROMPT_WRITE_SYNTAX.format(
            qualified_path=component.qualified_path,
            signature=component.signature,
            synopsis=component.synopsis,
            docstring=component.docstring[:1000],  # Truncate long docstrings
        )

        messages = self.agent._build_messages(system_prompt, user_prompt)

        try:
            response = self.agent._call_llm_json(messages)

            return Question(
                type=self.question_type,
                component=component,
                prompt=response.get("prompt", f"Write code using {component.name}"),
                expected_answer=response.get("expected_code", ""),
                hints=response.get("hints", []),
                difficulty=response.get("difficulty", 3),
                setup_code=response.get("setup_code"),
                explanation=response.get("explanation", ""),
            )

        except Exception as e:
            logger.warning("Failed to generate write_syntax question: %s", str(e))
            # Return a basic fallback question
            return self._fallback_question(component)

    def _fallback_question(self, component: LibraryComponent) -> Question:
        """Generate a basic fallback question without LLM."""
        return Question(
            type=self.question_type,
            component=component,
            prompt=f"Write code that uses {component.qualified_path}. {component.synopsis}",
            expected_answer=f"# Use {component.name}{component.signature}",
            hints=[
                f"The function signature is: {component.signature}",
                component.synopsis,
            ],
            difficulty=3,
            explanation=component.synopsis,
        )
