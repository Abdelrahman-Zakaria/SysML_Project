"""Configuration. Everything is overridable via environment variables; no secrets live in source.

The only secret is ANTHROPIC_API_KEY, which is read from the environment at runtime.
"""
import os
from dataclasses import dataclass

PROMPT_VERSION = "intent-prompt.v1"
SCHEMA_VERSION = "intent.v1"

# ASSUMPTIONS: confirm against the provider's current pricing page before trusting cost numbers.
DEFAULT_MODEL_ID = "claude-sonnet-5-5"
DEFAULT_PRICE_IN_PER_MTOK = 3.00    # USD per 1M input tokens (assumption)
DEFAULT_PRICE_OUT_PER_MTOK = 15.00  # USD per 1M output tokens (assumption)


@dataclass(frozen=True)
class Config:
    provider: str
    model_id: str
    timeout_s: float
    max_tokens: int
    price_in_per_mtok: float
    price_out_per_mtok: float

    @property
    def pricing_assumption(self) -> str:
        return (f"{self.price_in_per_mtok}/Mtok in, {self.price_out_per_mtok}/Mtok out "
                f"(USD, user-configured assumption; not fetched from provider)")


def load_config(provider: str = "anthropic") -> Config:
    env = os.environ.get
    return Config(
        provider=provider,
        model_id=env("TEACHER_MODEL_ID", DEFAULT_MODEL_ID),
        timeout_s=float(env("TEACHER_TIMEOUT_S", "30")),
        max_tokens=int(env("TEACHER_MAX_TOKENS", "1000")),
        price_in_per_mtok=float(env("TEACHER_PRICE_IN_PER_MTOK", DEFAULT_PRICE_IN_PER_MTOK)),
        price_out_per_mtok=float(env("TEACHER_PRICE_OUT_PER_MTOK", DEFAULT_PRICE_OUT_PER_MTOK)),
    )
