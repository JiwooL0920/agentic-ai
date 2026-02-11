"""Web search tool using DuckDuckGo."""

from typing import Any

import httpx
import structlog

from ..base import BaseTool, ToolParameter, ToolParameterType, ToolResult

logger = structlog.get_logger()

DUCKDUCKGO_API_URL = "https://api.duckduckgo.com/"


class WebSearchTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="web_search",
            description="Search the web for information using DuckDuckGo",
        )
        self._logger = logger.bind(tool=self.name)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                param_type=ToolParameterType.STRING,
                description="The search query",
                required=True,
            ),
            ToolParameter(
                name="max_results",
                param_type=ToolParameterType.INTEGER,
                description="Maximum number of results to return",
                required=False,
                default=5,
            ),
        ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        query: str = kwargs.get("query", "")
        max_results: int = kwargs.get("max_results", 5)

        if not query:
            return ToolResult(success=False, error="Missing required parameter: query")

        self._logger.info("searching", query=query, max_results=max_results)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    DUCKDUCKGO_API_URL,
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []

            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", ""),
                    "snippet": data["Abstract"],
                    "url": data.get("AbstractURL", ""),
                })

            for topic in data.get("RelatedTopics", [])[:max_results]:
                if "Text" in topic:
                    results.append({
                        "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                        "snippet": topic["Text"],
                        "url": topic.get("FirstURL", ""),
                    })

            if not results:
                return ToolResult(
                    success=True,
                    output="No results found for the query.",
                )

            formatted = self._format_results(results[:max_results])
            return ToolResult(success=True, output=formatted)

        except httpx.TimeoutException:
            self._logger.error("search_timeout", query=query)
            return ToolResult(success=False, error="Search request timed out")
        except httpx.HTTPStatusError as e:
            self._logger.error("search_http_error", status=e.response.status_code)
            return ToolResult(success=False, error=f"HTTP error: {e.response.status_code}")
        except Exception as e:
            self._logger.error("search_error", error=str(e))
            return ToolResult(success=False, error=str(e))

    def _format_results(self, results: list[dict[str, str]]) -> str:
        lines = []
        for i, result in enumerate(results, 1):
            lines.append(f"{i}. {result['title']}")
            lines.append(f"   {result['snippet']}")
            if result["url"]:
                lines.append(f"   URL: {result['url']}")
            lines.append("")
        return "\n".join(lines)
