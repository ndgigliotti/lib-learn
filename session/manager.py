"""Session manager for coordinating learning sessions."""

import logging
from typing import Optional

from config import AppConfig
from agents.base import BaseAgent
from agents.explorer import ExplorerAgent
from introspection.analyzer import LibraryAnalyzer
from questions.generator import QuestionOrchestrator
from execution.sandbox import CodeSandbox
from execution.validator import AnswerValidator, ValidationResult
from execution.environment import LibraryEnvironment
from session.state import SessionState, SessionMode

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages the lifecycle of a learning session.

    Coordinates between library analysis, question generation,
    code execution, and the REPL.
    """

    def __init__(self, config: AppConfig, auto_install: bool = False):
        """
        Initialize the session manager.

        Args:
            config: Application configuration
            auto_install: If True, install missing libraries without prompting
        """
        self.config = config
        self.auto_install = auto_install
        self.state: Optional[SessionState] = None

        # Initialize components
        self.environment = LibraryEnvironment()
        self.sandbox = CodeSandbox(config.sandbox)
        self.agent = BaseAgent(config.llm)
        self.explorer = ExplorerAgent(config.llm)
        self.orchestrator = QuestionOrchestrator(self.agent)
        self.validator = AnswerValidator(self.sandbox, self.agent)
        self.analyzer = LibraryAnalyzer()

    def start_session(self, library_path: str) -> SessionState:
        """
        Initialize a new learning session.

        Args:
            library_path: Path to the library to learn (e.g., "pandas.DataFrame")

        Returns:
            Initialized SessionState
        """
        logger.info("Starting session for: %s", library_path)

        # Create session state
        self.state = SessionState(library_path=library_path)

        # Ensure library is available (install in isolated env if needed)
        python_executable = self.environment.ensure_available(
            library_path,
            auto_install=self.auto_install,
        )

        # Configure sandbox for this library
        self.sandbox.set_library(library_path)
        self.sandbox.set_python_executable(python_executable)

        # Analyze the library
        print(f"Analyzing {library_path}...")
        try:
            components = self.analyzer.analyze(library_path)
            print(f"Found {len(components)} components")
        except Exception as e:
            print(f"Error analyzing library: {e}")
            raise

        # Rank components
        print("Identifying important concepts...")
        try:
            ranked = self.explorer.explore(
                components,
                n_top=self.config.session.components_to_rank,
            )
        except Exception as e:
            logger.warning("LLM ranking failed, using heuristics: %s", e)
            ranked = self.explorer.explore_without_llm(
                components,
                n_top=self.config.session.components_to_rank,
            )

        self.state.ranked_components = ranked
        print(f"Selected {len(ranked)} components to learn")

        # Generate questions
        print("Generating questions...")
        questions = self.orchestrator.generate_session(
            ranked,
            n_questions=self.config.session.questions_per_session,
        )
        self.state.questions = questions
        print(f"Generated {len(questions)} questions")

        return self.state

    def interact(self):
        """
        Run the main interaction loop.

        Handles question display, answer input, REPL mode, and commands.
        """
        if not self.state:
            raise RuntimeError("No active session. Call start_session first.")

        print("\n" + "=" * 60)
        print(f"Learning: {self.state.library_path}")
        print(f"Questions: {len(self.state.questions)}")
        print("Commands: /hint, /skip, /repl, /quit")
        print("=" * 60 + "\n")

        while not self.state.is_complete:
            if self.state.mode == SessionMode.REPL:
                self._run_repl()
                continue

            self._show_question()
            answer = self._get_input()

            if answer is None:  # EOF
                break

            result = self._handle_input(answer)
            if result == "quit":
                break

        self._show_summary()

    def _show_question(self):
        """Display the current question."""
        question = self.state.current_question
        if not question:
            return

        self.state.start_question()

        print(
            f"\n--- Question {self.state.current_question_index + 1}/{len(self.state.questions)} ---"
        )
        print(f"[{question.type.value}] {question.component.qualified_path}\n")
        print(question.prompt)
        print()

    def _get_input(self) -> Optional[str]:
        """Get input from the user, handling multi-line code."""
        try:
            lines = []
            prompt = ">>> " if not lines else "... "

            while True:
                line = input(prompt)

                # Check for commands on first line
                if not lines and line.startswith("/"):
                    return line

                lines.append(line)

                # Simple heuristic: if the last line is empty, we're done
                if not line.strip():
                    break

                # If it's a single-line answer, we're done
                if len(lines) == 1 and not line.endswith(":"):
                    break

                prompt = "... "

            return "\n".join(lines).strip()

        except EOFError:
            return None
        except KeyboardInterrupt:
            print("\n(Use /quit to exit)")
            return ""

    def _handle_input(self, answer: str) -> Optional[str]:
        """
        Handle user input, returning a command result if applicable.

        Returns:
            None for normal answers, "quit" to exit, etc.
        """
        if not answer:
            return None

        # Handle commands
        if answer.startswith("/"):
            cmd = answer.split()[0].lower()

            if cmd == "/quit" or cmd == "/q":
                return "quit"

            elif cmd == "/skip" or cmd == "/s":
                self._skip_question()
                return None

            elif cmd == "/hint" or cmd == "/h":
                self._show_hint()
                return None

            elif cmd == "/repl" or cmd == "/r":
                self.state.mode = SessionMode.REPL
                return None

            elif cmd == "/help":
                self._show_help()
                return None

            elif cmd == "/score":
                self._show_score()
                return None

            else:
                print(f"Unknown command: {cmd}")
                return None

        # Validate the answer
        question = self.state.current_question
        if not question:
            return None

        result = self.validator.validate(question, answer)
        self._show_result(result)
        self.state.record_answer(answer, result)

        return None

    def _show_result(self, result: ValidationResult):
        """Display the validation result."""
        print()
        if result.is_correct:
            print("CORRECT!")
        else:
            print("INCORRECT")

        print(result.feedback)

        if not result.is_correct and result.expected_output:
            print(f"\nExpected:\n{result.expected_output}")

        print()

    def _skip_question(self):
        """Skip the current question."""
        question = self.state.current_question
        if question:
            result = ValidationResult(
                is_correct=False,
                feedback="Skipped",
                expected_output=question.expected_answer,
                actual_output=None,
                partial_credit=0.0,
            )
            self.state.record_answer("(skipped)", result)
            print("Question skipped.\n")

    def _show_hint(self):
        """Show the next hint for the current question."""
        if not self.config.session.enable_hints:
            print("Hints are disabled.")
            return

        if self.state.current_hint_index >= self.config.session.max_hints_per_question:
            print("No more hints available.")
            return

        hint = self.state.get_next_hint()
        if hint:
            print(f"Hint {self.state.current_hint_index}: {hint}")
        else:
            print("No hints available for this question.")

    def _show_help(self):
        """Show help information."""
        print("""
Commands:
  /hint, /h    - Get a hint for the current question
  /skip, /s    - Skip the current question
  /repl, /r    - Enter REPL mode to experiment
  /score       - Show current score
  /quit, /q    - End the session
  /help        - Show this help message

In REPL mode:
  /exit        - Return to questions
  /current     - Show current question
  /docs <name> - Show documentation
""")

    def _show_score(self):
        """Show the current score."""
        summary = self.state.get_summary()
        print(
            f"\nScore: {summary['questions_correct']}/{summary['questions_answered']} ({summary['score_percentage']}%)"
        )

    def _run_repl(self):
        """Run the REPL mode."""
        from session.repl import InteractiveREPL

        repl = InteractiveREPL(self.sandbox, self.state)
        repl.start()
        self.state.mode = SessionMode.LEARNING

    def _show_summary(self):
        """Show the end-of-session summary."""
        summary = self.state.get_summary()

        print("\n" + "=" * 60)
        print("SESSION COMPLETE")
        print("=" * 60)
        print(f"Library: {summary['library']}")
        print(
            f"Score: {summary['questions_correct']}/{summary['questions_answered']} ({summary['score_percentage']}%)"
        )
        print(f"Time: {summary['session_duration']:.0f} seconds")
        print(f"Hints used: {summary['hints_used']}")
        print("=" * 60 + "\n")
