

from typing import Any, Literal, TypeGuard, TypedDict

class GenericSuccess(TypedDict):
    success: Literal[True]

class GenericFailure(TypedDict):
    success: Literal[False]
    error: str

class GenericError(TypedDict):
    success: Literal[False]
    error: Exception

# Database

class SingleSuccess(TypedDict):
    success: Literal[True]
    data: tuple[Any, ...] | None

class SingleSuccessCleaned(TypedDict):
    success: Literal[True]
    data: Any | None

class MultipleSuccess(TypedDict):
    success: Literal[True]
    data: list[list[Any]]

class MultipleTupleSuccess(TypedDict):
    success: Literal[True]
    data: list[tuple[Any, ...]]

# Type checking

def is_single_success(result: GenericSuccess | SingleSuccess | GenericFailure) -> TypeGuard[SingleSuccess]:
  return result['success'] and 'data' in result

# Error convertion

def error_to_failure(error: dict) -> dict:
  return {"success": False, "error": str(error['error'])}