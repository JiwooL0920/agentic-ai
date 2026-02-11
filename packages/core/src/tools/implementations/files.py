"""File reading tool with path restrictions."""

from pathlib import Path
from typing import Any

import structlog

from ..base import BaseTool, ToolParameter, ToolParameterType, ToolResult

logger = structlog.get_logger()

MAX_FILE_SIZE_BYTES = 1024 * 1024
MAX_OUTPUT_LINES = 500

ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".html", ".css", ".xml", ".csv", ".log", ".sh", ".bash",
    ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
    ".sql", ".graphql", ".toml", ".ini", ".cfg", ".conf",
}


class FileReadTool(BaseTool):
    def __init__(self, allowed_directories: list[str] | None = None) -> None:
        super().__init__(
            name="file_read",
            description="Read the contents of a file",
        )
        self._logger = logger.bind(tool=self.name)
        self._allowed_directories = allowed_directories or []

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                param_type=ToolParameterType.STRING,
                description="Path to the file to read",
                required=True,
            ),
            ToolParameter(
                name="start_line",
                param_type=ToolParameterType.INTEGER,
                description="Starting line number (1-based, optional)",
                required=False,
            ),
            ToolParameter(
                name="end_line",
                param_type=ToolParameterType.INTEGER,
                description="Ending line number (inclusive, optional)",
                required=False,
            ),
        ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        path: str = kwargs.get("path", "")
        start_line: int | None = kwargs.get("start_line")
        end_line: int | None = kwargs.get("end_line")

        if not path:
            return ToolResult(success=False, error="Missing required parameter: path")

        self._logger.info("reading_file", path=path)

        try:
            file_path = Path(path).resolve()
        except (ValueError, OSError) as e:
            return ToolResult(success=False, error=f"Invalid path: {e}")

        validation_error = self._validate_path(file_path)
        if validation_error:
            return ToolResult(success=False, error=validation_error)

        try:
            file_size = file_path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                return ToolResult(
                    success=False,
                    error=f"File too large: {file_size} bytes (max {MAX_FILE_SIZE_BYTES})",
                )

            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            if start_line is not None or end_line is not None:
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                lines = lines[start:end]

            if len(lines) > MAX_OUTPUT_LINES:
                lines = lines[:MAX_OUTPUT_LINES]
                lines.append(f"\n... (truncated, showing first {MAX_OUTPUT_LINES} lines)")

            return ToolResult(success=True, output="\n".join(lines))

        except FileNotFoundError:
            return ToolResult(success=False, error=f"File not found: {path}")
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")
        except UnicodeDecodeError:
            return ToolResult(success=False, error="File is not valid UTF-8 text")
        except Exception as e:
            self._logger.error("file_read_error", error=str(e))
            return ToolResult(success=False, error=str(e))

    def _validate_path(self, file_path: Path) -> str | None:
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return f"File type not allowed: {file_path.suffix}"

        if ".." in str(file_path):
            return "Path traversal not allowed"

        if self._allowed_directories:
            allowed = False
            for allowed_dir in self._allowed_directories:
                try:
                    file_path.relative_to(Path(allowed_dir).resolve())
                    allowed = True
                    break
                except ValueError:
                    continue

            if not allowed:
                return "File is outside allowed directories"

        return None
