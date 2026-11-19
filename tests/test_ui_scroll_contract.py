import unittest

from tools.check_ui_scroll_contract import check


class ScrollContractCoverage(unittest.TestCase):
    def setUp(self):
        self.short = dict(page='page', size='900x640', owner='text', state='short')
        self.long = dict(self.short, state='long')
        self.short_measurement = dict(self.short, viewport_height=100, content_height=80,
                                      max_offset=0, scrollbar_visible=False, measurement_source='Tk')
        self.long_measurement = dict(self.long, viewport_height=100, content_height=400,
                                     max_offset=300, scrollbar_visible=True, thumb_fraction=.25,
                                     measurement_source='Tk')

    def check_rows(self, *rows):
        return check(dict(coverage_complete=True, regions=list(rows)), [self.short, self.long])

    def test_expected_cases_pass(self):
        self.assertEqual(self.check_rows(self.short_measurement, self.long_measurement), [])

    def test_declared_complete_cannot_hide_missing_or_duplicate_case(self):
        errors = self.check_rows(self.short_measurement, self.short_measurement)
        self.assertIn('漏測：page / 900x640 / text / long', errors)
        self.assertIn('重複量測：page / 900x640 / text / short', errors)

    def test_detect_wrong_viewport_and_incorrect_measured_offset(self):
        errors = self.check_rows(self.short_measurement, dict(self.long_measurement, size='1280x720', max_offset=0))
        self.assertIn('漏測：page / 900x640 / text / long', errors)
        self.assertIn('未列入預期情境：page / 1280x720 / text / long', errors)
        self.assertTrue(any('行程' in error for error in errors))

    def test_legacy_contract_without_size_still_works(self):
        row = self.short_measurement.copy()
        del row['size']
        self.assertEqual(check(dict(coverage_complete=True, regions=[row])), [])
