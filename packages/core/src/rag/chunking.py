"""
Document chunking strategies for RAG.

Provides text, markdown, and code-aware chunking with configurable
chunk sizes and overlap to preserve semantic boundaries.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypedDict


class MarkdownSection(TypedDict):
    """Type for markdown section dictionary."""

    heading: str | None
    level: int
    content: str


@dataclass
class Chunk:
    """A chunk of text from a document.

    Attributes:
        content: The chunk text content.
        index: Chunk index within the document.
        metadata: Additional metadata (start_line, end_line, section, etc.).
    """

    content: str
    index: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        """Get character count."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())


class BaseChunker(ABC):
    """Base class for document chunkers."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        """Initialize chunker.

        Args:
            chunk_size: Target chunk size in characters.
            chunk_overlap: Overlap between chunks in characters.
            min_chunk_size: Minimum chunk size (smaller chunks are merged).
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    @abstractmethod
    def chunk(self, text: str) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: Text to chunk.

        Returns:
            List of chunks.
        """
        pass


class TextChunker(BaseChunker):
    """Simple text chunker that splits on sentence/paragraph boundaries.

    Tries to preserve semantic boundaries by preferring splits at:
    1. Paragraph breaks (double newline)
    2. Sentence ends (. ! ?)
    3. Other punctuation (, ; :)
    4. Word boundaries
    """

    # Regex patterns for split points, ordered by preference
    SPLIT_PATTERNS = [
        r"\n\n+",  # Paragraph breaks
        r"(?<=[.!?])\s+",  # Sentence ends
        r"(?<=[,;:])\s+",  # Other punctuation
        r"\s+",  # Word boundaries
    ]

    def chunk(self, text: str) -> list[Chunk]:
        """Split text into chunks at semantic boundaries."""
        if not text or not text.strip():
            return []

        text = text.strip()

        # If text fits in one chunk, return it
        if len(text) <= self.chunk_size:
            return [Chunk(content=text, index=0)]

        chunks: list[Chunk] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            # Calculate end position
            end = min(start + self.chunk_size, len(text))

            # If we're not at the end, find a good split point
            if end < len(text):
                split_point = self._find_split_point(text, start, end)
                if split_point > start:
                    end = split_point

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    Chunk(
                        content=chunk_text,
                        index=chunk_index,
                        metadata={"start_char": start, "end_char": end},
                    )
                )
                chunk_index += 1

            # Move start position (with overlap)
            start = max(start + 1, end - self.chunk_overlap)

        return self._merge_small_chunks(chunks)

    def _find_split_point(self, text: str, start: int, end: int) -> int:
        """Find the best split point in the text range."""
        # Look for split points in the last portion of the chunk
        search_start = max(start, end - self.chunk_overlap)
        search_text = text[search_start:end]

        for pattern in self.SPLIT_PATTERNS:
            matches = list(re.finditer(pattern, search_text))
            if matches:
                # Use the last match (closest to end)
                last_match = matches[-1]
                return search_start + last_match.end()

        return end

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge chunks that are too small."""
        if not chunks:
            return chunks

        merged: list[Chunk] = []

        for chunk in chunks:
            if merged and len(chunk.content) < self.min_chunk_size:
                # Merge with previous chunk
                merged[-1] = Chunk(
                    content=merged[-1].content + "\n\n" + chunk.content,
                    index=merged[-1].index,
                    metadata={
                        "start_char": merged[-1].metadata.get("start_char", 0),
                        "end_char": chunk.metadata.get("end_char", 0),
                        "merged": True,
                    },
                )
            else:
                merged.append(chunk)

        return merged


class MarkdownChunker(BaseChunker):
    """Markdown-aware chunker that respects document structure.

    Preserves:
    - Heading hierarchy
    - Code blocks
    - Lists
    - Blockquotes
    """

    # Regex patterns for markdown elements
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
    LIST_PATTERN = re.compile(r"^(\s*[-*+]|\s*\d+\.)\s+", re.MULTILINE)

    def chunk(self, text: str) -> list[Chunk]:
        """Split markdown into chunks respecting structure."""
        if not text or not text.strip():
            return []

        text = text.strip()

        # Split by headings first
        sections = self._split_by_headings(text)

        chunks: list[Chunk] = []
        chunk_index = 0

        for section in sections:
            section_chunks = self._chunk_section(section, chunk_index)
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        return self._merge_small_chunks(chunks)

    def _split_by_headings(self, text: str) -> list[MarkdownSection]:
        """Split text into sections by headings."""
        sections: list[MarkdownSection] = []
        current_section: MarkdownSection = {"heading": None, "level": 0, "content": ""}

        lines = text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for heading
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match:
                # Save current section if it has content
                if current_section["content"].strip():
                    sections.append(current_section)

                # Start new section
                current_section = {
                    "heading": heading_match.group(2),
                    "level": len(heading_match.group(1)),
                    "content": line + "\n",
                }
            else:
                current_section["content"] += line + "\n"

            i += 1

        # Save final section
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def _chunk_section(self, section: MarkdownSection, start_index: int) -> list[Chunk]:
        """Chunk a single section, preserving code blocks."""
        content = section["content"]

        if len(content) <= self.chunk_size:
            return [
                Chunk(
                    content=content.strip(),
                    index=start_index,
                    metadata={
                        "heading": section.get("heading"),
                        "level": section.get("level"),
                    },
                )
            ]

        # Protect code blocks from being split
        code_blocks: list[str] = []
        placeholder_prefix = "<<<CODE_BLOCK_"

        def replace_code_block(match: re.Match[str]) -> str:
            code_blocks.append(match.group(0))
            return f"{placeholder_prefix}{len(code_blocks) - 1}>>>"

        protected_content = self.CODE_BLOCK_PATTERN.sub(replace_code_block, content)

        # Use text chunker for the protected content
        text_chunker = TextChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            min_chunk_size=self.min_chunk_size,
        )
        text_chunks = text_chunker.chunk(protected_content)

        # Restore code blocks
        chunks: list[Chunk] = []
        for i, text_chunk in enumerate(text_chunks):
            restored_content = text_chunk.content
            for j, code_block in enumerate(code_blocks):
                restored_content = restored_content.replace(
                    f"{placeholder_prefix}{j}>>>", code_block
                )

            chunks.append(
                Chunk(
                    content=restored_content,
                    index=start_index + i,
                    metadata={
                        "heading": section.get("heading"),
                        "level": section.get("level"),
                        **text_chunk.metadata,
                    },
                )
            )

        return chunks

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge small chunks while preserving section boundaries."""
        if not chunks:
            return chunks

        merged: list[Chunk] = []

        for chunk in chunks:
            if (
                merged
                and len(chunk.content) < self.min_chunk_size
                and merged[-1].metadata.get("heading") == chunk.metadata.get("heading")
            ):
                # Merge with previous chunk if same section
                merged[-1] = Chunk(
                    content=merged[-1].content + "\n\n" + chunk.content,
                    index=merged[-1].index,
                    metadata={**merged[-1].metadata, "merged": True},
                )
            else:
                merged.append(chunk)

        return merged


class CodeChunker(BaseChunker):
    """Code-aware chunker that respects syntax boundaries.

    Preserves:
    - Function/class definitions
    - Import blocks
    - Comments and docstrings
    """

    # Common language patterns
    PYTHON_PATTERNS = {
        "function": re.compile(r"^(\s*)(async\s+)?def\s+\w+", re.MULTILINE),
        "class": re.compile(r"^(\s*)class\s+\w+", re.MULTILINE),
        "import": re.compile(r"^(import\s+|from\s+\w+\s+import\s+)", re.MULTILINE),
    }

    JS_PATTERNS = {
        "function": re.compile(
            r"^(\s*)(async\s+)?function\s+\w+|"
            r"^(\s*)(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s+)?\(",
            re.MULTILINE,
        ),
        "class": re.compile(r"^(\s*)(export\s+)?class\s+\w+", re.MULTILINE),
        "import": re.compile(r"^import\s+|^export\s+", re.MULTILINE),
    }

    LANGUAGE_PATTERNS = {
        "python": PYTHON_PATTERNS,
        "py": PYTHON_PATTERNS,
        "javascript": JS_PATTERNS,
        "js": JS_PATTERNS,
        "typescript": JS_PATTERNS,
        "ts": JS_PATTERNS,
        "tsx": JS_PATTERNS,
        "jsx": JS_PATTERNS,
    }

    def __init__(
        self,
        language: str = "python",
        chunk_size: int = 1500,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        """Initialize code chunker.

        Args:
            language: Programming language (python, javascript, etc.).
            chunk_size: Target chunk size in characters.
            chunk_overlap: Overlap between chunks in characters.
            min_chunk_size: Minimum chunk size.
        """
        super().__init__(chunk_size, chunk_overlap, min_chunk_size)
        self.language = language.lower()
        self.patterns = self.LANGUAGE_PATTERNS.get(self.language, self.PYTHON_PATTERNS)

    def chunk(self, text: str) -> list[Chunk]:
        """Split code into chunks at syntax boundaries."""
        if not text or not text.strip():
            return []

        text = text.strip()

        # If text fits in one chunk, return it
        if len(text) <= self.chunk_size:
            return [
                Chunk(content=text, index=0, metadata={"language": self.language})
            ]

        # Find all definition boundaries
        boundaries = self._find_boundaries(text)

        # If no boundaries found, fall back to text chunker
        if not boundaries:
            text_chunker = TextChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                min_chunk_size=self.min_chunk_size,
            )
            chunks = text_chunker.chunk(text)
            for chunk in chunks:
                chunk.metadata["language"] = self.language
            return chunks

        # Split at boundaries
        chunks = self._split_at_boundaries(text, boundaries)
        return self._merge_small_chunks(chunks)

    def _find_boundaries(self, text: str) -> list[int]:
        """Find code structure boundaries (function/class definitions)."""
        boundaries: set[int] = {0}  # Always include start

        for _pattern_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                boundaries.add(match.start())

        return sorted(boundaries)

    def _split_at_boundaries(self, text: str, boundaries: list[int]) -> list[Chunk]:
        """Split text at the given boundaries."""
        chunks: list[Chunk] = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for i, boundary in enumerate(boundaries):
            next_boundary = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
            segment = text[boundary:next_boundary]

            # Check if adding segment exceeds chunk size
            if len(current_chunk) + len(segment) > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(
                    Chunk(
                        content=current_chunk.strip(),
                        index=chunk_index,
                        metadata={
                            "language": self.language,
                            "start_char": current_start,
                            "end_char": boundary,
                        },
                    )
                )
                chunk_index += 1

                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + segment
                current_start = boundary - (len(current_chunk) - len(segment))
            else:
                current_chunk += segment

        # Save final chunk
        if current_chunk.strip():
            chunks.append(
                Chunk(
                    content=current_chunk.strip(),
                    index=chunk_index,
                    metadata={
                        "language": self.language,
                        "start_char": current_start,
                        "end_char": len(text),
                    },
                )
            )

        return chunks

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge chunks that are too small."""
        if not chunks:
            return chunks

        merged: list[Chunk] = []

        for chunk in chunks:
            if merged and len(chunk.content) < self.min_chunk_size:
                # Merge with previous chunk
                merged[-1] = Chunk(
                    content=merged[-1].content + "\n\n" + chunk.content,
                    index=merged[-1].index,
                    metadata={
                        **merged[-1].metadata,
                        "end_char": chunk.metadata.get("end_char", 0),
                        "merged": True,
                    },
                )
            else:
                merged.append(chunk)

        return merged


def get_chunker(
    file_type: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> BaseChunker:
    """Get appropriate chunker for file type.

    Args:
        file_type: File type or extension (e.g., "md", "py", "txt").
        chunk_size: Target chunk size.
        chunk_overlap: Overlap between chunks.

    Returns:
        Appropriate chunker instance.
    """
    file_type = file_type.lower().lstrip(".")

    if file_type in ("md", "markdown"):
        return MarkdownChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    elif file_type in ("py", "python", "js", "javascript", "ts", "typescript", "tsx", "jsx"):
        return CodeChunker(
            language=file_type, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
    else:
        return TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
