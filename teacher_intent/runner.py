"""Run one request end to end and return a flat, loggable record. Expected failures never raise."""
import datetime as dt
import time
from typing import Optional

from .client import ProviderError, TeacherTimeout
from .config import PROMPT_VERSION, SCHEMA_VERSION, Config
from .prompt import SYSTEM_PROMPT, build_user_message
from .validate import InvalidJSON, SchemaViolation, parse_intent


def estimate_cost(usage: Optional[dict], cfg: Config) -> Optional[float]:
    if not usage:
        return None
    return round(usage["input_tokens"] / 1e6 * cfg.price_in_per_mtok
                 + usage["output_tokens"] / 1e6 * cfg.price_out_per_mtok, 6)


def run_one(request: dict, provider, cfg: Config) -> dict:
    record = {
        "request_id": request["id"],
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": provider.name,
        "model_id": cfg.model_id,
        "model_id_reported": None,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": None,
        "error_type": None,
        "error_detail": None,
        "duration_s": None,
        "usage": None,
        "estimated_cost_usd": None,
        "pricing_assumption": cfg.pricing_assumption,
        "intent": None,
        "raw_output_excerpt": None,
    }
    t0 = time.monotonic()
    try:
        resp = provider.complete(SYSTEM_PROMPT, build_user_message(request["text"]))
        record["duration_s"] = round(time.monotonic() - t0, 3)
        record["usage"] = resp.usage
        record["model_id_reported"] = resp.model_id
        record["estimated_cost_usd"] = estimate_cost(resp.usage, cfg)  # tokens were spent even if output is bad
        try:
            record["intent"] = parse_intent(resp.text)
            record["status"] = "ok"
        except InvalidJSON as e:
            record.update(status="invalid_json", error_type="InvalidJSON", error_detail=str(e),
                          raw_output_excerpt=resp.text[:500])
        except SchemaViolation as e:
            record.update(status="schema_violation", error_type="SchemaViolation", error_detail=str(e),
                          raw_output_excerpt=resp.text[:500])
    except TeacherTimeout as e:
        record.update(status="timeout", error_type="TeacherTimeout", error_detail=str(e))
    except ProviderError as e:
        record.update(status="provider_error", error_type="ProviderError",
                      error_detail=f"{e} (status={e.status})")
    if record["duration_s"] is None:
        record["duration_s"] = round(time.monotonic() - t0, 3)
    return record
