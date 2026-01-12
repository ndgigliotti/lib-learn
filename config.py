"""Configuration management for lib-learn."""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

# Use tomllib in Python 3.11+, otherwise tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class SandboxConfig:
    """Code execution sandbox configuration."""

    timeout: int = 10
    max_memory_mb: int = 256
    allowed_imports: List[str] = field(
        default_factory=lambda: [
            "pandas",
            "numpy",
            "collections",
            "itertools",
            "functools",
            "datetime",
            "math",
            "random",
            "re",
            "json",
            "string",
            "operator",
            "typing",
            "dataclasses",
            "enum",
            "copy",
        ]
    )


@dataclass
class SessionConfig:
    """Learning session configuration."""

    questions_per_session: int = 10
    components_to_rank: int = 50
    enable_hints: bool = True
    max_hints_per_question: int = 3


@dataclass
class AppConfig:
    """Complete application configuration."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    log_level: str = "INFO"


class ConfigManager:
    """
    Manages configuration loading and merging from multiple sources.

    Priority order (highest to lowest):
    1. CLI arguments
    2. Environment variables
    3. User config file (~/.lib-learn/config.toml)
    4. Project config file (.lib-learn.toml)
    5. Built-in defaults
    """

    USER_CONFIG_DIR = Path.home() / ".lib-learn"
    USER_CONFIG_PATH = USER_CONFIG_DIR / "config.toml"
    PROJECT_CONFIG_NAME = ".lib-learn.toml"

    # Environment variable mapping
    ENV_MAP = {
        "LIBLEARN_LLM_PROVIDER": ("llm", "provider"),
        "LIBLEARN_LLM_MODEL": ("llm", "model"),
        "LIBLEARN_LLM_API_KEY": ("llm", "api_key"),
        "LIBLEARN_LLM_API_BASE": ("llm", "api_base"),
        "LIBLEARN_SANDBOX_TIMEOUT": ("sandbox", "timeout"),
        "LIBLEARN_LOG_LEVEL": ("log_level",),
        "LIBLEARN_QUESTIONS_PER_SESSION": ("session", "questions_per_session"),
    }

    # Provider-specific API key environment variables
    PROVIDER_API_KEYS = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "cohere": "COHERE_API_KEY",
        "together": "TOGETHER_API_KEY",
        "groq": "GROQ_API_KEY",
    }

    @classmethod
    def load(cls, cli_overrides: Optional[Dict[str, Any]] = None) -> AppConfig:
        """
        Load configuration from all sources and merge.

        Args:
            cli_overrides: Dict of CLI argument overrides

        Returns:
            Merged AppConfig
        """
        config = AppConfig()

        # Load project config if exists
        project_config_path = Path.cwd() / cls.PROJECT_CONFIG_NAME
        project_data = cls._load_toml(project_config_path)
        if project_data:
            config = cls._merge(config, project_data)

        # Load user config if exists
        user_data = cls._load_toml(cls.USER_CONFIG_PATH)
        if user_data:
            config = cls._merge(config, user_data)

        # Apply environment variables
        config = cls._apply_env(config)

        # Apply CLI overrides
        if cli_overrides:
            config = cls._merge(config, cli_overrides)

        # Auto-detect API key based on provider
        if not config.llm.api_key:
            provider_env = cls.PROVIDER_API_KEYS.get(config.llm.provider)
            if provider_env:
                config.llm.api_key = os.environ.get(provider_env)

        return config

    @classmethod
    def _load_toml(cls, path: Path) -> Optional[Dict[str, Any]]:
        """Load TOML file if it exists."""
        if not path.exists():
            return None

        if tomllib is None:
            return None

        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except Exception:
            return None

    @classmethod
    def _merge(cls, config: AppConfig, data: Dict[str, Any]) -> AppConfig:
        """Merge dict data into config."""
        if "llm" in data:
            llm_data = data["llm"]
            if "provider" in llm_data:
                config.llm.provider = llm_data["provider"]
            if "model" in llm_data:
                config.llm.model = llm_data["model"]
            if "api_key" in llm_data:
                config.llm.api_key = llm_data["api_key"]
            if "api_base" in llm_data:
                config.llm.api_base = llm_data["api_base"]
            if "temperature" in llm_data:
                config.llm.temperature = float(llm_data["temperature"])
            if "max_tokens" in llm_data:
                config.llm.max_tokens = int(llm_data["max_tokens"])

        if "sandbox" in data:
            sandbox_data = data["sandbox"]
            if "timeout" in sandbox_data:
                config.sandbox.timeout = int(sandbox_data["timeout"])
            if "max_memory_mb" in sandbox_data:
                config.sandbox.max_memory_mb = int(sandbox_data["max_memory_mb"])
            if "allowed_imports" in sandbox_data:
                config.sandbox.allowed_imports = list(sandbox_data["allowed_imports"])

        if "session" in data:
            session_data = data["session"]
            if "questions_per_session" in session_data:
                config.session.questions_per_session = int(
                    session_data["questions_per_session"]
                )
            if "components_to_rank" in session_data:
                config.session.components_to_rank = int(
                    session_data["components_to_rank"]
                )
            if "enable_hints" in session_data:
                config.session.enable_hints = bool(session_data["enable_hints"])
            if "max_hints_per_question" in session_data:
                config.session.max_hints_per_question = int(
                    session_data["max_hints_per_question"]
                )

        if "log_level" in data:
            config.log_level = data["log_level"]

        return config

    @classmethod
    def _apply_env(cls, config: AppConfig) -> AppConfig:
        """Apply environment variable overrides."""
        for env_var, path in cls.ENV_MAP.items():
            value = os.environ.get(env_var)
            if value:
                cls._set_nested(config, path, value)
        return config

    @classmethod
    def _set_nested(cls, config: AppConfig, path: tuple, value: str):
        """Set a nested attribute on config."""
        if len(path) == 1:
            setattr(config, path[0], value)
        elif len(path) == 2:
            section = getattr(config, path[0])
            # Convert types appropriately
            current_value = getattr(section, path[1])
            if isinstance(current_value, int):
                value = int(value)
            elif isinstance(current_value, float):
                value = float(value)
            elif isinstance(current_value, bool):
                value = value.lower() in ("true", "1", "yes")
            setattr(section, path[1], value)

    @classmethod
    def validate(cls, config: AppConfig) -> List[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check for API key if using remote provider
        remote_providers = {"openai", "anthropic", "cohere", "together", "groq"}
        if config.llm.provider in remote_providers and not config.llm.api_key:
            errors.append(
                f"API key required for provider '{config.llm.provider}'. "
                f"Set via config file, LIBLEARN_LLM_API_KEY, or "
                f"{cls.PROVIDER_API_KEYS.get(config.llm.provider, 'provider-specific')} env var."
            )

        # Validate numeric ranges
        if config.sandbox.timeout < 1:
            errors.append("sandbox.timeout must be at least 1 second")
        if config.session.questions_per_session < 1:
            errors.append("session.questions_per_session must be at least 1")

        return errors

    @classmethod
    def init_config_file(cls) -> Path:
        """
        Create a default config file in the user's home directory.

        Returns:
            Path to the created config file
        """
        cls.USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        default_config = """# lib-learn configuration
# See documentation for all available options

[llm]
provider = "openai"  # openai, anthropic, ollama, together, groq, etc.
model = "gpt-4o-mini"
# api_key = "..."  # Or use environment variable
temperature = 0.7
max_tokens = 2048

[sandbox]
timeout = 10  # seconds
# allowed_imports = ["pandas", "numpy", ...]

[session]
questions_per_session = 10
components_to_rank = 50
enable_hints = true
max_hints_per_question = 3
"""

        cls.USER_CONFIG_PATH.write_text(default_config)
        return cls.USER_CONFIG_PATH

    @classmethod
    def show_config(cls, config: AppConfig) -> str:
        """Return a formatted string representation of the config."""
        lines = [
            "Current Configuration:",
            "",
            "[llm]",
            f"  provider = {config.llm.provider!r}",
            f"  model = {config.llm.model!r}",
            f"  api_key = {'<set>' if config.llm.api_key else '<not set>'}",
            f"  api_base = {config.llm.api_base!r}"
            if config.llm.api_base
            else "  api_base = <default>",
            f"  temperature = {config.llm.temperature}",
            f"  max_tokens = {config.llm.max_tokens}",
            "",
            "[sandbox]",
            f"  timeout = {config.sandbox.timeout}",
            f"  max_memory_mb = {config.sandbox.max_memory_mb}",
            f"  allowed_imports = {len(config.sandbox.allowed_imports)} modules",
            "",
            "[session]",
            f"  questions_per_session = {config.session.questions_per_session}",
            f"  components_to_rank = {config.session.components_to_rank}",
            f"  enable_hints = {config.session.enable_hints}",
            f"  max_hints_per_question = {config.session.max_hints_per_question}",
            "",
            f"log_level = {config.log_level!r}",
        ]
        return "\n".join(lines)
