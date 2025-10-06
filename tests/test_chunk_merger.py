"""Tests for SimpleChunkMerger."""

import pytest
from maia.core.chunk_merger import SimpleChunkMerger


class TestSimpleChunkMerger:
    """Test cases for SimpleChunkMerger."""

    def test_first_chunk(self):
        """Test that first chunk is used as-is."""
        merger = SimpleChunkMerger()
        result = merger.add_chunk("hello world")
        assert result == "hello world"

    def test_overlapping_chunks(self):
        """Test merging of overlapping chunks."""
        merger = SimpleChunkMerger()
        merger.add_chunk("hello world how are you")
        result = merger.add_chunk("how are you doing today")
        assert result == "hello world how are you doing today"

    def test_no_overlap_adds_gap_marker(self):
        """Test that chunks with no overlap get gap marker."""
        merger = SimpleChunkMerger()
        merger.add_chunk("hello world")
        result = merger.add_chunk("completely different text")
        assert "..." in result

    def test_empty_chunk_ignored(self):
        """Test that empty chunks are ignored."""
        merger = SimpleChunkMerger()
        merger.add_chunk("hello world")
        result = merger.add_chunk("")
        assert result == "hello world"

    def test_reset(self):
        """Test that reset clears the merger state."""
        merger = SimpleChunkMerger()
        merger.add_chunk("hello world")
        merger.reset()
        assert merger.get_result() == ""

    def test_get_result(self):
        """Test getting the final result."""
        merger = SimpleChunkMerger()
        merger.add_chunk("hello world")
        merger.add_chunk("world how are you")
        result = merger.get_result()
        assert "hello" in result
        assert "you" in result
