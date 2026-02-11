"""Tests for the tools module."""

import pytest

from src.tools.base import (
    ToolCall,
    ToolParameter,
    ToolParameterType,
    ToolResult,
)
from src.tools.executor import ToolExecutor
from src.tools.implementations import (
    CodeExecuteTool,
    FileReadTool,
    HttpRequestTool,
    WebSearchTool,
)
from src.tools.registry import ToolRegistry, get_tool_registry, register_builtin_tools


class TestToolParameter:
    def test_to_json_schema_string(self) -> None:
        param = ToolParameter(
            name="query",
            param_type=ToolParameterType.STRING,
            description="Search query",
            required=True,
        )
        schema = param.to_json_schema()
        assert schema == {"type": "string", "description": "Search query"}

    def test_to_json_schema_integer_with_default(self) -> None:
        param = ToolParameter(
            name="count",
            param_type=ToolParameterType.INTEGER,
            description="Number of items",
            required=False,
            default=10,
        )
        schema = param.to_json_schema()
        assert schema == {"type": "integer", "description": "Number of items", "default": 10}

    def test_to_json_schema_with_enum(self) -> None:
        param = ToolParameter(
            name="method",
            param_type=ToolParameterType.STRING,
            description="HTTP method",
            required=True,
            enum=["GET", "POST", "PUT", "DELETE"],
        )
        schema = param.to_json_schema()
        assert schema["enum"] == ["GET", "POST", "PUT", "DELETE"]


class TestToolResult:
    def test_to_message_success(self) -> None:
        result = ToolResult(success=True, output="Hello world")
        message = result.to_message()
        assert message == "Hello world"

    def test_to_message_error(self) -> None:
        result = ToolResult(success=False, error="Something went wrong")
        message = result.to_message()
        assert message == "Error: Something went wrong"

    def test_to_message_dict_output(self) -> None:
        result = ToolResult(success=True, output={"key": "value"})
        message = result.to_message()
        assert "'key': 'value'" in message


class TestToolRegistry:
    def test_register_and_get_tool(self) -> None:
        registry = ToolRegistry()
        tool = WebSearchTool()
        registry.register(tool)
        assert registry.get("web_search") == tool
        assert registry.is_registered("web_search")

    def test_unregister_tool(self) -> None:
        registry = ToolRegistry()
        tool = WebSearchTool()
        registry.register(tool)
        assert registry.unregister("web_search")
        assert registry.get("web_search") is None

    def test_get_tools_for_agent(self) -> None:
        registry = ToolRegistry()
        registry.register(WebSearchTool())
        registry.register(CodeExecuteTool())
        tools = registry.get_tools_for_agent(["web_search", "code_execute"])
        assert len(tools) == 2

    def test_get_ollama_tools(self) -> None:
        registry = ToolRegistry()
        registry.register(WebSearchTool())
        ollama_tools = registry.get_ollama_tools(["web_search"])
        assert len(ollama_tools) == 1
        assert ollama_tools[0]["type"] == "function"
        assert ollama_tools[0]["function"]["name"] == "web_search"

    def test_clear_registry(self) -> None:
        registry = ToolRegistry()
        registry.register(WebSearchTool())
        registry.clear()
        assert registry.tool_count == 0


class TestRegisterBuiltinTools:
    def test_registers_all_builtin_tools(self) -> None:
        registry = get_tool_registry()
        registry.clear()
        registry._initialized = False
        register_builtin_tools()
        assert registry.is_registered("web_search")
        assert registry.is_registered("code_execute")
        assert registry.is_registered("file_read")
        assert registry.is_registered("http_request")
        assert registry.tool_count == 4

    def test_idempotent_registration(self) -> None:
        registry = get_tool_registry()
        registry.clear()
        registry._initialized = False
        register_builtin_tools()
        register_builtin_tools()
        assert registry.tool_count == 4


class TestWebSearchTool:
    def test_ollama_format(self) -> None:
        tool = WebSearchTool()
        fmt = tool.to_ollama_format()
        assert fmt["function"]["name"] == "web_search"
        assert "query" in fmt["function"]["parameters"]["properties"]
        assert "query" in fmt["function"]["parameters"]["required"]

    @pytest.mark.asyncio
    async def test_missing_query_returns_error(self) -> None:
        tool = WebSearchTool()
        result = await tool.execute()
        assert not result.success
        assert "Missing required parameter" in (result.error or "")


class TestCodeExecuteTool:
    @pytest.mark.asyncio
    async def test_simple_execution(self) -> None:
        tool = CodeExecuteTool()
        result = await tool.execute(code="print('Hello, World!')")
        assert result.success
        assert "Hello, World!" in (result.output or "")

    @pytest.mark.asyncio
    async def test_forbidden_import(self) -> None:
        tool = CodeExecuteTool()
        result = await tool.execute(code="import os")
        assert not result.success
        assert "not allowed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_forbidden_builtin(self) -> None:
        tool = CodeExecuteTool()
        result = await tool.execute(code="eval('1+1')")
        assert not result.success
        assert "not allowed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_syntax_error(self) -> None:
        tool = CodeExecuteTool()
        result = await tool.execute(code="def foo(")
        assert not result.success
        assert "Syntax error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_result_variable(self) -> None:
        tool = CodeExecuteTool()
        result = await tool.execute(code="_result = 2 + 2")
        assert result.success
        assert "4" in (result.output or "")


class TestFileReadTool:
    @pytest.mark.asyncio
    async def test_file_not_found(self) -> None:
        tool = FileReadTool()
        result = await tool.execute(path="/nonexistent/file.txt")
        assert not result.success
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_forbidden_extension(self) -> None:
        tool = FileReadTool()
        result = await tool.execute(path="/some/file.exe")
        assert not result.success
        assert "not allowed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_missing_path(self) -> None:
        tool = FileReadTool()
        result = await tool.execute()
        assert not result.success
        assert "Missing required parameter" in (result.error or "")


class TestHttpRequestTool:
    @pytest.mark.asyncio
    async def test_invalid_domain(self) -> None:
        tool = HttpRequestTool()
        result = await tool.execute(url="https://evil.com/api")
        assert not result.success
        assert "not in allowlist" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invalid_method(self) -> None:
        tool = HttpRequestTool()
        result = await tool.execute(url="https://api.github.com/users", method="PATCH")
        assert not result.success
        assert "Invalid HTTP method" in (result.error or "")

    @pytest.mark.asyncio
    async def test_missing_url(self) -> None:
        tool = HttpRequestTool()
        result = await tool.execute()
        assert not result.success
        assert "Missing required parameter" in (result.error or "")

    def test_add_allowed_domain(self) -> None:
        tool = HttpRequestTool()
        tool.add_allowed_domain("example.com")
        domains = tool.get_allowed_domains()
        assert "example.com" in domains


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_execute_registered_tool(self) -> None:
        registry = get_tool_registry()
        registry.clear()
        registry._initialized = False
        register_builtin_tools()

        executor = ToolExecutor()
        tool_call = ToolCall(
            tool_name="code_execute",
            arguments={"code": "print('test')"},
            call_id="1",
        )
        result = await executor.execute_tool(tool_call)
        assert result.success

    @pytest.mark.asyncio
    async def test_execute_unregistered_tool(self) -> None:
        registry = get_tool_registry()
        registry.clear()
        registry._initialized = False
        register_builtin_tools()

        executor = ToolExecutor()
        tool_call = ToolCall(
            tool_name="nonexistent_tool",
            arguments={},
            call_id="1",
        )
        result = await executor.execute_tool(tool_call)
        assert not result.success
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_execute_multiple_tools(self) -> None:
        registry = get_tool_registry()
        registry.clear()
        registry._initialized = False
        register_builtin_tools()

        executor = ToolExecutor()
        tool_calls = [
            ToolCall(tool_name="code_execute", arguments={"code": "_result = 1"}, call_id="1"),
            ToolCall(tool_name="code_execute", arguments={"code": "_result = 2"}, call_id="2"),
        ]
        results = await executor.execute_tools(tool_calls)
        assert len(results) == 2
        assert all(r.success for r in results)
