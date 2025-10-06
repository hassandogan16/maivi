"""
Maia - My AI Assistant
A voice-to-text application with real-time transcription.
"""

__version__ = "0.1.0"
__author__ = "Maxime Rivest"

from maia.core.chunk_merger import SimpleChunkMerger
from maia.core.streaming_recorder import StreamingRecorder

__all__ = ["SimpleChunkMerger", "StreamingRecorder", "__version__"]
