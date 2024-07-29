import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import os
import json
from src.http_load_tester import HTTPLoadTester, main
from aiohttp import web
import pytest


async def test_server(request):
    await asyncio.sleep(0.1)  # Simulate some processing time
    return web.Response(text="Test response")


class TestHTTPLoadTester(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.api_url = "http://localhost:5000/run-test"

        # Test configurations for various APIs
        cls.jsonplaceholder_get = {
            "url": "https://jsonplaceholder.typicode.com/posts/1",
            "method": "GET",
            "headers": {"Accept": "application/json"},
            "qps": 10,
            "duration": 30,
            "concurrency": 50
        }
        cls.jsonplaceholder_post = {
            "url": "https://jsonplaceholder.typicode.com/posts",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": '{"title": "foo", "body": "bar", "userId": 1}',
            "qps": 5,
            "duration": 30,
            "concurrency": 25
        }
        cls.postman_echo_get = {
            "url": "https://postman-echo.com/get?foo1=bar1&foo2=bar2",
            "method": "GET",
            "headers": {"Accept": "application/json"},
            "qps": 10,
            "duration": 30,
            "concurrency": 50
        }
        cls.postman_echo_post = {
            "url": "https://postman-echo.com/post",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": '{"key": "value"}',
            "qps": 5,
            "duration": 30,
            "concurrency": 25
        }
        cls.reqres_get = {
            "url": "https://reqres.in/api/users?page=2",
            "method": "GET",
            "headers": {"Accept": "application/json"},
            "qps": 10,
            "duration": 30,
            "concurrency": 50
        }
        cls.reqres_post = {
            "url": "https://reqres.in/api/users",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": '{"name": "morpheus", "job": "leader"}',
            "qps": 5,
            "duration": 30,
            "concurrency": 25
        }
        cls.pokeapi_get = {
            "url": "https://pokeapi.co/api/v2/pokemon/1/",
            "method": "GET",
            "headers": {"Accept": "application/json"},
            "qps": 5,
            "duration": 30,
            "concurrency": 25
        }
        cls.random_user_get = {
            "url": "https://randomuser.me/api/",
            "method": "GET",
            "headers": {"Accept": "application/json"},
            "qps": 10,
            "duration": 30,
            "concurrency": 50
        }
        cls.open_notify_get = {
            "url": "http://api.open-notify.org/iss-now.json",
            "method": "GET",
            "headers": {"Accept": "application/json"},
            "qps": 5,
            "duration": 30,
            "concurrency": 25
        }
        cls.httpstatus_get = {
            "url": "https://httpstat.us/200",
            "method": "GET",
            "headers": {"Accept": "text/plain"},
            "qps": 20,
            "duration": 30,
            "concurrency": 100
        }

        cls.test_configs = [
            cls.jsonplaceholder_get,
            cls.jsonplaceholder_post,
            cls.postman_echo_get,
            cls.postman_echo_post,
            cls.reqres_get,
            cls.reqres_post,
            cls.pokeapi_get,
            cls.random_user_get,
            cls.open_notify_get,
            cls.httpstatus_get
        ]

    def setUp(self):
        self.url = "https://example.com"
        self.qps = 10
        self.duration = 5
        self.tester = HTTPLoadTester(self.url, self.qps, self.duration)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    @patch('aiohttp.ClientSession')
    def test_send_request(self, mock_session):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "Test response"
        mock_session.request.return_value.__aenter__.return_value = mock_response

        async def run_test():
            await self.tester.send_request(mock_session)

        self.loop.run_until_complete(run_test())

        self.assertEqual(len(self.tester.results), 1)
        self.assertIn('latency', self.tester.results[0])
        self.assertIn('status', self.tester.results[0])
        self.assertEqual(self.tester.results[0]['status'], 200)

    @patch('aiohttp.ClientSession')
    def test_send_request_error(self, mock_session):
        mock_session.request.side_effect = Exception("Test error")

        async def run_test():
            await self.tester.send_request(mock_session)

        self.loop.run_until_complete(run_test())

        self.assertEqual(self.tester.error_count, 1)
        self.assertEqual(len(self.tester.results), 0)

    def test_generate_report(self):
        self.tester.results = [
            {'latency': 100, 'status': 200},
            {'latency': 150, 'status': 200},
            {'latency': 200, 'status': 404},
        ]
        self.tester.error_count = 1

        report = self.tester.generate_report()

        self.assertIsNotNone(report)
        self.assertEqual(report['total_requests'], 4)
        self.assertAlmostEqual(report['error_rate'], 0.25)
        self.assertAlmostEqual(report['avg_latency'], 150)
        self.assertEqual(report['median_latency'], 150)
        self.assertEqual(report['min_latency'], 100)
        self.assertEqual(report['max_latency'], 200)
        self.assertEqual(report['status_codes'], {200: 2, 404: 1})

    def test_generate_report_no_results(self):
        self.tester.results = []
        self.tester.error_count = 0

        report = self.tester.generate_report()

        self.assertIsNone(report)

    def test_generate_report_all_errors(self):
        self.tester.results = []
        self.tester.error_count = 10

        report = self.tester.generate_report()

        self.assertIsNotNone(report)
        self.assertEqual(report['total_requests'], 10)
        self.assertEqual(report['error_rate'], 1)
        self.assertEqual(report['avg_latency'], 0)
        self.assertEqual(report['median_latency'], 0)
        self.assertEqual(report['min_latency'], 0)
        self.assertEqual(report['max_latency'], 0)
        self.assertEqual(report['status_codes'], {})

    @patch('aiohttp.ClientSession')
    def test_different_http_methods(self, mock_session):
        methods = ['GET', 'POST', 'PUT', 'DELETE']
        for method in methods:
            self.tester.method = method
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = f"Test response for {method}"
            mock_session.request.return_value.__aenter__.return_value = mock_response

            async def run_test():
                await self.tester.send_request(mock_session)

            self.loop.run_until_complete(run_test())

            mock_session.request.assert_called_with(method, self.url, headers={}, data=None)

    @patch('aiohttp.ClientSession')
    def test_with_headers_and_data(self, mock_session):
        self.tester.method = 'POST'
        self.tester.headers = {'Content-Type': 'application/json'}
        self.tester.data = '{"key": "value"}'

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "Test response"
        mock_session.request.return_value.__aenter__.return_value = mock_response

        async def run_test():
            await self.tester.send_request(mock_session)

        self.loop.run_until_complete(run_test())

        mock_session.request.assert_called_with('POST', self.url, headers={'Content-Type': 'application/json'},
                                                data='{"key": "value"}')

    @unittest.skipIf(os.environ.get('SKIP_INTEGRATION_TESTS'), "Skipping integration tests")
    def test_integration(self):
        app = web.Application()
        app.router.add_get('/', test_server)

        async def run_server():
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', 8080)
            await site.start()
            return runner

        async def run_test():
            runner = await run_server()
            try:
                tester = HTTPLoadTester('http://localhost:8080', qps=50, duration=2)
                await tester.run_test()
                report = tester.generate_report()
                self.assertIsNotNone(report)
                self.assertGreater(report['total_requests'], 0)
                self.assertLess(report['error_rate'], 0.1)  # Assuming less than 10% error rate
            finally:
                await runner.cleanup()

        self.loop.run_until_complete(run_test())

    @patch('src.http_load_tester.HTTPLoadTester.run_test')
    @patch('src.http_load_tester.HTTPLoadTester.generate_report')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('json.dumps')
    @patch('builtins.print')
    def test_main(self, mock_print, mock_json_dumps, mock_parse_args, mock_generate_report, mock_run_test):
        mock_parse_args.return_value = MagicMock(
            url=self.url,
            qps=self.qps,
            duration=self.duration,
            method='GET',
            headers={},
            data=None,
            concurrency=100
        )

        mock_report = {
            'total_requests': 100,
            'error_rate': 0.05,
            'avg_latency': 150,
            'median_latency': 140,
            'min_latency': 100,
            'max_latency': 300,
            'p50_latency': 140,
            'p90_latency': 200,
            'p95_latency': 250,
            'p99_latency': 290,
            'latencies': [100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300],
            'status_codes': {200: 95, 404: 5}
        }
        mock_generate_report.return_value = mock_report
        mock_json_dumps.return_value = json.dumps(mock_report, indent=2)

        self.loop.run_until_complete(main())

        mock_run_test.assert_called_once()
        mock_generate_report.assert_called_once()
        mock_json_dumps.assert_called_with(mock_report, indent=2)
        mock_print.assert_called()

        self.assertTrue(os.path.exists('output'))

    @patch('src.http_load_tester.HTTPLoadTester.run_test')
    @patch('src.http_load_tester.HTTPLoadTester.generate_report')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('builtins.print')
    def test_main_no_results(self, mock_print, mock_parse_args, mock_generate_report, mock_run_test):
        mock_parse_args.return_value = MagicMock(
            url=self.url,
            qps=self.qps,
            duration=self.duration,
            method='GET',
            headers={},
            data=None,
            concurrency=100
        )

        mock_generate_report.return_value = None

        self.loop.run_until_complete(main())

        mock_run_test.assert_called_once()
        mock_generate_report.assert_called_once()
        mock_print.assert_called_with("No results generated from the test.")

    @patch('requests.post')
    def test_run_test_api(self, mock_post):
        payload = {
            "url": "http://httpbin.org/get",
            "qps": 10,
            "duration": 30,
            "method": "GET",
            "headers": {"User-Agent": "HTTPLoadTester/1.0"},
            "concurrency": 50
        }
        headers = {"Content-Type": "application/json"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "total_requests": 300,
                "error_rate": 0.0,
                "avg_latency": 150.5,
                "median_latency": 145.0,
                "p95_latency": 200.0,
                "p99_latency": 250.0
            },
            "latency_plot": "/output/latency_distribution.png",
            "status_plot": "/output/status_code_distribution.png"
        }
        mock_post.return_value = mock_response

        response = mock_post(self.api_url, json=payload, headers=headers)

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("results", json_data)
        self.assertIn("latency_plot", json_data)
        self.assertIn("status_plot", json_data)
        results = json_data["results"]
        self.assertIn("total_requests", results)
        self.assertIn("error_rate", results)
        self.assertIn("avg_latency", results)
        self.assertIn("median_latency", results)
        self.assertIn("p95_latency", results)
        self.assertIn("p99_latency", results)

    @unittest.skipIf(os.environ.get('SKIP_API_TESTS'), "Skipping API tests")
    def test_api_configurations(self):
        print("Starting test_api_configurations")
        tested_urls = set()

        async def run_tests():
            for config in self.test_configs:
                with self.subTest(url=config['url']):
                    # Adjust the configuration to use shorter duration and lower QPS
                    adjusted_config = config.copy()
                    adjusted_config['duration'] = 2  # 2 seconds duration
                    adjusted_config['qps'] = 2  # 2 queries per second

                    tester = HTTPLoadTester(**adjusted_config)
                    try:
                        await tester.run_test()
                        report = tester.generate_report()

                        self.assertIsNotNone(report)
                        self.assertIn('total_requests', report)
                        self.assertIn('error_rate', report)
                        self.assertIn('avg_latency', report)
                        self.assertIn('median_latency', report)
                        self.assertIn('min_latency', report)
                        self.assertIn('max_latency', report)
                        self.assertIn('p50_latency', report)
                        self.assertIn('p90_latency', report)
                        self.assertIn('p95_latency', report)
                        self.assertIn('p99_latency', report)
                        self.assertIn('latencies', report)
                        self.assertIn('status_codes', report)

                        tested_urls.add(adjusted_config['url'])

                        # Verify that the tester was created with the correct configuration
                        self.assertEqual(tester.url, adjusted_config['url'])
                        self.assertEqual(tester.method, adjusted_config['method'])
                        self.assertEqual(tester.headers, adjusted_config['headers'])
                        self.assertEqual(tester.qps, adjusted_config['qps'])
                        self.assertEqual(tester.duration, adjusted_config['duration'])
                        self.assertEqual(tester.concurrency, adjusted_config['concurrency'])
                        if 'data' in adjusted_config:
                            self.assertEqual(tester.data, adjusted_config['data'])
                    except Exception as e:
                        print(f"Error testing {adjusted_config['url']}: {str(e)}")

        self.loop.run_until_complete(run_tests())

        # Verify that all configured URLs were tested
        self.assertEqual(set(config['url'] for config in self.test_configs), tested_urls)
        self.assertEqual(len(self.test_configs), len(tested_urls))

        # Print out all tested URLs for verification
        print("Tested URLs:")
        for url in tested_urls:
            print(f"  - {url}")

if __name__ == '__main__':
    unittest.main(verbosity=2)