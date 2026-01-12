"""ExplorerAgent for library exploration and component ranking."""

import logging
from typing import List

from config import LLMConfig
from agents.base import BaseAgent
from agents.prompts import SYSTEM_PROMPT_EXPLORER, USER_PROMPT_EXPLORER_RANK
from introspection.component import LibraryComponent, RankedComponent

logger = logging.getLogger(__name__)


class ExplorerAgent(BaseAgent):
    """
    Agent that explores a library to find its most important components.

    Combines heuristic scoring (public, documented, not deprecated) with
    LLM analysis to rank components by educational value.
    """

    def __init__(self, config: LLMConfig, batch_size: int = 20):
        """
        Initialize the ExplorerAgent.

        Args:
            config: LLM configuration
            batch_size: Number of components to send to LLM at once
        """
        super().__init__(config)
        self.batch_size = batch_size

    def explore(
        self,
        components: List[LibraryComponent],
        n_top: int = 20,
        heuristic_weight: float = 0.4,
    ) -> List[RankedComponent]:
        """
        Analyze and rank library components by learning value.

        Strategy:
        1. Compute heuristic scores for all components
        2. Filter to top candidates by heuristic score
        3. Batch components and ask LLM to rank by importance
        4. Combine heuristic + LLM scores
        5. Return top N ranked components

        Args:
            components: List of LibraryComponent objects to analyze
            n_top: Number of top components to return
            heuristic_weight: Weight for heuristic score (LLM gets 1 - this)

        Returns:
            List of RankedComponent objects, sorted by combined score
        """
        logger.info("Exploring %d components", len(components))

        # Step 1: Compute heuristic scores
        ranked = []
        for component in components:
            score = self._compute_heuristic_score(component)
            ranked.append(
                RankedComponent(
                    component=component,
                    heuristic_score=score,
                )
            )

        # Step 2: Sort by heuristic and take top candidates for LLM analysis
        ranked.sort(key=lambda r: r.heuristic_score, reverse=True)

        # Take more than n_top for LLM to have room to reorder
        n_candidates = min(len(ranked), n_top * 2)
        candidates = ranked[:n_candidates]

        # Step 3: Get LLM rankings in batches
        library_path = components[0].parent_path if components else "unknown"
        llm_scores = self._llm_rank_all(candidates, library_path)

        # Step 4: Apply LLM scores and compute combined scores
        for i, rc in enumerate(candidates):
            if i < len(llm_scores):
                rc.llm_score = llm_scores[i]["score"]
                rc.explanation = llm_scores[i].get("reason", "")
            rc.compute_combined_score(heuristic_weight)

        # Step 5: Re-sort by combined score and return top N
        candidates.sort()
        result = candidates[:n_top]

        logger.info("Selected top %d components", len(result))
        return result

    def _compute_heuristic_score(self, component: LibraryComponent) -> float:
        """
        Compute a heuristic importance score for a component.

        Factors:
        - Public API (higher) vs private
        - Has good documentation
        - Not deprecated
        - Reasonable complexity (not too simple, not too complex)
        - Has a complete signature

        Args:
            component: The component to score

        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0

        # Public API bonus
        if component.is_public:
            score += 0.3

        # Documentation quality
        score += component.documentation_quality * 0.3

        # Not deprecated
        if not component.is_deprecated:
            score += 0.1

        # Has complete signature (not ...)
        if component.signature != "(...)":
            score += 0.1

        # Reasonable name length (not too short like 'x', not too long)
        name_len = len(component.name)
        if 3 <= name_len <= 20:
            score += 0.1

        # Has docstring
        if component.has_documentation:
            score += 0.1

        return min(score, 1.0)

    def _llm_rank_all(
        self,
        candidates: List[RankedComponent],
        library_path: str,
    ) -> List[dict]:
        """
        Get LLM rankings for all candidates, processing in batches.

        Args:
            candidates: Components to rank
            library_path: Path to the library being explored

        Returns:
            List of dicts with 'score' and 'reason' keys
        """
        all_scores = []

        for i in range(0, len(candidates), self.batch_size):
            batch = candidates[i : i + self.batch_size]
            batch_scores = self._llm_rank_batch(batch, library_path)
            all_scores.extend(batch_scores)

        return all_scores

    def _llm_rank_batch(
        self,
        batch: List[RankedComponent],
        library_path: str,
    ) -> List[dict]:
        """
        Ask LLM to rank a batch of components by educational value.

        Args:
            batch: Batch of components to rank
            library_path: Path to the library

        Returns:
            List of dicts with 'score' (normalized 0-1) and 'reason'
        """
        # Format components for the prompt
        components_text = []
        for rc in batch:
            c = rc.component
            text = f"- {c.name}{c.signature}"
            if c.synopsis:
                # Truncate long synopses
                synopsis = (
                    c.synopsis[:200] + "..." if len(c.synopsis) > 200 else c.synopsis
                )
                text += f"\n  {synopsis}"
            components_text.append(text)

        components_formatted = "\n".join(components_text)

        user_prompt = USER_PROMPT_EXPLORER_RANK.format(
            library_path=library_path,
            components_formatted=components_formatted,
        )

        messages = self._build_messages(SYSTEM_PROMPT_EXPLORER, user_prompt)

        try:
            response = self._call_llm_json(messages)
            rankings = response.get("rankings", [])

            # Normalize scores to 0-1 range and match with components
            results = []
            ranking_map = {r["name"]: r for r in rankings}

            for rc in batch:
                name = rc.component.name
                if name in ranking_map:
                    raw_score = ranking_map[name].get("score", 5)
                    normalized = raw_score / 10.0  # Convert 1-10 to 0-1
                    results.append(
                        {
                            "score": normalized,
                            "reason": ranking_map[name].get("reason", ""),
                        }
                    )
                else:
                    # Component not in LLM response, use neutral score
                    results.append({"score": 0.5, "reason": ""})

            return results

        except Exception as e:
            logger.warning("LLM ranking failed: %s", str(e))
            # Return neutral scores on failure
            return [{"score": 0.5, "reason": ""} for _ in batch]

    def explore_without_llm(
        self,
        components: List[LibraryComponent],
        n_top: int = 20,
    ) -> List[RankedComponent]:
        """
        Rank components using only heuristics (no LLM calls).

        Useful for testing or when LLM is not available.

        Args:
            components: List of components to analyze
            n_top: Number of top components to return

        Returns:
            List of RankedComponent objects
        """
        ranked = []
        for component in components:
            score = self._compute_heuristic_score(component)
            ranked.append(
                RankedComponent(
                    component=component,
                    heuristic_score=score,
                    llm_score=0.0,
                    combined_score=score,  # Use heuristic as combined
                )
            )

        ranked.sort(key=lambda r: r.combined_score, reverse=True)
        return ranked[:n_top]
