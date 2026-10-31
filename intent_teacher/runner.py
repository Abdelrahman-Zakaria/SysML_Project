"""Send one request, classify the outcome, and build an audit record."""
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

from .cost import estimate_cost
from .prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_message
from .providers import ProviderError, TeacherTimeout
from .schema import (SCHEMA_VERSION, IntentValidationError, InvalidJSONError,
                     parse_intent_json, validate_intent)

STATUSES = ("ok", "timeout", "provider_error", "invalid_json", "invalid_intent")


@dataclass
class RunRecord:
    timestamp: str
    provider: str
    requested_model: str
    response_model: Optional[str]
    prompt_version: str
    schema_version: str
    status: str
    error_message: Optional[str]
    duration_s: float
    usage: Optional[dict]
    est_cost_usd: Optional[float]
    cost_note: str
    intent: Optional[dict]  # only populated when status == "ok"

    def to_dict(self):
        return asdict(self)


def request_intent(provider, project_request, *, timeout=30.0, pricing=None, clock=time.perf_counter):
    """Never raises for expected failures; the outcome is in `status`."""
    start = clock()
    completion = intent = error = None
    try:
        completion = provider.complete(SYSTEM_PROMPT, build_user_message(project_request), timeout)
        intent = validate_intent(parse_intent_json(completion.text))
        status = "ok"
    except TeacherTimeout as exc:
        status, error = "timeout", str(exc)
    except ProviderError as exc:
        status, error = "provider_error", str(exc)
    except InvalidJSONError as exc:
        status, error = "invalid_json", str(exc)
    except IntentValidationError as exc:
        status, error = "invalid_intent", str(exc)
    duration = round(clock() - start, 4)

    usage = completion.usage if completion else None
    response_model = completion.model_id if completion else None
    requested = getattr(provider, "model", "unknown")
    cost, note = estimate_cost(pricing, [m for m in (response_model, requested) if m], usage)

    return RunRecord(
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        provider=provider.name, requested_model=requested, response_model=response_model,
        prompt_version=PROMPT_VERSION, schema_version=SCHEMA_VERSION, status=status,
        error_message=error, duration_s=duration, usage=usage,
        est_cost_usd=cost, cost_note=note, intent=intent,
    )
