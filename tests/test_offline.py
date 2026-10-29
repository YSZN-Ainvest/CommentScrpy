"""所有验证禁止真实网络；sleep 只在测试进程中替换。"""
import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(socket.socket, 'connect', side_effect=AssertionError('禁止网络'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.http = patch('requests.sessions.Session.request', side_effect=AssertionError('禁止HTTP'))
        self.http.start()
        self.addCleanup(self.http.stop)
        self.app = load('merged_crawler', 'test.py')
        self.index = load('merged_index', 'index_comp.py')

    def test_import_has_no_requests(self):
        self.assertTrue(callable(self.app.Updates))
        self.assertTrue(callable(self.index.get_hs300_codes))

    def test_retry_boundary_and_conservative_delay(self):
        loader = Mock(side_effect=[ValueError('模拟错误'), [(200, '新')], [(100, '旧')]])
        with patch.object(self.app.time, 'sleep') as sleep:
            result = self.app.Load_New_Comments('SH600000', 5, (6, 10), 100, loader)
        self.assertEqual(result, [(200, '新'), (100, '旧')])
        self.assertEqual([c.args[1] for c in loader.call_args_list], [1, 1, 2])
        self.assertEqual(sleep.call_count, 2)
        self.assertTrue(all(40 <= c.args[0] <= 60 for c in sleep.call_args_list))

    def test_attempt_limit_and_empty_page(self):
        loader = Mock(side_effect=ValueError('模拟错误'))
        with patch.object(self.app.time, 'sleep') as sleep:
            self.assertEqual(self.app.Load_New_Comments('SH600000', 3, Load_Comment=loader), [])
        self.assertEqual(loader.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        with patch.object(self.app.time, 'sleep') as sleep:
            self.assertEqual(self.app.Load_New_Comments('SH600000', Load_Comment=lambda *a: []), [])
        sleep.assert_not_called()

    def test_incremental_csv_and_platform_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            xue = Path(tmp) / 'xueqiu'
            dfcf = Path(tmp) / 'dfcf'
            self.app.Updates('SH600000', Load_Comment=lambda *a: [(100, '旧')], DATA_PATH=xue, max_search=1)
            loader = lambda *a: [(200, '新'), (200, '新'), (100, '旧')]
            self.app.Updates('SH600000', Load_Comment=loader, DATA_PATH=xue)
            self.app.Updates('SH600000', Load_Comment=lambda *a: [(300, '东方财富')], DATA_PATH=dfcf, max_search=1)
            result = self.app.pd.read_csv(xue / 'SH600000.csv')
            self.assertEqual(result['stamp'].tolist(), [200, 100])
            self.assertEqual(self.app.pd.read_csv(dfcf / 'SH600000.csv')['text'].tolist(), ['东方财富'])

    def test_platform_parsers(self):
        with patch.object(self.app.requests, 'get', return_value=Mock(text=json.dumps({'list': [{'created_at': 123, 'description': '雪球'}]}))) as get:
            self.assertEqual(self.app.Load_Comment_xueqiu('SH600000'), [(123, '雪球')])
            self.assertEqual(get.call_args.kwargs['params']['symbol'], 'SH600000')
        payload = {'re': [{'post_last_time': '2026-10-20 12:00:00', 'post_title': '东方财富'}]}
        with patch.object(self.app.requests, 'get', return_value=Mock(text='article_list='+json.dumps(payload)+';')) as get:
            self.assertEqual(self.app.Load_Comment_dfcf('SH600000')[0][1], '东方财富')
            self.assertEqual(get.call_args.args[0], 'https://guba.eastmoney.com/list,600000_1.html')

    def test_main_waits_after_failure(self):
        class StopLoop(BaseException):
            pass
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'HS300'
            path.write_text('SH600000\n')
            events = []
            def sleep(seconds):
                self.assertTrue(40 <= seconds <= 60)
                events.append('sleep')
                if len(events) == 4:
                    raise StopLoop()
            def update(*args):
                events.append('update')
                raise ValueError('模拟写入或请求异常')
            with patch.object(sys, 'argv', ['test.py']), patch.object(self.app, 'HS300_PATH', path), patch.object(self.app, 'BASE_PATH', Path(tmp)), patch.object(self.app.time, 'sleep', side_effect=sleep), patch.object(self.app, 'Updates', side_effect=update), patch.object(self.app.logging, 'FileHandler', return_value=unittest.mock.Mock()), patch.object(self.app.logging, 'basicConfig'):
                with self.assertRaises(StopLoop):
                    self.app.main()
            self.assertEqual(events, ['sleep', 'update', 'update', 'sleep'])

    def test_logs_include_platform_for_full_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            for source in ('雪球', '东方财富'):
                loader = Mock(side_effect=[ValueError('模拟失败'), [(200, '新增')], []])
                with self.assertLogs(self.app.logger, level='INFO') as captured, patch.object(self.app.time, 'sleep'), patch.object(self.app, 'Load_Comment_dfcf' if source == '东方财富' else 'Load_Comment_xueqiu', loader):
                    self.app.Updates('SH600000', max_search=3, Load_Comment=loader,
                                     DATA_PATH=Path(tmp) / source)
                messages = [record.getMessage() for record in captured.records]
                self.assertTrue(all(message.startswith(f'[{source}][SH600000]') for message in messages))
                for detail in ('本地档案不存在', '抓取失败', '无评论', '准备保存'):
                    self.assertTrue(any(detail in message for message in messages), detail)

    def test_index_retry_waits_one_second(self):
        session = Mock()
        session.get.side_effect = self.index.requests.RequestException("模拟失败")
        with patch.object(self.index.requests, 'Session', return_value=session), patch.object(self.index.time, 'sleep') as sleep:
            with self.assertRaises(self.index.requests.RequestException):
                self.index.get_hs300_codes()
        self.assertEqual(session.get.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 1])

    def test_index_pagination_and_union(self):
        session = Mock()
        responses = []
        for page in range(15):
            rows = [{'f12': f'{600000 + i:06}', 'f13': 1} for i in range(page * 20, (page + 1) * 20)]
            responses.append(Mock(json=Mock(return_value={'rc': 0, 'data': {'total': 300, 'diff': rows}})))
        session.get.side_effect = responses
        with patch.object(self.index.requests, 'Session', return_value=session), patch.object(self.index.time, 'sleep') as sleep:
            codes = self.index.get_hs300_codes()
        self.assertEqual(len(codes), 300)
        self.assertEqual(sleep.call_count, 14)
        self.assertTrue(all(c.args[0] == 1 for c in sleep.call_args_list))
        self.assertEqual(session.get.call_args.kwargs['params']['pz'], 20)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'HS300'
            path.write_text('SZ000001\n')
            with patch.object(self.index, 'HS300_PATH', path), patch.object(self.index, 'get_hs300_codes', return_value=codes), patch('builtins.print'):
                self.index.main()
            self.assertEqual(len(path.read_text().splitlines()), 301)
            self.assertIn('SZ000001', path.read_text())

if __name__ == '__main__':
    unittest.main()
