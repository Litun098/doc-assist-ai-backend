from typing import List, Dict, Tuple, Optional, Union, Any
from datetime import datetime
import uuid
import re

from app.models.db_models import Chunk, FileType
from config.config import settings


class ChunkingStrategy:
    """Base class for chunking strategies"""
    name = "base"

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """Split text into chunks with metadata"""
        raise NotImplementedError("Subclasses must implement this method")


class FixedSizeChunker(ChunkingStrategy):
    """Chunker that splits text into fixed-size chunks with overlap"""
    name = "fixed_size"

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """Split text into fixed-size chunks with overlap"""
        if not text:
            return []

        metadata = metadata or {}
        chunks = []
        start = 0
        text_length = len(text)
        chunk_index = 0

        while start < text_length:
            end = min(start + self.chunk_size, text_length)

            # Try to find a good breaking point (newline or space)
            if end < text_length:
                # Look for newline first
                newline_pos = text.rfind("\n", start, end)
                if newline_pos > start:
                    end = newline_pos + 1
                else:
                    # Look for space
                    space_pos = text.rfind(" ", start, end)
                    if space_pos > start:
                        end = space_pos + 1

            # Create chunk text
            chunk_text = text[start:end]

            # Create chunk metadata
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunking_strategy": self.name,
                "chunk_index": chunk_index,
                "start_char": start,
                "end_char": end
            })

            # Add the chunk
            chunks.append((chunk_text, chunk_metadata))
            chunk_index += 1

            # Move the start position, considering overlap
            start = end - self.chunk_overlap if end < text_length else text_length

        return chunks


class TopicBasedChunker(ChunkingStrategy):
    """Chunker that splits text based on headings and topics"""
    name = "topic_based"

    def __init__(self, max_chunk_size: int = 2000, min_chunk_size: int = 100, heading_patterns: List[str] = None):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.heading_patterns = heading_patterns or settings.HEADING_PATTERNS
        self.compiled_patterns = [re.compile(pattern, re.MULTILINE) for pattern in self.heading_patterns]

    def _extract_headings(self, text: str) -> List[Tuple[int, int, str]]:
        """Extract headings and their positions from text"""
        headings = []

        # Find all headings using the patterns
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                heading_text = match.group(1) if len(match.groups()) >= 1 else match.group(0)
                headings.append((match.start(), match.end(), heading_text.strip()))

        # Sort headings by position
        headings.sort()

        return headings

    def _split_by_paragraphs(self, text: str, max_size: int) -> List[str]:
        """Split text into paragraphs, ensuring each is under max_size"""
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)

        # Further split any paragraphs that are too large
        result = []
        for para in paragraphs:
            if len(para) <= max_size:
                result.append(para)
            else:
                # Split large paragraph by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current = ""

                for sentence in sentences:
                    if len(current) + len(sentence) + 1 <= max_size:
                        if current:
                            current += " " + sentence
                        else:
                            current = sentence
                    else:
                        if current:
                            result.append(current)
                        current = sentence

                if current:
                    result.append(current)

        return result

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """Split text into topic-based chunks"""
        if not text:
            return []

        metadata = metadata or {}
        chunks = []
        chunk_index = 0

        # Extract headings
        headings = self._extract_headings(text)

        # If no headings found, fall back to paragraph-based chunking
        if not headings:
            paragraphs = self._split_by_paragraphs(text, self.max_chunk_size)

            for para in paragraphs:
                if len(para.strip()) < self.min_chunk_size:
                    continue

                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunking_strategy": self.name,
                    "chunk_index": chunk_index,
                    "heading": None
                })

                chunks.append((para, chunk_metadata))
                chunk_index += 1

            return chunks

        # Process each section (text between headings)
        for i in range(len(headings)):
            heading_start, heading_end, heading_text = headings[i]

            # Determine section end
            if i < len(headings) - 1:
                section_end = headings[i+1][0]
            else:
                section_end = len(text)

            # Extract section text (including the heading)
            section_text = text[heading_start:section_end]

            # If section is small enough, keep it as one chunk
            if len(section_text) <= self.max_chunk_size:
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunking_strategy": self.name,
                    "chunk_index": chunk_index,
                    "heading": heading_text,
                    "start_char": heading_start,
                    "end_char": section_end
                })

                chunks.append((section_text, chunk_metadata))
                chunk_index += 1
            else:
                # Split section into smaller chunks
                # First, separate the heading
                heading_chunk = text[heading_start:heading_end]
                section_content = text[heading_end:section_end]

                # Split the content by paragraphs
                paragraphs = self._split_by_paragraphs(section_content, self.max_chunk_size)

                # Add heading to the first paragraph
                if paragraphs:
                    paragraphs[0] = heading_chunk + "\n" + paragraphs[0]
                else:
                    paragraphs = [heading_chunk]

                # Create chunks from paragraphs
                for j, para in enumerate(paragraphs):
                    if len(para.strip()) < self.min_chunk_size and j > 0:
                        # Append small paragraphs to the previous chunk if possible
                        if chunks and len(chunks[-1][0]) + len(para) <= self.max_chunk_size:
                            prev_text, prev_metadata = chunks[-1]
                            chunks[-1] = (prev_text + "\n\n" + para, prev_metadata)
                            continue

                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunking_strategy": self.name,
                        "chunk_index": chunk_index,
                        "heading": heading_text,
                        "is_first_in_section": j == 0
                    })

                    chunks.append((para, chunk_metadata))
                    chunk_index += 1

        return chunks


class HybridChunker:
    """Hybrid chunking system that selects the appropriate chunking strategy"""

    def __init__(self):
        self.fixed_size_chunker = FixedSizeChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

        self.topic_based_chunker = TopicBasedChunker(
            max_chunk_size=settings.MAX_CHUNK_SIZE,
            min_chunk_size=settings.MIN_CHUNK_SIZE
        )

    def _select_chunking_strategy(self, file_type: FileType, content: str) -> ChunkingStrategy:
        """Select the appropriate chunking strategy based on file type and content"""
        # First, check if file type is explicitly mapped to a strategy
        if file_type in settings.TOPIC_BASED_FILETYPES:
            # For text-heavy documents, check if they have headings
            if self._has_headings(content):
                return self.topic_based_chunker

        if file_type in settings.FIXED_SIZE_FILETYPES:
            return self.fixed_size_chunker

        # Default to fixed-size chunking for unknown file types or no headings
        return self.fixed_size_chunker

    def _has_headings(self, content: str) -> bool:
        """Check if the content has headings"""
        for pattern in self.topic_based_chunker.compiled_patterns:
            if pattern.search(content):
                return True
        return False

    def chunk_text(self, text: str, file_type: FileType = None, metadata: Dict[str, Any] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """Chunk text using the appropriate strategy"""
        strategy = self._select_chunking_strategy(file_type, text)
        return strategy.chunk_text(text, metadata)


def fixed_size_chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Legacy function for backward compatibility"""
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # Try to find a good breaking point (newline or space)
        if end < text_length:
            # Look for newline first
            newline_pos = text.rfind("\n", start, end)
            if newline_pos > start:
                end = newline_pos + 1
            else:
                # Look for space
                space_pos = text.rfind(" ", start, end)
                if space_pos > start:
                    end = space_pos + 1

        # Add the chunk
        chunks.append(text[start:end])

        # Move the start position, considering overlap
        start = end - chunk_overlap if end < text_length else text_length

    return chunks


# For backward compatibility
chunk_text = fixed_size_chunk_text


def create_chunks_from_content(file_id: str, content: List[str], file_type: FileType = None) -> List[Chunk]:
    """Create chunks from file content using the hybrid chunking system"""
    chunks = []
    chunk_index = 0
    hybrid_chunker = HybridChunker()

    for page_num, page_content in enumerate(content):
        # Base metadata for this page
        base_metadata = {
            "page_number": page_num + 1,
            "file_id": file_id
        }

        # Use hybrid chunker to get chunks with metadata
        page_chunks = hybrid_chunker.chunk_text(
            text=page_content,
            file_type=file_type,
            metadata=base_metadata
        )

        # Create Chunk objects from the chunked content
        for chunk_text, chunk_metadata in page_chunks:
            # Update chunk index
            chunk_metadata["chunk_index"] = chunk_index

            chunk = Chunk(
                id=str(uuid.uuid4()),
                file_id=file_id,
                content=chunk_text,
                page_number=page_num + 1,
                chunk_index=chunk_index,
                created_at=datetime.now(),
                metadata=chunk_metadata
            )
            chunks.append(chunk)
            chunk_index += 1

    return chunks
