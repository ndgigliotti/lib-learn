"""LibraryComponent dataclass for representing discoverable library components."""

from dataclasses import dataclass


@dataclass
class LibraryComponent:
    """
    Represents a discoverable library component (function, method, or class).

    Attributes:
        name: Short name of the component (e.g., "merge")
        qualified_path: Full dotted path (e.g., "pandas.DataFrame.merge")
        signature: Parameter signature (e.g., "(self, right, how='inner', ...)")
        docstring: Full docstring
        synopsis: First paragraph of docstring
        component_type: Type of component ("function", "method", "class")
        is_public: True if this is a public API
        is_deprecated: True if marked as deprecated
        documentation_quality: Score from 0.0-1.0 based on doc completeness
        parent_path: Path to the parent module/class
    """

    name: str
    qualified_path: str
    signature: str
    docstring: str
    synopsis: str
    component_type: str
    is_public: bool
    is_deprecated: bool
    documentation_quality: float = 0.0
    parent_path: str = ""

    @property
    def full_signature(self) -> str:
        """Return the qualified path with signature."""
        return f"{self.qualified_path}{self.signature}"

    @property
    def has_documentation(self) -> bool:
        """Return True if the component has a non-empty docstring."""
        return bool(self.docstring and self.docstring.strip())

    def __str__(self) -> str:
        return self.full_signature

    def __repr__(self) -> str:
        return f"LibraryComponent({self.qualified_path!r})"


@dataclass
class RankedComponent:
    """
    A LibraryComponent with computed importance ranking.

    Attributes:
        component: The underlying LibraryComponent
        heuristic_score: Score from usage heuristics (0.0-1.0)
        llm_score: Score from LLM analysis (0.0-1.0)
        combined_score: Weighted combination of scores
        explanation: LLM's reasoning for the ranking
    """

    component: LibraryComponent
    heuristic_score: float = 0.0
    llm_score: float = 0.0
    combined_score: float = 0.0
    explanation: str = ""

    def compute_combined_score(self, heuristic_weight: float = 0.4) -> float:
        """
        Compute combined score from heuristic and LLM scores.

        Args:
            heuristic_weight: Weight for heuristic score (LLM gets 1 - this)

        Returns:
            Combined score between 0.0 and 1.0
        """
        llm_weight = 1.0 - heuristic_weight
        self.combined_score = (
            self.heuristic_score * heuristic_weight + self.llm_score * llm_weight
        )
        return self.combined_score

    def __lt__(self, other: "RankedComponent") -> bool:
        """Allow sorting by combined_score (descending)."""
        return self.combined_score > other.combined_score

    def __str__(self) -> str:
        return f"{self.component.qualified_path} (score: {self.combined_score:.2f})"
