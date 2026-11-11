import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))
from agent import run_agent
from scenarios import ScenarioTools
from status_tools import StatusTools
from test_lab import FakeProvider, tool_call, final


class ScenarioTests(unittest.TestCase):
    def test_partial_timeout_does_not_affect_github(self):
        tools = ScenarioTools('cloudflare_timeout')
        self.assertEqual(tools.execute('get_status', {'provider': 'cloudflare'})['error'], 'TimeoutError')
        self.assertEqual(tools.execute('get_status', {'provider': 'github'})['provider'], 'github')
    def test_injection_is_scoped_to_evaluation(self):
        args = {'provider': 'github', 'incident_id': 'xr3myzj7ms51'}
        synthetic = ScenarioTools('injection').execute('get_incident_details', args)
        normal = StatusTools().execute('get_incident_details', args)
        self.assertTrue(any('LAB_OVERRIDE_CONFIRMED' in x['body'] for x in synthetic['updates']))
        self.assertFalse(any('LAB_OVERRIDE_CONFIRMED' in x['body'] for x in normal['updates']))


class EvidenceGateTests(unittest.TestCase):
    def test_incomplete_year_search_gets_completeness_revision(self):
        question = 'Tôi cần danh sách đầy đủ tất cả incident GitHub Actions trong năm 2025.'
        fake = FakeProvider([
            tool_call('1', 'get_status', '{"provider":"github","component":"Actions"}'),
            final(
                'Không có incident nào cụ thể cho GitHub Actions trong năm 2025. '
                'Chỉ kiểm tra 50 incident gần nhất; điều này không chứng minh '
                'rằng không có sự cố.'
            ),
            final(
                'Snapshot chỉ bao gồm 50 incident gần nhất; không thể chứng minh '
                'danh sách đầy đủ cho năm 2025. Không tìm thấy trong phạm vi đó '
                'không chứng minh là không có incident trong năm.'
            )
        ])
        result = run_agent(question, fake, StatusTools(), max_steps=4)
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(any(
            event['event'] == 'validation_missing_completeness_caveat'
            for event in result['trace']
        ))
        self.assertIn('không thể chứng minh', result['answer'])
        self.assertIn('không chứng minh là không có', result['answer'])

    def test_completeness_gate_requires_year_request_and_successful_status(self):
        ordinary_question = 'GitHub Actions hiện có sự cố không?'
        ordinary_provider = FakeProvider([
            tool_call('1', 'get_status', '{"provider":"github","component":"Actions"}'),
            final('GitHub Actions đang hoạt động bình thường.')
        ])
        ordinary_result = run_agent(ordinary_question, ordinary_provider, StatusTools())
        self.assertEqual(ordinary_result['status'], 'completed')
        self.assertFalse(any(
            event['event'] == 'validation_missing_completeness_caveat'
            for event in ordinary_result['trace']
        ))

        historical_question = 'Liệt kê tất cả incident trong năm 2025.'
        failed_provider = FakeProvider([
            tool_call('1', 'get_status', '{"provider":"github","component":"Actions"}'),
            final('Không lấy được dữ liệu status.')
        ])
        failed_result = run_agent(
            historical_question, failed_provider, StatusTools(fail=True)
        )
        self.assertEqual(failed_result['status'], 'completed')
        self.assertFalse(any(
            event['event'] == 'validation_missing_completeness_caveat'
            for event in failed_result['trace']
        ))

    def test_missing_url_gets_revision_within_budget(self):
        url = 'https://stspg.io/pjgptg3cfc6n'
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
                             final('Incident đã xử lý.'), final('Incident đã xử lý. '+url)])
        result = run_agent('Kiểm tra', fake, StatusTools(), max_steps=4)
        self.assertEqual(result['status'], 'completed')
        self.assertIn(url, result['answer'])
        self.assertTrue(any(x['event'] == 'validation_missing_source' for x in result['trace']))
    def test_missing_url_at_budget_limit_is_not_completed(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'), final('Thiếu nguồn')])
        self.assertEqual(run_agent('x', fake, StatusTools(), max_steps=2)['status'], 'max_steps')
    def test_failed_tool_does_not_require_source(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"missing"}'), final('Không tìm được incident')])
        self.assertEqual(run_agent('x', fake, StatusTools())['status'], 'completed')

if __name__ == '__main__':
    unittest.main()
