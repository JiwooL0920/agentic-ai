"""HTTP request tool with URL allowlist."""

from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from ..base import BaseTool, ToolParameter, ToolParameterType, ToolResult

logger = structlog.get_logger()

REQUEST_TIMEOUT_SECONDS = 30
MAX_RESPONSE_SIZE_BYTES = 1024 * 1024

DEFAULT_ALLOWED_DOMAINS = [
    "api.github.com",
    "pypi.org",
    "registry.npmjs.org",
    "crates.io",
    "hub.docker.com",
    "api.duckduckgo.com",
]


class HttpRequestTool(BaseTool):
    def __init__(self, allowed_domains: list[str] | None = None) -> None:
        super().__init__(
            name="http_request",
            description="Make HTTP requests to allowed URLs",
        )
        self._logger = logger.bind(tool=self.name)
        self._allowed_domains = allowed_domains or DEFAULT_ALLOWED_DOMAINS

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="url",
                param_type=ToolParameterType.STRING,
                description="The URL to request",
                required=True,
            ),
            ToolParameter(
                name="method",
                param_type=ToolParameterType.STRING,
                description="HTTP method (GET, POST, PUT, DELETE)",
                required=False,
                default="GET",
                enum=["GET", "POST", "PUT", "DELETE"],
            ),
            ToolParameter(
                name="headers",
                param_type=ToolParameterType.OBJECT,
                description="Request headers as key-value pairs",
                required=False,
            ),
            ToolParameter(
                name="body",
                param_type=ToolParameterType.STRING,
                description="Request body for POST/PUT requests",
                required=False,
            ),
        ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        url: str = kwargs.get("url", "")
        method: str = kwargs.get("method", "GET")
        headers: dict[str, str] | None = kwargs.get("headers")
        body: str | None = kwargs.get("body")

        if not url:
            return ToolResult(success=False, error="Missing required parameter: url")

        self._logger.info("http_request", url=url, method=method)

        validation_error = self._validate_url(url)
        if validation_error:
            return ToolResult(success=False, error=validation_error)

        method = method.upper()
        if method not in ("GET", "POST", "PUT", "DELETE"):
            return ToolResult(success=False, error=f"Invalid HTTP method: {method}")

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                request_kwargs: dict[str, Any] = {
                    "method": method,
                    "url": url,
                    "headers": headers or {},
                }

                if body and method in ("POST", "PUT"):
                    request_kwargs["content"] = body

                response = await client.request(**request_kwargs)

                content_length = len(response.content)
                if content_length > MAX_RESPONSE_SIZE_BYTES:
                    return ToolResult(
                        success=False,
                        error=f"Response too large: {content_length} bytes",
                    )

                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text,
                }

                return ToolResult(success=True, output=result)

        except httpx.TimeoutException:
            self._logger.error("request_timeout", url=url)
            return ToolResult(success=False, error="Request timed out")
        except httpx.RequestError as e:
            self._logger.error("request_error", url=url, error=str(e))
            return ToolResult(success=False, error=f"Request failed: {e}")
        except Exception as e:
            self._logger.error("http_error", error=str(e))
            return ToolResult(success=False, error=str(e))

    def _validate_url(self, url: str) -> str | None:
        try:
            parsed = urlparse(url)
        except ValueError:
            return "Invalid URL format"

        if parsed.scheme not in ("http", "https"):
            return f"Invalid URL scheme: {parsed.scheme}"

        if not parsed.netloc:
            return "URL must include a domain"

        domain = parsed.netloc.lower()
        if ":" in domain:
            domain = domain.split(":")[0]

        if domain not in self._allowed_domains:
            return f"Domain not in allowlist: {domain}"

        return None

    def add_allowed_domain(self, domain: str) -> None:
        if domain not in self._allowed_domains:
            self._allowed_domains.append(domain)

    def get_allowed_domains(self) -> list[str]:
        return self._allowed_domains.copy()
