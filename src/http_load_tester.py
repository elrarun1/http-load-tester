import argparse
import asyncio
import aiohttp
import time
import statistics
from collections import Counter
from typing import List, Dict, Any
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')

class HTTPLoadTester:
    def __init__(self, url: str, qps: int, duration: int = 60,
                 method: str = 'GET', headers: Dict[str, str] = None,
                 data: Any = None, concurrency: int = 100):
        self.url = url
        self.qps = qps
        self.duration = duration
        self.method = method
        self.headers = headers or {}
        self.data = data
        self.concurrency = concurrency
        self.results: List[Dict[str, Any]] = []
        self.error_count = 0

    async def run_test(self):
        start_time = time.time()
        tasks = []
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < self.duration:
                if len(tasks) < self.concurrency:
                    tasks.append(asyncio.create_task(self.send_request(session)))

                if len(tasks) >= self.qps:
                    done, pending = await asyncio.wait(tasks, timeout=1)
                    tasks = list(pending)

                await asyncio.sleep(1 / self.qps)

            # Wait for remaining tasks to complete
            await asyncio.gather(*tasks)

    async def send_request(self, session: aiohttp.ClientSession):
        start_time = time.time()
        try:
            async with session.request(self.method, self.url, headers=self.headers, data=self.data) as response:
                await response.text()
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # Convert to milliseconds
                self.results.append({
                    'latency': latency,
                    'status': response.status
                })
        except Exception as e:
            self.error_count += 1
            print(f"Error: {str(e)}")

    def generate_report(self):
        total_requests = len(self.results) + self.error_count
        if total_requests == 0:
            return None

        latencies = [result['latency'] for result in self.results]
        statuses = [result['status'] for result in self.results]

        error_rate = self.error_count / total_requests if total_requests > 0 else 1

        return {
            'total_requests': total_requests,
            'error_rate': error_rate,
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'median_latency': statistics.median(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'p50_latency': np.percentile(latencies, 50) if latencies else 0,
            'p90_latency': np.percentile(latencies, 90) if latencies else 0,
            'p95_latency': np.percentile(latencies, 95) if latencies else 0,
            'p99_latency': np.percentile(latencies, 99) if latencies else 0,
            'latencies': latencies,
            'status_codes': dict(Counter(statuses))
        }

    def plot_latency_distribution(self, latencies, p50, p90, p95, p99, output_path):
        plt.figure(figsize=(12, 6))

        # Plot histogram
        n, bins, patches = plt.hist(latencies, bins=50, edgecolor='black', alpha=0.7)

        # Color the bars based on percentiles
        for i, p in enumerate(patches):
            if bins[i] < p50:
                p.set_facecolor('green')
            elif bins[i] < p90:
                p.set_facecolor('yellow')
            elif bins[i] < p95:
                p.set_facecolor('orange')
            elif bins[i] < p99:
                p.set_facecolor('red')
            else:
                p.set_facecolor('purple')

        # Add percentile lines
        plt.axvline(p50, color='blue', linestyle='dashed', linewidth=2, label=f'50th Percentile: {p50:.2f} ms')
        plt.axvline(p90, color='yellow', linestyle='dashed', linewidth=2, label=f'90th Percentile: {p90:.2f} ms')
        plt.axvline(p95, color='orange', linestyle='dashed', linewidth=2, label=f'95th Percentile: {p95:.2f} ms')
        plt.axvline(p99, color='red', linestyle='dashed', linewidth=2, label=f'99th Percentile: {p99:.2f} ms')

        plt.title('Latency Distribution')
        plt.xlabel('Latency (ms)')
        plt.ylabel('Frequency')
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_path)
        plt.show()
        plt.close()

    def plot_status_code_distribution(self, statuses: List[int], output_path: str):
        status_counts = Counter(statuses)

        # Define common status codes and their categories
        status_categories = {
            '1xx': list(range(100, 200)),
            '2xx': list(range(200, 300)),
            '3xx': list(range(300, 400)),
            '4xx': list(range(400, 500)),
            '5xx': list(range(500, 600))
        }

        # Define colors for each category
        category_colors = {
            '1xx': 'blue',
            '2xx': 'green',
            '3xx': 'yellow',
            '4xx': 'orange',
            '5xx': 'red'
        }

        # Prepare data for plotting
        codes = []
        counts = []
        colors = []

        for status, count in sorted(status_counts.items()):
            codes.append(str(status))
            counts.append(count)
            for category, code_range in status_categories.items():
                if status in code_range:
                    colors.append(category_colors[category])
                    break
            else:
                colors.append('gray')  # For any unexpected status codes

        plt.figure(figsize=(12, 6))
        bars = plt.bar(codes, counts, color=colors)

        plt.title('Status Code Distribution')
        plt.xlabel('Status Code')
        plt.ylabel('Count')
        plt.xticks(rotation=45, ha='right')

        # Add value labels on top of each bar
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{int(height)}',
                     ha='center', va='bottom')

        # Add a legend
        legend_elements = [plt.Rectangle((0, 0), 1, 1, color=color, label=category)
                           for category, color in category_colors.items()]
        plt.legend(handles=legend_elements, title="Status Categories")

        plt.tight_layout()
        plt.savefig(output_path)
        plt.show()
        plt.close()

async def main():
    parser = argparse.ArgumentParser(description='HTTP Load Testing Tool')
    parser.add_argument('url', type=str, help='Target URL')
    parser.add_argument('--qps', type=int, default=10, help='Queries per second')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--method', type=str, default='GET', help='HTTP method')
    parser.add_argument('--headers', type=json.loads, default={}, help='HTTP headers as JSON')
    parser.add_argument('--data', type=str, help='Request body data')
    parser.add_argument('--concurrency', type=int, default=100, help='Maximum number of concurrent requests')

    args = parser.parse_args()

    load_tester = HTTPLoadTester(
        url=args.url,
        qps=args.qps,
        duration=args.duration,
        method=args.method,
        headers=args.headers,
        data=args.data,
        concurrency=args.concurrency
    )

    await load_tester.run_test()
    results = load_tester.generate_report()

    if results:
        print(json.dumps(results, indent=2))

        # Save plots
        os.makedirs('output', exist_ok=True)
        latency_plot_path = os.path.join('output', 'latency_distribution.png')
        status_plot_path = os.path.join('output', 'status_code_distribution.png')

        load_tester.plot_latency_distribution(
            results['latencies'],
            results['p50_latency'],
            results['p90_latency'],
            results['p95_latency'],
            results['p99_latency'],
            latency_plot_path
        )
        load_tester.plot_status_code_distribution(
            results['status_codes'],
            status_plot_path
        )

        print(f"\nLatency distribution plot saved to: {latency_plot_path}")
        print(f"Status code distribution plot saved to: {status_plot_path}")
    else:
        print("No results generated from the test.")


if __name__ == '__main__':
    asyncio.run(main())