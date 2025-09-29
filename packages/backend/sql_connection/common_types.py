

from typing import Any, Literal, TypeGuard, TypedDict

class GenericSuccess(TypedDict):
    success: Literal[True]

class GenericFailure(TypedDict):
    success: Literal[False]
    error: str

# class GenericError(TypedDict):
#     success: Literal[False]
#     error: Exception

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

def is_multiple_success(result: MultipleSuccess | GenericFailure) -> TypeGuard[MultipleSuccess]:
  return result['success']

def is_multiple_tuple_success(result: MultipleTupleSuccess | GenericFailure) -> TypeGuard[MultipleTupleSuccess]:
  return result['success']

def is_generic_failure(result: SingleSuccess | MultipleSuccess | MultipleTupleSuccess | GenericFailure) -> TypeGuard[GenericFailure]:
  return result['success'] is False
