"""Sandboxed code execution environment."""

import sys
import time
import pickle
import logging
import tempfile
import subprocess
from dataclasses import dataclass
from typing import Any, Optional, List
from pathlib import Path

from config import SandboxConfig

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution in the sandbox."""

    success: bool
    output: Any  # The returned/printed value
    stdout: str
    stderr: str
    exception: Optional[str]
    execution_time: float  # seconds


# Template for sandboxed execution
SANDBOX_TEMPLATE = """
import sys
import io
import pickle
import builtins

# Capture stdout
_stdout_capture = io.StringIO()
_original_stdout = sys.stdout
sys.stdout = _stdout_capture

# Restrict dangerous builtins
_forbidden = ['eval', 'exec', 'compile', '__import__', 'open',
              'input', 'breakpoint', 'exit', 'quit']
for _name in _forbidden:
    if hasattr(builtins, _name):
        delattr(builtins, _name)

# Restrict imports
_allowed_modules = {allowed_modules}
_original_import = __builtins__.__dict__.get('__import__', __import__)

def _restricted_import(name, *args, **kwargs):
    base_module = name.split('.')[0]
    if base_module not in _allowed_modules:
        raise ImportError(f"Import of '{{name}}' is not allowed in sandbox")
    return _original_import(name, *args, **kwargs)

builtins.__import__ = _restricted_import

# Result storage
_result = None
_exception = None

try:
    # Setup code
{setup_code}

    # User code
{user_code}

except Exception as _e:
    _exception = str(_e)

# Restore stdout
sys.stdout = _original_stdout
_stdout_output = _stdout_capture.getvalue()

# Write results
with open("{output_file}", "wb") as _f:
    pickle.dump({{
        "result": _result,
        "stdout": _stdout_output,
        "exception": _exception,
    }}, _f)
"""


class CodeSandbox:
    """
    Sandboxed code execution environment.

    Executes code in a subprocess with:
    - Restricted imports (whitelist only)
    - Removed dangerous builtins
    - Timeout enforcement
    - Output capture
    """

    def __init__(self, config: SandboxConfig):
        """
        Initialize the sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config
        self._library_imports: List[str] = []

    def set_library(self, library_path: str):
        """
        Configure the sandbox to allow imports for the library being studied.

        Args:
            library_path: The library path (e.g., "pandas.DataFrame")
        """
        # Extract the base module name
        base_module = library_path.split(".")[0]
        if base_module not in self._library_imports:
            self._library_imports.append(base_module)
            logger.debug("Added %s to sandbox allowed imports", base_module)

    def execute(
        self,
        code: str,
        setup_code: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute code in the sandbox.

        Args:
            code: The code to execute
            setup_code: Optional setup code to run first
            timeout: Timeout in seconds (uses config default if None)

        Returns:
            ExecutionResult with output and status
        """
        timeout = timeout or self.config.timeout
        start_time = time.time()

        # Prepare allowed modules list
        allowed = set(self.config.allowed_imports)
        allowed.update(self._library_imports)
        allowed_str = repr(allowed)

        # Prepare the code
        setup_indent = self._indent_code(setup_code or "pass", 4)
        user_indent = self._indent_code(code, 4)

        # Create temp file for output
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            output_file = f.name

        try:
            # Build the sandbox script
            script = SANDBOX_TEMPLATE.format(
                allowed_modules=allowed_str,
                setup_code=setup_indent,
                user_code=user_indent,
                output_file=output_file.replace("\\", "\\\\"),
            )

            # Write script to temp file
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                delete=False,
            ) as script_file:
                script_file.write(script)
                script_path = script_file.name

            try:
                # Execute in subprocess
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                execution_time = time.time() - start_time

                # Read the results
                try:
                    with open(output_file, "rb") as f:
                        data = pickle.load(f)

                    return ExecutionResult(
                        success=data["exception"] is None,
                        output=data["result"],
                        stdout=data["stdout"],
                        stderr=result.stderr,
                        exception=data["exception"],
                        execution_time=execution_time,
                    )
                except Exception as e:
                    # Failed to read output file
                    return ExecutionResult(
                        success=False,
                        output=None,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        exception=f"Failed to read results: {str(e)}",
                        execution_time=execution_time,
                    )

            except subprocess.TimeoutExpired:
                execution_time = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    output=None,
                    stdout="",
                    stderr="",
                    exception=f"Execution timed out after {timeout} seconds",
                    execution_time=execution_time,
                )

            finally:
                # Clean up script file
                try:
                    Path(script_path).unlink()
                except Exception:
                    pass

        finally:
            # Clean up output file
            try:
                Path(output_file).unlink()
            except Exception:
                pass

    def execute_simple(self, code: str) -> str:
        """
        Execute code and return a simple string result.

        Convenience method for REPL-style execution.

        Args:
            code: The code to execute

        Returns:
            String representation of result or error
        """
        result = self.execute(code)

        if result.success:
            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout.rstrip())
            if result.output is not None:
                output_parts.append(repr(result.output))
            return "\n".join(output_parts) if output_parts else ""
        else:
            return f"Error: {result.exception}"

    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by the specified number of spaces."""
        indent = " " * spaces
        lines = code.split("\n")
        return "\n".join(indent + line for line in lines)

    def test_import(self, module_name: str) -> bool:
        """
        Test if a module can be imported in the sandbox.

        Args:
            module_name: The module to test

        Returns:
            True if the import succeeds
        """
        code = f"import {module_name}"
        result = self.execute(code)
        return result.success
