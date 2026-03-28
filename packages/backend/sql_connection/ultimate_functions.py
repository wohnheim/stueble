
from typing import Any


def clean_single_data(data: list | tuple) -> Any:
    """
    Cleans the data for a single data point by removing the outer list. If the data is None, it returns None in data.

    Args:
        data (list | tuple): The list or tuple containing the data to be cleaned
    Returns:
        Any: The cleaned data or None if the input is None
    """
    if isinstance(data, (list, tuple)):
        return data[0] if data else None
    return data