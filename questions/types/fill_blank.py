"""Fill-in-the-blank question generator."""

import logging

from agents.base import BaseAgent
from introspection.component import LibraryComponent
from questions.base import Question, QuestionType, QuestionGenerator
from questions.prompts import SYSTEM_PROMPT_QUESTION_GEN, USER_PROMPT_FILL_BLANK

logger = logging.getLogger(__name__)


class FillBlankGenerator(QuestionGenerator):
    """
    Generates fill-in-the-blank questions.

    Example: "Complete: df.___(axis=1) to drop columns"
    The user must fill in "drop"
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
        return QuestionType.FILL_BLANK

    def can_generate(self, component: LibraryComponent) -> bool:
        """
        Check if we can generate a question for this component.

        Fill-in-the-blank works best for:
        - Methods with clear purposes
        - Names that aren't too long or obscure
        """
        if component.is_deprecated:
            return False
        if not component.has_documentation:
            return False
        # Very short names might be too easy to guess
        if len(component.name) < 3:
            return False
        # Very long names might be frustrating
        if len(component.name) > 25:
            return False
        return True

    def generate(self, component: LibraryComponent) -> Question:
        """
        Generate a fill-in-the-blank question using LLM.

        Args:
            component: The library component to create a question about

        Returns:
            A Question object
        """
        library = component.parent_path.split(".")[0]
        system_prompt = SYSTEM_PROMPT_QUESTION_GEN.format(library=library)

        user_prompt = USER_PROMPT_FILL_BLANK.format(
            qualified_path=component.qualified_path,
            signature=component.signature,
            synopsis=component.synopsis,
        )

        messages = self.agent._build_messages(system_prompt, user_prompt)

        try:
            response = self.agent._call_llm_json(messages)

            # Build the prompt with the code block
            code_with_blank = response.get("code_with_blank", "obj.___")
            prompt = response.get(
                "prompt", f"Complete the code:\n```python\n{code_with_blank}\n```"
            )

            return Question(
                type=self.question_type,
                component=component,
                prompt=prompt,
                expected_answer=response.get("answer", component.name),
                hints=response.get("hints", []),
                difficulty=response.get("difficulty", 2),
                setup_code=response.get("setup_code"),
                validation_code=response.get("full_code"),
                explanation=response.get("explanation", ""),
            )

        except Exception as e:
            logger.warning("Failed to generate fill_blank question: %s", str(e))
            return self._fallback_question(component)

    def _fallback_question(self, component: LibraryComponent) -> Question:
        """Generate a basic fallback question without LLM."""
        # Create a simple fill-in-the-blank
        parent = component.parent_path.split(".")[-1]
        code = f"{parent.lower()}.___()"

        return Question(
            type=self.question_type,
            component=component,
            prompt=f"Fill in the blank to {component.synopsis.lower()}:\n```python\n{code}\n```",
            expected_answer=component.name,
            hints=[
                f"The method starts with '{component.name[0]}'",
                f"It has {len(component.name)} characters",
            ],
            difficulty=2,
            explanation=component.synopsis,
        )
