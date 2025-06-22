class PdfPageService:
    @staticmethod
    def update_highlights(current_segments, hovered_segment_id):
        """
        하이라이트 동기화 로직: hovered_segment_id에 해당하는 세그먼트만 True, 나머지는 False로 반환
        """
        return {
            seg_id: (seg_id == hovered_segment_id)
            for seg_id in current_segments
        }
