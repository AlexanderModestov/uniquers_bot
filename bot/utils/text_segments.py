from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import re
from pathlib import Path

@dataclass
class TextSegment:
    text: str
    speaker: str
    start_time: str  # Format: "HH:MM:SS"
    end_time: str    # Format: "HH:MM:SS"
    video_file: str

class SegmentManager:
    def __init__(self):
        self.segments: List[TextSegment] = []
    
    def load_segments(self, file_path: str):
        """Load segments from a JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.segments = [
                    TextSegment(**segment) for segment in data
                ]
        except Exception as e:
            print(f"Error loading segments: {e}")
            return False
        return True

    def search_segments(self, query: str) -> List[Dict]:
        """
        Search through segments and return matching ones with video references
        Returns: List of dicts with segment info and video reference
        """
        results = []
        query = query.lower()
        
        for segment in self.segments:
            if query in segment.text.lower():
                results.append({
                    'text': segment.text,
                    'speaker': segment.speaker,
                    'timestamp': f"{segment.start_time} - {segment.end_time}",
                    'video_file': segment.video_file
                })
        
        return results

    def format_search_result(self, results: List[Dict]) -> str:
        """Format search results into a readable message"""
        if not results:
            return "No matching segments found."
        
        formatted = "Found relevant segments:\n\n"
        for i, result in enumerate(results, 1):
            formatted += (
                f"{i}. Speaker: {result['speaker']}\n"
                f"   Time: {result['timestamp']}\n"
                f"   Video: {result['video_file']}\n"
                f"   Text: {result['text']}\n\n"
            )
        return formatted
