"""LLM client abstraction and GPT@RUB (OpenAI-compatible) implementation."""

import logging
import os
import time
from abc import ABC, abstractmethod
from collections import deque

from apr_framework.core.exceptions import APRFrameworkError, ConfigurationError
from apr_framework.repair.llm.config import LLMRepairConfig

logger = logging.getLogger(__name__)

GPT_AT_RUB_DEFAULT_BASE_URL = "https://gpt.ruhr-uni-bochum.de/external/v1"

# GPT@RUB caps external-API requests at 60 per minute (see the "BETA: External API
# Endpoint" documentation). The client throttles itself to that limit rather than
# relying on the server to reject overflow requests.
GPT_AT_RUB_RATE_LIMIT_REQUESTS_PER_MINUTE = 60
GPT_AT_RUB_RATE_LIMIT_WINDOW_SECONDS = 60.0


class LLMClient(ABC):
    """Provider-agnostic interface for LLM completion calls."""

    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> str:
        """Send an OpenAI-style messages list and return the response text.

        Args:
            messages: Conversation turns, e.g.
                [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

        Returns:
            The model's reply as a plain string.
        """


class OpenAICompatibleClient(LLMClient):
    """LLM client for any OpenAI-compatible endpoint, including GPT@RUB.

    The API key is read from the environment at call time so the env var can be
    set after this object is constructed (useful in tests and Docker environments).
    Streaming is explicitly disabled — GPT@RUB does not support it.
    """

    def __init__(self, repair_config: LLMRepairConfig) -> None:
        self._repair_config = repair_config
        self._endpoint_url = repair_config.base_url or GPT_AT_RUB_DEFAULT_BASE_URL
        self._recent_request_timestamps: deque[float] = deque()

    def _wait_for_rate_limit_slot(self) -> None:
        """Block until issuing another request would stay within the per-minute cap."""
        while True:
            now = time.monotonic()
            while (
                self._recent_request_timestamps
                and now - self._recent_request_timestamps[0]
                >= GPT_AT_RUB_RATE_LIMIT_WINDOW_SECONDS
            ):
                self._recent_request_timestamps.popleft()

            if (
                len(self._recent_request_timestamps)
                < GPT_AT_RUB_RATE_LIMIT_REQUESTS_PER_MINUTE
            ):
                self._recent_request_timestamps.append(now)
                return

            sleep_seconds = GPT_AT_RUB_RATE_LIMIT_WINDOW_SECONDS - (
                now - self._recent_request_timestamps[0]
            )
            logger.info(
                "GPT@RUB rate limit (%d req/min) reached; sleeping %.1fs",
                GPT_AT_RUB_RATE_LIMIT_REQUESTS_PER_MINUTE,
                sleep_seconds,
            )
            time.sleep(sleep_seconds)

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Call the OpenAI-compatible chat completions endpoint.

        Args:
            messages: Conversation turns in OpenAI format.

        Returns:
            The model's text response.

        Raises:
            ConfigurationError: If the API key env var is not set.
            APRFrameworkError: On any OpenAI API error.
        """
        import openai

        api_key = os.environ.get(self._repair_config.api_key_env_var)
        if not api_key:
            raise ConfigurationError(
                f"LLM API key not found. Set the environment variable "
                f"{self._repair_config.api_key_env_var!r} before running."
            )

        openai_client = openai.OpenAI(
            base_url=self._endpoint_url,
            api_key=api_key,
        )

        logger.debug(
            "Calling %s model=%s temperature=%s",
            self._endpoint_url,
            self._repair_config.model_name,
            self._repair_config.temperature,
        )

        self._wait_for_rate_limit_slot()

        try:
            response = openai_client.chat.completions.create(
                model=self._repair_config.model_name,
                messages=messages,
                temperature=self._repair_config.temperature,
                stream=False,
            )
        except openai.OpenAIError as error:
            raise APRFrameworkError(
                f"LLM API call failed ({type(error).__name__}): {error}"
            ) from error

        response_text = response.choices[0].message.content
        logger.debug("LLM response received (%d chars)", len(response_text or ""))
        return response_text or ""
