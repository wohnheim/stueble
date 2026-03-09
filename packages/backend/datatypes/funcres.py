"""
FuncRes data type module

This module defines response-related data types including Status, Message, and FuncRes classes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar, Any
import json


class Status(Enum):
    """
    Status representing the result of an operation.

    Attributes:
        FULL_SUCCESS (int): Indicates a full success.
        PARTIAL_SUCCESS (int): Indicates a partial success.
        FULL_ERROR (int): Indicates a full error.
    """

    FULL_SUCCESS = 1
    PARTIAL_SUCCESS = 0
    FULL_ERROR = -1


# NOTE: This code isn't save, because json.dumps can consume a big amount of cpu and memory
# for the wrong data
def _is_json_serializable(value: Any) -> bool:
    """
    NOTE: This code IS NOT SAVE, because json.dumps can consume a big amount of cpu and memory
    for the wrong data
    Check if a value is JSON-serializable.

    Args:
        value (Any): The value to check.
    Returns:
        bool: True if the value is JSON-serializable, False otherwise.
    """
    try:
        json.dumps(value)
        return True
    except (TypeError, OverflowError):
        return False


@dataclass
class Message:
    """
    Message class representing additional information about the response.

    Attributes:
        name (str): Name of the message.
        type (str): Type of the message.
        category (str | int | None): Category of the message.
        info (str | None): Information message.
        details (dict[str, Any] | None): Additional details as a dictionary.
        code (int | None): Optional code associated with the message.
    """

    name: str
    type: str
    category: str | int | None = None
    info: str | None = None
    details: dict[str, Any] | None = None
    code: int | None = None

    def to_json(self) -> dict:
        """
        Convert the Message object to a JSON-serializable dictionary.

        Returns:
            dict: A dictionary representation of the Message object.
        """
        return {
            "name": self.name,
            "type": self.type,
            "category": self.category,
            "info": self.info,
            "details": {
                key: value if _is_json_serializable(value) else str(value)
                for key, value in self.details.items()
            }
            if self.details
            else None,
            "code": self.code,
        }


T = TypeVar("T")  # success type
E = TypeVar("E")  # error type


@dataclass
class FuncRes(Generic[T, E]):
    """
    FuncRes class representing the result of an operation, which can be either a success with
    data or an error.

    Attributes:
        _data (Optional[T]): The successful result data.
        _error (Optional[E]): The error information if the operation failed.
        _status (Status): The status of the response indicating success or error.
    """

    def __init__(
        self,
        data: T | None = None,
        error: E | None = None,
        message: Message | None = None,
        user_warning: str | None = None,
        status: Status | None = None,
    ) -> None:
        """
        Initialize a FuncRes object.

        Args:
            data (T | None): The successful result data.
            error (E | None): The error information if the operation failed.
            message (str | dict[str, Any] | None): Additional message or information.
            user_warning (str | None): Optional user warning message.
            status (Status | None): The status of the response; if None, it will be set automatically
        Returns:
            None
        """
        self._data = data
        self._error = error
        self._user_warning = user_warning
        self._status = status
        if status is None:
            if (error is None or len(error) == 0) and (  # type: ignore
                message is None or "error" not in message.type.lower()
            ):
                self._status = Status.FULL_SUCCESS
            elif (data is None or len(data) == 0) and (  # type: ignore
                message is None or "error" in message.type.lower()
            ):
                self._status = Status.FULL_ERROR
            else:
                self._status = Status.PARTIAL_SUCCESS
        self.message = (
            message
            if message is not None
            else Message(
                name="Unknown",
                type="success" if self.status != Status.FULL_ERROR else "error",
            )
        )

    @property
    def data(self) -> T:
        """
        Get the list of successful results.

        Returns:
            T: The successful result data.
        """
        return self._data  # type: ignore

    @property
    def error(self) -> E:
        """
        Get the list of error results.

        Returns:
            E: The error result data.
        """
        return self._error  # type: ignore

    @property
    def status(self) -> Status:
        """
        Get the status of the response.

        Returns:
            Status: The status of the response.
        """
        return self._status  # type: ignore

    @property
    def is_success(self) -> bool:
        return self._status == Status.FULL_SUCCESS

    @property
    def is_error(self) -> bool:
        return (
            self._status == Status.FULL_ERROR or self.status == Status.PARTIAL_SUCCESS
        )

    @property
    def user_warning(self) -> str | None:
        """
        Get the user warning message if any.

        Returns:
            str | None: The user warning message or None if not set.
        """
        return self._user_warning

    def to_json(self) -> dict:
        """
        Convert the FuncRes object to a JSON-serializable dictionary.

        Returns:
            dict: A dictionary representation of the FuncRes object.
        """
        return {
            "data": self._data,
            "error": str(self._error),
            "status": self._status.name,  # type: ignore
            "message": self.message.to_json() if self.message else None,
        }
