from typing import Dict, List, Optional


class PdfPageService:
    @staticmethod
    def update_highlights(
        all_segment_ids: List[str], hovered_segment_id: Optional[str]
    ) -> Dict[str, bool]:
        """
        Determines which segments to highlight based on the hovered segment.
        """
        segments_to_update = {segment_id: False for segment_id in all_segment_ids}
        if hovered_segment_id and hovered_segment_id in segments_to_update:
            segments_to_update[hovered_segment_id] = True
        return segments_to_update
