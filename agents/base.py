"""Base agent class with litellm integration."""

import json
import logging
from typing import List, Dict, Any, Optional

import litellm
from config import LLMConfig

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for LLM-powered agents.

    Provides a unified interface for calling LLMs through litellm,
    which supports multiple providers (OpenAI, Anthropic, Ollama, etc.).
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize the agent with LLM configuration.

        Args:
            config: LLM configuration with provider, model, API key, etc.
        """
        self.config = config

        # Configure litellm
        if config.api_key:
            # Set the API key for the appropriate provider
            if config.provider == "openai":
                litellm.api_key = config.api_key
            elif config.provider == "anthropic":
                litellm.anthropic_key = config.api_key

        if config.api_base:
            litellm.api_base = config.api_base

    def _get_model_string(self) -> str:
        """
        Get the model string for litellm.

        Different providers need different formats.
        """
        provider = self.config.provider
        model = self.config.model

        # Some providers need a prefix
        provider_prefixes = {
            "anthropic": "anthropic/",
            "together": "together_ai/",
            "groq": "groq/",
            "ollama": "ollama/",
            "cohere": "cohere/",
        }

        prefix = provider_prefixes.get(provider, "")

        # If the model already has a prefix, don't add another
        if "/" in model:
            return model

        return f"{prefix}{model}"

    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Call the LLM using litellm.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            response_format: Optional response format (e.g., {"type": "json_object"})
            max_retries: Number of retries on failure

        Returns:
            The LLM's response content as a string

        Raises:
            Exception: If all retries fail
        """
        model = self._get_model_string()

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key

        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base

        last_error = None
        for attempt in range(max_retries):
            try:
                logger.debug(
                    "LLM call attempt %d/%d to %s",
                    attempt + 1,
                    max_retries,
                    model,
                )

                response = litellm.completion(**kwargs)
                content = response.choices[0].message.content

                logger.debug("LLM response received, length: %d", len(content))
                return content

            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM call attempt %d failed: %s",
                    attempt + 1,
                    str(e),
                )

        raise last_error

    def _call_llm_json(
        self,
        messages: List[Dict[str, str]],
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Call the LLM and parse the response as JSON.

        Args:
            messages: List of message dicts
            max_retries: Number of retries on failure

        Returns:
            Parsed JSON response as a dict

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        # Try to use JSON mode if supported
        response_format = {"type": "json_object"}

        try:
            content = self._call_llm(
                messages,
                response_format=response_format,
                max_retries=max_retries,
            )
        except Exception:
            # Some providers don't support response_format, try without
            content = self._call_llm(messages, max_retries=max_retries)

        # Clean up the response - sometimes LLMs wrap JSON in markdown
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        return json.loads(content)

    def _build_messages(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> List[Dict[str, str]]:
        """
        Build a standard message list from system and user prompts.

        Args:
            system_prompt: The system/context prompt
            user_prompt: The user's request

        Returns:
            List of message dicts
        """
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
