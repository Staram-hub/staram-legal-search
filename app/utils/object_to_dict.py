"""
This module provides a utility function to convert an object to a dictionary. Useful to for converting
openai response model output to dict
"""

from typing import Any, Union


def object_to_dict(
    obj: Union[dict[str, Any], list[dict[str, Any]]],
) -> Union[dict[str, Any], list[dict[str, Any]]]:
    """
    Converts an object to a dictionary recursively, handling lists and objects with '__dict__' attribute.
    """
    if isinstance(obj, list):
        return [object_to_dict(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return {key: object_to_dict(value) for key, value in obj.__dict__.items()}
    else:
        return obj
