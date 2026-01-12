"""Interactive REPL for experimentation during learning sessions."""

import logging

from execution.sandbox import CodeSandbox
from session.state import SessionState

logger = logging.getLogger(__name__)


class InteractiveREPL:
    """
    Integrated REPL for experimentation.

    User can drop into this mid-session to experiment with the library.
    """

    COMMANDS = {
        "/exit": "Exit REPL and return to questions",
        "/quit": "Same as /exit",
        "/help": "Show this help message",
        "/history": "Show REPL command history",
        "/current": "Show current question",
        "/docs": "Show docs for a component: /docs merge",
        "/clear": "Clear the screen",
    }

    def __init__(self, sandbox: CodeSandbox, session: SessionState):
        """
        Initialize the REPL.

        Args:
            sandbox: Code sandbox for execution
            session: Current session state
        """
        self.sandbox = sandbox
        self.session = session
        self._multiline_buffer = []

    def start(self):
        """
        Start the REPL loop.

        Runs until the user exits with /exit or /quit.
        """
        self._print_banner()

        while True:
            try:
                line = self._get_input()
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n(Use /exit to leave REPL)")
                continue

            if line is None:
                break

            if not line:
                continue

            if line.startswith("/"):
                result = self._handle_command(line)
                if result == "EXIT":
                    break
                if result:
                    print(result)
            else:
                result = self._execute(line)
                if result:
                    print(result)

        self._on_exit()

    def _get_input(self) -> str:
        """Get input from the user, handling multi-line code."""
        prompt = ">>> " if not self._multiline_buffer else "... "

        line = input(prompt)

        # Check for commands only on first line
        if not self._multiline_buffer and line.startswith("/"):
            return line

        self._multiline_buffer.append(line)

        # Check if we need more lines
        code = "\n".join(self._multiline_buffer)

        # Simple heuristics for multi-line input
        if line.endswith(":"):
            # Starting a block - need more lines
            return self._get_input()

        if line.startswith((" ", "\t")) and len(self._multiline_buffer) > 1:
            # Continuing a block
            return self._get_input()

        # Complete input
        result = code
        self._multiline_buffer = []
        return result

    def _handle_command(self, line: str) -> str:
        """
        Process REPL commands.

        Args:
            line: Command line starting with /

        Returns:
            "EXIT" to exit REPL, or message to display
        """
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("/exit", "/quit"):
            return "EXIT"

        elif cmd == "/help":
            return self._format_help()

        elif cmd == "/history":
            return self._format_history()

        elif cmd == "/current":
            return self._format_current_question()

        elif cmd == "/docs":
            return self._show_docs(arg)

        elif cmd == "/clear":
            print("\033[2J\033[H", end="")  # ANSI clear
            return ""

        else:
            return f"Unknown command: {cmd}. Type /help for commands."

    def _execute(self, code: str) -> str:
        """
        Execute code and return formatted result.

        Args:
            code: Python code to execute

        Returns:
            Formatted output or error message
        """
        result = self.sandbox.execute(code)
        self.session.repl_history.append(code)

        if result.success:
            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout.rstrip())
            if result.output is not None:
                output_parts.append(repr(result.output))
            return "\n".join(output_parts) if output_parts else ""
        else:
            return f"Error: {result.exception}"

    def _format_help(self) -> str:
        """Format the help message."""
        lines = ["\nREPL Commands:"]
        for cmd, desc in self.COMMANDS.items():
            lines.append(f"  {cmd:<12} - {desc}")
        lines.append("")
        return "\n".join(lines)

    def _format_history(self) -> str:
        """Format the command history."""
        if not self.session.repl_history:
            return "No history yet."

        history = self.session.repl_history[-20:]  # Last 20 commands
        lines = [f"{i+1}: {cmd}" for i, cmd in enumerate(history)]
        return "\n".join(lines)

    def _format_current_question(self) -> str:
        """Format the current question."""
        question = self.session.current_question
        if not question:
            return "No active question."

        return f"""
Current Question ({question.type.value}):
Component: {question.component.qualified_path}

{question.prompt}
"""

    def _show_docs(self, name: str) -> str:
        """
        Show documentation for a component.

        Args:
            name: Component name to look up

        Returns:
            Documentation string or error message
        """
        if not name:
            return "Usage: /docs <component_name>"

        # Search in ranked components
        for rc in self.session.ranked_components:
            comp = rc.component
            if name in comp.name or name in comp.qualified_path:
                return f"""
{comp.qualified_path}{comp.signature}

{comp.docstring}
"""

        return f"Documentation not found for: {name}"

    def _print_banner(self):
        """Print REPL welcome message."""
        lib = self.session.library_path
        print(f"\n{'=' * 50}")
        print(f"lib-learn REPL ({lib} loaded)")
        print("Type Python code to experiment.")
        print("Type /help for commands, /exit to return.")
        print("=" * 50 + "\n")

    def _on_exit(self):
        """Clean up when exiting REPL."""
        print("\nReturning to questions...\n")
