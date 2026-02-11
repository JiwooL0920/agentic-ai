"""Base classes for tool/function calling framework."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ToolParameterType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    name: str
    param_type: ToolParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None
    items: dict[str, Any] | None = None

    def to_json_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {
            "type": self.param_type.value,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.items and self.param_type == ToolParameterType.ARRAY:
            schema["items"] = self.items
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None

    def to_message(self) -> str:
        if self.success:
            if isinstance(self.output, str):
                return self.output
            return str(self.output)
        return f"Error: {self.error}"


@dataclass
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)

    def to_ollama_format(self) -> dict[str, Any]:
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class BaseTool(ABC):
    def __init__(self, name: str, description: str):
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @abstractmethod
    def get_parameters(self) -> list[ToolParameter]:
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        pass

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.get_parameters(),
        )

    def to_ollama_format(self) -> dict[str, Any]:
        return self.get_definition().to_ollama_format()

    def validate_arguments(self, arguments: dict[str, Any]) -> tuple[bool, str | None]:
        params = {p.name: p for p in self.get_parameters()}

        for param_name, param in params.items():
            if param.required and param_name not in arguments:
                return False, f"Missing required parameter: {param_name}"

        for arg_name in arguments:
            if arg_name not in params:
                return False, f"Unknown parameter: {arg_name}"

        return True, None
