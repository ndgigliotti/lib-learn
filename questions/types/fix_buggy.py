"""Fix buggy code question generator."""

import logging

from agents.base import BaseAgent
from introspection.component import LibraryComponent
from questions.base import Question, QuestionType, QuestionGenerator
from questions.prompts import SYSTEM_PROMPT_QUESTION_GEN, USER_PROMPT_FIX_BUGGY

logger = logging.getLogger(__name__)


class FixBuggyGenerator(QuestionGenerator):
    """
    Generates bug-fixing questions.

    Example: "This code has an error, fix it: df.mege(other)"
    The user must identify the typo and fix it to "merge"
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
        return QuestionType.FIX_BUGGY

    def can_generate(self, component: LibraryComponent) -> bool:
        """
        Check if we can generate a question for this component.

        Bug-fixing works best for:
        - Functions with parameters (more opportunities for bugs)
        - Functions with common misspellings
        - Well-documented functions
        """
        if component.is_deprecated:
            return False
        if not component.has_documentation:
            return False
        # Need a non-trivial signature for interesting bugs
        if component.signature in ["()", "(self)", "(...)"]:
            return False
        return True

    def generate(self, component: LibraryComponent) -> Question:
        """
        Generate a bug-fixing question using LLM.

        Args:
            component: The library component to create a question about

        Returns:
            A Question object
        """
        library = component.parent_path.split(".")[0]
        system_prompt = SYSTEM_PROMPT_QUESTION_GEN.format(library=library)

        user_prompt = USER_PROMPT_FIX_BUGGY.format(
            qualified_path=component.qualified_path,
            signature=component.signature,
            synopsis=component.synopsis,
        )

        messages = self.agent._build_messages(system_prompt, user_prompt)

        try:
            response = self.agent._call_llm_json(messages)

            buggy_code = response.get("buggy_code", "")
            prompt = f"Fix the bug in this code:\n```python\n{buggy_code}\n```"

            if "bug_description" in response:
                # Don't reveal the bug in the prompt, but save it for explanation
                pass

            return Question(
                type=self.question_type,
                component=component,
                prompt=prompt,
                expected_answer=response.get("correct_code", ""),
                hints=response.get("hints", []),
                difficulty=response.get("difficulty", 3),
                setup_code=response.get("setup_code"),
                validation_code=response.get("correct_code"),
                explanation=response.get(
                    "explanation", response.get("bug_description", "")
                ),
            )

        except Exception as e:
            logger.warning("Failed to generate fix_buggy question: %s", str(e))
            return self._fallback_question(component)

    def _fallback_question(self, component: LibraryComponent) -> Question:
        """Generate a basic fallback question without LLM."""
        # Create a simple typo bug
        name = component.name
        if len(name) > 3:
            # Remove a character to create a typo
            buggy_name = name[: len(name) // 2] + name[len(name) // 2 + 1 :]
        else:
            buggy_name = name + "s"  # Add extra character

        buggy_code = f"obj.{buggy_name}()"
        correct_code = f"obj.{name}()"

        return Question(
            type=self.question_type,
            component=component,
            prompt=f"Fix the bug in this code:\n```python\n{buggy_code}\n```",
            expected_answer=correct_code,
            hints=[
                "There's a typo in the method name",
                f"The correct method is '{name}'",
            ],
            difficulty=2,
            explanation=f"The method name was misspelled. It should be '{name}'.",
        )
