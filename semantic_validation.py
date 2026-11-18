
class SemanticValidationError(ValueError):
    """Raised when the engineering intent contains semantic issues."""


def validate_semantics(intent):
    components = intent.components

    normalized_components = [
        component.strip().casefold()
        for component in components
    ]

    # Check for empty components
    if any(not component for component in normalized_components):
        raise SemanticValidationError(
            "Empty components are not allowed."
        )

    # Check for duplicate components
    if len(normalized_components) != len(set(normalized_components)):
        raise SemanticValidationError(
            "Duplicate components found."
        )
