"""Cost estimation from a user-maintained pricing file (USD per million tokens)."""
import json


def load_pricing(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def estimate_cost(pricing, model_ids, usage):
    """Return (cost_usd | None, note). Never guesses: missing price or usage -> None."""
    if not usage or "input_tokens" not in usage or "output_tokens" not in usage:
        return None, "provider did not report token usage"
    models = (pricing or {}).get("models", {})
    for model_id in model_ids:
        entry = models.get(model_id)
        if entry:
            cost = (usage["input_tokens"] * entry["input_per_mtok"]
                    + usage["output_tokens"] * entry["output_per_mtok"]) / 1_000_000
            return round(cost, 6), f"rates from pricing file for {model_id} (as_of={entry.get('as_of', '?')})"
    return None, f"no pricing entry for {' / '.join(model_ids)}; add one to the pricing file"
