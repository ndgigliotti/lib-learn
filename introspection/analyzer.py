"""LibraryAnalyzer for discovering and analyzing library components."""

import re
import logging
import inspect
import pydoc
from typing import List, Tuple, Optional

from introspection.component import LibraryComponent

WHITESPACE = " \t\n\r\f\v"
logger = logging.getLogger(__name__)


def _get_path(parent, child) -> str:
    """Return the dotted path of `child` relative to its parent class or module."""
    return f"{parent.__name__}.{child.__name__}"


def _shorten(doc: str) -> str:
    """Return the first paragraph of `doc`."""
    doc = doc.strip(WHITESPACE)
    return doc.split("\n\n")[0]


def _sig_fallback(obj, parent, doc: str) -> Tuple[str, str]:
    """
    Look for the signature in the synopsis line.

    Check if the synopsis line is a signature and extract it if so. Ensure that
    the extracted signature has the `self` parameter if `parent` is a class.

    Args:
        obj: Routine in need of signature.
        parent: Parent class or module of `obj`.
        doc: Docstring of `obj`.

    Returns:
        Tuple of (signature, docstring)
    """
    path = _get_path(parent, obj)
    syn, rem = pydoc.splitdoc(doc)
    match = re.match(r"([\w\.]+)\((.*)\)", syn)
    if match:
        sig = match[2]
        if inspect.isclass(parent):
            if sig and not sig.startswith("self"):
                sig = f"self, {sig}"
            elif not sig.startswith("self"):
                sig = "self"
        sig = f"({sig})"
        logger.debug("Found signature for `%s` using fallback.", path)
        return (sig, rem)
    else:
        doc = "\n".join((syn, rem)).strip(WHITESPACE)
        logger.debug("Could not find signature for `%s`.", path)
        return ("(...)", doc)


def _get_doc(obj, parent) -> Tuple[str, str]:
    """
    Get the signature and docstring of the given object.

    Args:
        obj: Function, method, methoddescriptor, or builtin.
        parent: Parent class or module of `obj`.

    Returns:
        Tuple of (signature, docstring)
    """
    doc = pydoc.getdoc(obj).strip(WHITESPACE)
    path = _get_path(parent, obj)
    try:
        sig = str(inspect.signature(obj))
        logger.debug("Found signature for `%s` using inspect.", path)
        return (sig, doc)
    except ValueError:
        return _sig_fallback(obj, parent, doc)


def _is_special(obj) -> bool:
    """Return True if obj is a __special__ method."""
    return obj.__name__.startswith("__") and obj.__name__.endswith("__")


def _is_private(obj) -> bool:
    """Return True if obj is a _private method (but not special)."""
    return obj.__name__.startswith("_") and not _is_special(obj)


def _is_deprecated(obj) -> bool:
    """Return True if obj appears to be deprecated."""
    short, _ = pydoc.splitdoc(pydoc.getdoc(obj))
    return "deprecated" in short.lower()


def _compute_doc_quality(docstring: str, signature: str) -> float:
    """
    Compute a documentation quality score from 0.0 to 1.0.

    Factors:
    - Has any docstring
    - Docstring length
    - Has a complete signature (not ...)
    - Has examples in docstring
    """
    if not docstring:
        return 0.0

    score = 0.0

    # Base score for having documentation
    score += 0.3

    # Length bonus (up to 0.2)
    length_score = min(len(docstring) / 500, 1.0) * 0.2
    score += length_score

    # Complete signature bonus
    if signature != "(...)":
        score += 0.2

    # Has examples bonus
    if ">>>" in docstring or "Example" in docstring:
        score += 0.2

    # Has parameter documentation
    if "Args:" in docstring or "Parameters" in docstring or ":param" in docstring:
        score += 0.1

    return min(score, 1.0)


class LibraryAnalyzer:
    """
    Analyzes a library module or class to discover its components.

    This is a refactored version of the flashcards.create_deck() function,
    returning structured LibraryComponent objects instead of a simple dict.
    """

    def __init__(
        self,
        include_private: bool = False,
        include_special: bool = False,
        include_deprecated: bool = False,
    ):
        """
        Initialize the analyzer.

        Args:
            include_private: Include _private methods
            include_special: Include __special__ methods
            include_deprecated: Include deprecated methods
        """
        self.include_private = include_private
        self.include_special = include_special
        self.include_deprecated = include_deprecated

    def analyze(self, path: str) -> List[LibraryComponent]:
        """
        Analyze a module or class and return its components.

        Args:
            path: Dotted path to the module or class (e.g., "pandas.DataFrame")

        Returns:
            List of LibraryComponent objects

        Raises:
            TypeError: If path resolves to something other than a class or module
            ImportError: If the path cannot be resolved
        """
        logger.debug("Analyzing: `%s`", path)

        obj, _ = pydoc.resolve(path)
        if not (inspect.isclass(obj) or inspect.ismodule(obj)):
            raise TypeError("target must be class or module")

        components = []
        parent_path = path

        # Get all routines (functions, methods)
        routines = inspect.getmembers(obj, inspect.isroutine)

        for name, routine in routines:
            # Apply filters
            if not self.include_special and _is_special(routine):
                continue
            if not self.include_private and _is_private(routine):
                continue

            is_deprecated = _is_deprecated(routine)
            if not self.include_deprecated and is_deprecated:
                continue

            # Extract signature and docstring
            signature, docstring = _get_doc(routine, obj)

            # Determine component type
            if inspect.ismethod(routine):
                component_type = "method"
            elif inspect.isfunction(routine):
                component_type = "function"
            else:
                component_type = "builtin"

            # Create component
            component = LibraryComponent(
                name=name,
                qualified_path=f"{path}.{name}",
                signature=signature,
                docstring=docstring,
                synopsis=_shorten(docstring) if docstring else "",
                component_type=component_type,
                is_public=not name.startswith("_"),
                is_deprecated=is_deprecated,
                documentation_quality=_compute_doc_quality(docstring, signature),
                parent_path=parent_path,
            )
            components.append(component)

        logger.debug(
            "Found %d components in `%s`",
            len(components),
            path,
        )

        # Sort alphabetically by name
        components.sort(key=lambda c: c.name)

        return components

    def get_component(self, qualified_path: str) -> Optional[LibraryComponent]:
        """
        Get a single component by its full qualified path.

        Args:
            qualified_path: Full path like "pandas.DataFrame.merge"

        Returns:
            LibraryComponent if found, None otherwise
        """
        # Split off the last part as the component name
        parts = qualified_path.rsplit(".", 1)
        if len(parts) != 2:
            return None

        parent_path, name = parts

        try:
            components = self.analyze(parent_path)
            for component in components:
                if component.name == name:
                    return component
        except (TypeError, ImportError):
            pass

        return None

    def get_quality_stats(self, components: List[LibraryComponent]) -> dict:
        """
        Get documentation quality statistics for a list of components.

        Args:
            components: List of LibraryComponent objects

        Returns:
            Dict with quality statistics
        """
        if not components:
            return {"total": 0, "documented": 0, "quality_pct": 0.0}

        documented = sum(1 for c in components if c.has_documentation)
        avg_quality = sum(c.documentation_quality for c in components) / len(components)

        return {
            "total": len(components),
            "documented": documented,
            "documented_pct": (documented / len(components)) * 100,
            "avg_quality": avg_quality,
        }
