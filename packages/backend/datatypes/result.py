"""
Result data type module

This module defines the Result class for representing operation outcomes.
"""

# TODO: implement .succes Enum datatype of success values: FULL_SUCCESS, PARTIAL_SUCCESS, ERROR

from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Optional

Data = TypeVar("Data") # success type
Error = TypeVar("Error") # error type

@dataclass
class Result(Generic[Data, Error]):
    """
    Result class representing the outcome of an operation, which can be either a success with data or an error.
    Especially useful for database operations.
    """

    def __init__(self, data: Data | None = None, error: Error | None = None, stack_trace: str | None = None, additional_information: Any = None) -> None:
        """
        Initialization of the Result object.

        Args:
            data (Data | None): The successful result data.
            error (Error | None): The error information if the operation failed.
            stack_trace: str | None = None
            additional_information: Any = None

        Returns:
            None
        """
        # if data and error are specified, return error
        if all(i is not None for i in (data, error)):
            raise ValueError("Result cannot have both data and error.")
        self._data = data
        self._error = error
        self._stack_trace = stack_trace
        self._additional_information: Any = None

    @property
    def is_success(self) -> bool:
        """
        Represents whether the result is a success.

        Returns:
            bool: True if the result is a success, False otherwise.
        """
        return self._error is None

    @property
    def is_error(self) -> bool:
        """
        Represents whether the result is an error.

        Returns:
            bool: True if the result is an error, False otherwise.
        """
        return self._error is not None
    
    @property
    def is_stack_trace(self) -> bool:
        """
        Represents whether the result has a stack trace.

        Returns:
            bool: True if the result has a stack trace, False otherwise.
        """
        return self._stack_trace is not None

    @property
    def data(self) -> Data:
        """
        Represents the successful result data.

        Returns:
            Data: The successful result data.
        """
        if self.is_error or self.is_stack_trace:
            raise ValueError("No data available, operation resulted in an error.")
        return self._data  # type: ignore

    @property
    def error(self) -> Error:
        """
        Represents the error information if the operation failed.

        Returns:
            Error: The error information if the operation failed.
        """
        if self.is_success:
            raise ValueError("Operation was successful.")
        return self._error  # type: ignore
    
    @property
    def additional_information(self) -> Any:
        """
        Represents any additional information related to the result.

        Returns:
            Any: Additional information related to the result.
        """
        return self._additional_information
    
    @property
    def stack_trace(self) -> str:
        """
        Represents the stack trace if available.

        Returns:
            str: The stack trace if available.
        """
        if self.is_success:
            raise ValueError("Operation was successful.")
        return self._stack_trace  # type: ignore
