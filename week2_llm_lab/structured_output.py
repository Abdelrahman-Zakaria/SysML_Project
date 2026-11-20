
from models import Intent


def build_response_format() -> dict:
    """
    Convert our Pydantic Intent model into
    a Groq-compatible strict JSON Schema format.
    """

    schema = Intent.model_json_schema()

    # Remove display-only titles from the schema.
    schema.pop("title", None)

    for field_schema in schema["properties"].values():
        field_schema.pop("title", None)

        # Convert Pydantic's single-value const
        # into an enum supported by the provider.
        if "const" in field_schema:
            value = field_schema.pop("const")
            field_schema["enum"] = [value]

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sysml_intent",
            "strict": True,
            "schema": schema
        }
    }
