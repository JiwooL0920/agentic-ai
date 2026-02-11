"""Tool executor for handling tool calls from LLM responses."""

from typing import Any

import structlog

from .base import BaseTool, ToolCall, ToolResult
from .registry import ToolRegistry, get_tool_registry

logger = structlog.get_logger()

MAX_TOOL_ITERATIONS = 5


class ToolExecutionError(Exception):
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class ToolExecutor:
    def __init__(self, registry: ToolRegistry | None = None):
        self._registry = registry or get_tool_registry()
        self._logger = logger.bind(component="ToolExecutor")

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        tool = self._registry.get(tool_call.tool_name)

        if not tool:
            self._logger.warning("tool_not_found", name=tool_call.tool_name)
            return ToolResult(
                success=False,
                error=f"Tool '{tool_call.tool_name}' not found",
            )

        valid, error = tool.validate_arguments(tool_call.arguments)
        if not valid:
            self._logger.warning(
                "invalid_arguments",
                tool=tool_call.tool_name,
                error=error,
            )
            return ToolResult(success=False, error=error)

        try:
            self._logger.info(
                "executing_tool",
                tool=tool_call.tool_name,
                call_id=tool_call.call_id,
            )

            result = await tool.execute(**tool_call.arguments)

            self._logger.info(
                "tool_executed",
                tool=tool_call.tool_name,
                success=result.success,
            )

            return result

        except Exception as e:
            self._logger.error(
                "tool_execution_error",
                tool=tool_call.tool_name,
                error=str(e),
            )
            return ToolResult(success=False, error=str(e))

    async def execute_tools(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        results = []
        for call in tool_calls:
            result = await self.execute_tool(call)
            results.append(result)
        return results

    def parse_tool_calls_from_response(
        self, response: dict[str, Any]
    ) -> list[ToolCall]:
        message = response.get("message", {})
        raw_tool_calls = message.get("tool_calls", [])

        tool_calls = []
        for i, tc in enumerate(raw_tool_calls):
            function = tc.get("function", {})
            tool_calls.append(
                ToolCall(
                    tool_name=function.get("name", ""),
                    arguments=function.get("arguments", {}),
                    call_id=str(i),
                )
            )

        return tool_calls

    def has_tool_calls(self, response: dict[str, Any]) -> bool:
        message = response.get("message", {})
        tool_calls = message.get("tool_calls", [])
        return len(tool_calls) > 0

    def build_tool_response_message(
        self, tool_call: ToolCall, result: ToolResult
    ) -> dict[str, Any]:
        return {
            "role": "tool",
            "content": result.to_message(),
            "name": tool_call.tool_name,
        }

    def get_available_tools(self) -> list[BaseTool]:
        return list(self._registry.get_all().values())
