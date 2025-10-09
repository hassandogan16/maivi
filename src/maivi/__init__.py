"""
Maivi - My AI Voice Input
A voice-to-text application with real-time transcription.
"""

__version__ = "0.4.1"
__author__ = "Maxime Rivest"

from maivi.core.chunk_merger import SimpleChunkMerger
from maivi.core.streaming_recorder import StreamingRecorder

__all__ = ["SimpleChunkMerger", "StreamingRecorder", "__version__"]
