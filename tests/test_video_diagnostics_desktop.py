"""Failure evidence is available through the existing details action."""
from unittest.mock import patch
import unittest
import test_total_video_desktop as fixture

class DiagnosticDesktop(unittest.TestCase):
    setUp=fixture.TotalVideoDesktop.setUp
    prepare=fixture.TotalVideoDesktop.prepare
    refresh_voices=fixture.TotalVideoDesktop.refresh_voices
    audio=fixture.TotalVideoDesktop.audio
    shutdown=fixture.TotalVideoDesktop.shutdown
    wait_page=fixture.TotalVideoDesktop.wait_page

    def test_existing_details_shows_failure_reason_and_recovery(self):
        self.app.batch_video()
        page=self.app.production.current;self.wait_page(page)
        diagnostic=dict(message='製片空間不足。請清出空間 → 重試製片。',phase='製作影片',detail='No space left on device')
        with patch.object(page.video_flow,'total_video_runs',return_value=[dict(progress=dict(diagnostic=diagnostic))]):
            page.detail_button.invoke()
        text=page.details_text.get('1.0','end')
        self.assertIn('No space left on device',text)
        self.assertIn('清出空間',text)
        self.assertIn('本批音訊',text)
