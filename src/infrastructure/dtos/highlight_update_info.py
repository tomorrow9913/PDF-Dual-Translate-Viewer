from typing import Dict

class HighlightUpdateInfo:
    def __init__(self, segments_to_update: Dict[str, bool]):
        self.segments_to_update = segments_to_update
