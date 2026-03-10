
from typing import Any
from backend.datatypes.funcres import FuncRes


def clean_single_data(data: FuncRes | Any) -> FuncRes | Any:
    """
    Cleans the data for a single data point by removing the outer list. If the data is None, it returns None in data.

    Args:
        data (FuncRes | Any): The FuncRes object containing the data to be cleaned or just the data object (Any)
    Returns:
        FuncRes | Any: A new FuncRes object with the cleaned data and the same metadata as the original in case a FuncRes object was passed, or just the data if an Any object was passed.
    """
    if isinstance(data, FuncRes):
        return FuncRes(data=data.data[0] if data.data is not None else None,
                    **{k: v for k, v in data.__dict__.items() if k != 'data'}
                       )
    return data[0] if data is not None else None
