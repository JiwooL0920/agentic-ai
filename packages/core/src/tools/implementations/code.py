"""Sandboxed code execution tool."""

import ast
import asyncio
import io
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

import structlog

from ..base import BaseTool, ToolParameter, ToolParameterType, ToolResult

logger = structlog.get_logger()

EXECUTION_TIMEOUT_SECONDS = 10
MAX_OUTPUT_LENGTH = 10000

FORBIDDEN_IMPORTS = {
    "os", "subprocess", "sys", "shutil", "pathlib",
    "socket", "requests", "urllib", "http",
    "multiprocessing", "threading", "ctypes",
    "pickle", "marshal", "shelve",
    "importlib", "__import__",
}

FORBIDDEN_BUILTINS = {
    "exec", "eval", "compile", "open", "input",
    "__import__", "breakpoint", "exit", "quit",
}


class CodeExecuteTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="code_execute",
            description="Execute Python code in a sandboxed environment",
        )
        self._logger = logger.bind(tool=self.name)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                param_type=ToolParameterType.STRING,
                description="Python code to execute",
                required=True,
            ),
        ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        code: str = kwargs.get("code", "")

        if not code:
            return ToolResult(success=False, error="Missing required parameter: code")

        self._logger.info("executing_code", code_length=len(code))

        validation_error = self._validate_code(code)
        if validation_error:
            return ToolResult(success=False, error=validation_error)

        try:
            result = await asyncio.wait_for(
                self._run_code(code),
                timeout=EXECUTION_TIMEOUT_SECONDS,
            )
            return result
        except TimeoutError:
            self._logger.warning("code_execution_timeout")
            return ToolResult(
                success=False,
                error=f"Code execution timed out after {EXECUTION_TIMEOUT_SECONDS} seconds",
            )

    def _validate_code(self, code: str) -> str | None:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"Syntax error: {e}"

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in FORBIDDEN_IMPORTS:
                        return f"Import of '{module}' is not allowed"

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module in FORBIDDEN_IMPORTS:
                        return f"Import from '{module}' is not allowed"

            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in FORBIDDEN_BUILTINS
            ):
                return f"Use of '{node.func.id}' is not allowed"

        return None

    async def _run_code(self, code: str) -> ToolResult:
        def execute_in_sandbox() -> tuple[str, str, Any]:
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            safe_builtins = {
                k: v for k, v in __builtins__.items()
                if k not in FORBIDDEN_BUILTINS
            } if isinstance(__builtins__, dict) else {
                k: getattr(__builtins__, k) for k in dir(__builtins__)
                if k not in FORBIDDEN_BUILTINS and not k.startswith("_")
            }

            sandbox_globals: dict[str, Any] = {
                "__builtins__": safe_builtins,
                "__name__": "__sandbox__",
            }

            result = None
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                try:
                    compiled = compile(code, "<sandbox>", "exec")
                    exec(compiled, sandbox_globals)

                    if "_result" in sandbox_globals:
                        result = sandbox_globals["_result"]
                except Exception as e:
                    stderr_capture.write(f"{type(e).__name__}: {e}")

            return stdout_capture.getvalue(), stderr_capture.getvalue(), result

        loop = asyncio.get_event_loop()
        stdout, stderr, result = await loop.run_in_executor(None, execute_in_sandbox)

        output_parts = []
        if stdout:
            output_parts.append(f"Output:\n{stdout[:MAX_OUTPUT_LENGTH]}")
        if result is not None:
            output_parts.append(f"Result: {result}")
        if stderr:
            output_parts.append(f"Errors:\n{stderr[:MAX_OUTPUT_LENGTH]}")

        if not output_parts:
            output_parts.append("Code executed successfully with no output.")

        output = "\n\n".join(output_parts)

        success = not stderr
        return ToolResult(
            success=success,
            output=output if success else None,
            error=stderr if not success else None,
        )
