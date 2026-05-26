"""LLM gateway exception types (PS5.1)."""


class LLMGatewayTimeoutError(Exception):
    """Raised when upstream LLM call times out."""


class LLMGatewayProviderError(Exception):
    """Raised when upstream LLM provider returns a non-timeout error."""


class LLMBudgetExceededError(Exception):
    """Raised when LLM budget guardrail refuses a call (PS5.6; no backend fallback)."""
