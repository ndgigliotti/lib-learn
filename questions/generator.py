"""Question generation orchestrator."""

import logging
import random
from typing import List, Dict, Optional

from agents.base import BaseAgent
from introspection.component import LibraryComponent, RankedComponent
from questions.base import Question, QuestionType, QuestionGenerator
from questions.types.write_syntax import WriteSyntaxGenerator
from questions.types.fill_blank import FillBlankGenerator
from questions.types.predict_output import PredictOutputGenerator
from questions.types.fix_buggy import FixBuggyGenerator

logger = logging.getLogger(__name__)


class QuestionOrchestrator:
    """
    Coordinates question generation across different types.

    Ensures variety in question types and balanced coverage of components.
    """

    def __init__(self, agent: BaseAgent):
        """
        Initialize the orchestrator with all question generators.

        Args:
            agent: LLM agent for generating questions
        """
        self.agent = agent
        self.generators: Dict[QuestionType, QuestionGenerator] = {
            QuestionType.WRITE_SYNTAX: WriteSyntaxGenerator(agent),
            QuestionType.FILL_BLANK: FillBlankGenerator(agent),
            QuestionType.PREDICT_OUTPUT: PredictOutputGenerator(agent),
            QuestionType.FIX_BUGGY: FixBuggyGenerator(agent),
        }

        # Track which components have been used to avoid repetition
        self._used_components: set = set()

    def generate_question(
        self,
        component: LibraryComponent,
        preferred_type: Optional[QuestionType] = None,
    ) -> Optional[Question]:
        """
        Generate a single question for the given component.

        Args:
            component: The component to generate a question about
            preferred_type: Optional preferred question type

        Returns:
            A Question object, or None if no question could be generated
        """
        # Try preferred type first if specified
        if preferred_type:
            generator = self.generators.get(preferred_type)
            if generator and generator.can_generate(component):
                try:
                    return generator.generate(component)
                except Exception as e:
                    logger.warning(
                        "Failed to generate %s question: %s",
                        preferred_type.value,
                        str(e),
                    )

        # Try other types in random order
        types = list(QuestionType)
        random.shuffle(types)

        for qtype in types:
            if qtype == preferred_type:
                continue  # Already tried

            generator = self.generators.get(qtype)
            if generator and generator.can_generate(component):
                try:
                    return generator.generate(component)
                except Exception as e:
                    logger.warning(
                        "Failed to generate %s question: %s",
                        qtype.value,
                        str(e),
                    )

        logger.warning(
            "Could not generate any question for %s", component.qualified_path
        )
        return None

    def generate_session(
        self,
        components: List[RankedComponent],
        n_questions: int = 10,
        balance_types: bool = True,
    ) -> List[Question]:
        """
        Generate a balanced set of questions for a learning session.

        Args:
            components: Ranked components to generate questions from
            n_questions: Number of questions to generate
            balance_types: If True, try to use all question types evenly

        Returns:
            List of Question objects
        """
        questions = []
        self._used_components.clear()

        if balance_types:
            # Determine target count per question type
            types = list(QuestionType)
            type_counts = {t: 0 for t in types}
            target_per_type = max(1, n_questions // len(types))

        # Sample components, prioritizing higher-ranked ones
        component_pool = [rc.component for rc in components]

        for _ in range(n_questions * 2):  # Try extra iterations in case of failures
            if len(questions) >= n_questions:
                break

            # Select a component (weighted by position in ranked list)
            available = [
                c
                for c in component_pool
                if c.qualified_path not in self._used_components
            ]

            if not available:
                # All components used, reset
                self._used_components.clear()
                available = component_pool

            # Weight selection toward earlier (higher-ranked) components
            weights = [1.0 / (i + 1) for i in range(len(available))]
            component = random.choices(available, weights=weights[: len(available)])[0]

            # Choose question type
            if balance_types:
                # Find types that are under their target
                under_target = [
                    t
                    for t in types
                    if type_counts[t] < target_per_type
                    and self.generators[t].can_generate(component)
                ]
                if under_target:
                    preferred_type = random.choice(under_target)
                else:
                    preferred_type = None
            else:
                preferred_type = None

            # Generate the question
            question = self.generate_question(component, preferred_type)

            if question:
                questions.append(question)
                self._used_components.add(component.qualified_path)

                if balance_types:
                    type_counts[question.type] += 1

        logger.info(
            "Generated %d questions (requested %d)",
            len(questions),
            n_questions,
        )

        return questions

    def get_applicable_types(
        self,
        component: LibraryComponent,
    ) -> List[QuestionType]:
        """
        Get the list of question types that can be generated for a component.

        Args:
            component: The component to check

        Returns:
            List of applicable QuestionType values
        """
        return [
            qtype
            for qtype, generator in self.generators.items()
            if generator.can_generate(component)
        ]
