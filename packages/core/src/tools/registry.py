"""Tool registry for managing available tools."""

from typing import Any

import structlog

from .base import BaseTool

logger = structlog.get_logger()


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._initialized: bool = False

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            logger.warning("tool_already_registered", name=tool.name)
            return

        self._tools[tool.name] = tool
        logger.info("tool_registered", name=tool.name)

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            logger.info("tool_unregistered", name=name)
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all(self) -> dict[str, BaseTool]:
        return self._tools.copy()

    def get_tools_for_agent(self, tool_names: list[str]) -> list[BaseTool]:
        tools = []
        for name in tool_names:
            tool = self.get(name)
            if tool:
                tools.append(tool)
            else:
                logger.warning("tool_not_found_for_agent", name=name)
        return tools

    def get_ollama_tools(self, tool_names: list[str]) -> list[dict[str, Any]]:
        tools = self.get_tools_for_agent(tool_names)
        return [tool.to_ollama_format() for tool in tools]

    def clear(self) -> None:
        self._tools.clear()
        logger.info("registry_cleared")

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    def is_registered(self, name: str) -> bool:
        return name in self._tools


_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_builtin_tools() -> None:
    from .implementations import (
        CodeExecuteTool,
        FileReadTool,
        HttpRequestTool,
        WebSearchTool,
    )

    registry = get_tool_registry()

    if registry._initialized:
        return

    registry.register(WebSearchTool())
    registry.register(CodeExecuteTool())
    registry.register(FileReadTool())
    registry.register(HttpRequestTool())

    registry._initialized = True
    logger.info("builtin_tools_registered", count=registry.tool_count)
