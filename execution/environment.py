"""Isolated virtual environment management for library exploration."""

import sys
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LibraryEnvironment:
    """
    Manages isolated virtual environments for exploring libraries.

    Creates and caches venvs in ~/.lib-learn/envs/<library>/ so users
    can explore libraries without installing them globally.
    """

    ENVS_DIR = Path.home() / ".lib-learn" / "envs"

    def __init__(self):
        """Initialize the environment manager."""
        self.ENVS_DIR.mkdir(parents=True, exist_ok=True)
        self._current_python: Optional[str] = None
        self._current_library: Optional[str] = None

    def get_base_module(self, library_path: str) -> str:
        """Extract the base module name from a library path."""
        return library_path.split(".")[0]

    def is_available(self, library_path: str) -> bool:
        """
        Check if a library is available for import.

        Args:
            library_path: The library path (e.g., "pandas.DataFrame")

        Returns:
            True if the library can be imported
        """
        base_module = self.get_base_module(library_path)

        # First check in current environment
        try:
            __import__(base_module)
            return True
        except ImportError:
            pass

        # Check if we have a cached venv for it
        venv_python = self._get_venv_python(base_module)
        if venv_python and Path(venv_python).exists():
            return True

        return False

    def ensure_available(
        self,
        library_path: str,
        auto_install: bool = False,
    ) -> str:
        """
        Ensure a library is available, installing if needed.

        Args:
            library_path: The library path (e.g., "pandas.DataFrame")
            auto_install: If True, install without prompting

        Returns:
            Path to the Python interpreter to use

        Raises:
            RuntimeError: If the library cannot be made available
        """
        base_module = self.get_base_module(library_path)

        # Check if available in current environment
        try:
            __import__(base_module)
            self._current_python = sys.executable
            self._current_library = base_module
            logger.info("Library %s available in current environment", base_module)
            return sys.executable
        except ImportError:
            pass

        # Check for cached venv
        venv_python = self._get_venv_python(base_module)
        if venv_python and Path(venv_python).exists():
            # Verify the library is actually installed
            if self._check_import_in_venv(venv_python, base_module):
                self._current_python = venv_python
                self._current_library = base_module
                logger.info("Using cached venv for %s", base_module)
                return venv_python

        # Need to create venv and install
        if not auto_install:
            print(f"\nLibrary '{base_module}' is not installed.")
            response = input(
                f"Install '{base_module}' in an isolated environment? [Y/n] "
            )
            if response.lower() in ("n", "no"):
                raise RuntimeError(f"Library '{base_module}' is not available")

        venv_python = self._create_and_install(base_module)
        self._current_python = venv_python
        self._current_library = base_module
        return venv_python

    def get_python_executable(self) -> str:
        """
        Get the Python executable for the current library.

        Returns:
            Path to Python executable
        """
        return self._current_python or sys.executable

    def _get_venv_dir(self, module_name: str) -> Path:
        """Get the venv directory for a module."""
        return self.ENVS_DIR / module_name

    def _get_venv_python(self, module_name: str) -> Optional[str]:
        """Get the Python executable path for a module's venv."""
        venv_dir = self._get_venv_dir(module_name)
        if sys.platform == "win32":
            python_path = venv_dir / "Scripts" / "python.exe"
        else:
            python_path = venv_dir / "bin" / "python"

        if python_path.exists():
            return str(python_path)
        return None

    def _check_import_in_venv(self, python_path: str, module_name: str) -> bool:
        """Check if a module can be imported in a venv."""
        try:
            result = subprocess.run(
                [python_path, "-c", f"import {module_name}"],
                capture_output=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _create_and_install(self, module_name: str) -> str:
        """
        Create a venv and install a library.

        Args:
            module_name: The module to install

        Returns:
            Path to the Python executable in the new venv
        """
        venv_dir = self._get_venv_dir(module_name)

        # Remove existing venv if present
        if venv_dir.exists():
            shutil.rmtree(venv_dir)

        print(f"Creating isolated environment for '{module_name}'...")

        # Try uv first (faster), fall back to venv
        if self._has_uv():
            self._create_with_uv(venv_dir, module_name)
        else:
            self._create_with_venv(venv_dir, module_name)

        python_path = self._get_venv_python(module_name)
        if not python_path or not Path(python_path).exists():
            raise RuntimeError(f"Failed to create venv for {module_name}")

        # Verify installation
        if not self._check_import_in_venv(python_path, module_name):
            raise RuntimeError(f"Failed to install {module_name}")

        print(f"Successfully installed '{module_name}'")
        return python_path

    def _has_uv(self) -> bool:
        """Check if uv is available."""
        return shutil.which("uv") is not None

    def _create_with_uv(self, venv_dir: Path, module_name: str):
        """Create venv and install using uv."""
        # Create venv
        subprocess.run(
            ["uv", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
        )

        # Install the library
        print(f"Installing {module_name}...")
        result = subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(venv_dir / "bin" / "python"),
                module_name,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error("uv pip install failed: %s", result.stderr)
            raise RuntimeError(f"Failed to install {module_name}: {result.stderr}")

    def _create_with_venv(self, venv_dir: Path, module_name: str):
        """Create venv and install using standard venv + pip."""
        import venv

        # Create venv
        venv.create(venv_dir, with_pip=True)

        # Get pip path
        if sys.platform == "win32":
            pip_path = venv_dir / "Scripts" / "pip.exe"
        else:
            pip_path = venv_dir / "bin" / "pip"

        # Install the library
        print(f"Installing {module_name}...")
        result = subprocess.run(
            [str(pip_path), "install", module_name],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error("pip install failed: %s", result.stderr)
            raise RuntimeError(f"Failed to install {module_name}: {result.stderr}")

    def cleanup(self, module_name: Optional[str] = None):
        """
        Clean up cached venvs.

        Args:
            module_name: Specific module to clean up, or None for all
        """
        if module_name:
            venv_dir = self._get_venv_dir(module_name)
            if venv_dir.exists():
                shutil.rmtree(venv_dir)
                print(f"Removed environment for '{module_name}'")
        else:
            if self.ENVS_DIR.exists():
                for child in self.ENVS_DIR.iterdir():
                    if child.is_dir():
                        shutil.rmtree(child)
                print("Removed all cached environments")

    def list_cached(self) -> list:
        """List all cached library environments."""
        if not self.ENVS_DIR.exists():
            return []

        return [
            d.name
            for d in self.ENVS_DIR.iterdir()
            if d.is_dir() and self._get_venv_python(d.name)
        ]
