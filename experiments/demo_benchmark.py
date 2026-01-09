"""
Quick Demonstration Benchmark
Tests 3 websites and generates visual comparison report

Usage: python experiments/demo_benchmark.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import ClonerSDK
import time
import json
from datetime import datetime
from typing import Dict, List
import webbrowser

class DemoBenchmark:
    """Quick benchmark for demonstration purposes"""

    def __init__(self):
        self.results = []

    def run_demo(self):
        """Run quick 3-site demo"""

        print("=" * 60)
        print("WEBSITE CLONER - QUICK BENCHMARK DEMO")
        print("=" * 60)
        print()

        # Test sites (ordered by complexity)
        test_sites = {
            "Static HTML": "https://example.com",
            "React SPA": "https://react.dev",
            "WordPress": "https://wordpress.org/news",
        }

        for site_type, url in test_sites.items():
            print(f"\n{'='*60}")
            print(f"Testing: {site_type}")
            print(f"URL: {url}")
            print(f"{'='*60}\n")

            result = self.clone_and_measure(site_type, url)
            self.results.append(result)

            # Print immediate results
            self.print_result(result)

            print("\n⏳ Cooling down (5 seconds)...\n")
            time.sleep(5)

        # Generate report
        print("\n" + "=" * 60)
        print("📊 Generating Report...")
        print("=" * 60 + "\n")

        self.generate_report()

    def clone_and_measure(self, site_type: str, url: str) -> Dict:
        """Clone a site and measure metrics"""

        result = {
            "site_type": site_type,
            "url": url,
            "timestamp": datetime.now().isoformat(),
        }

        # Initialize cloner
        cloner = ClonerSDK(headless=True)

        # Track metrics via events
        metrics = {
            "total_resources": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "skipped_downloads": 0,
            "file_types": {},
            "progress_updates": [],
        }

        @cloner.on_start
        def on_start(data):
            print(f"🟢 Clone started: {data.url}")
            result["start_time"] = time.time()

        @cloner.on_progress
        def on_progress(data):
            print(f"⏳ [{data.percentage:5.1f}%] {data.stage}: {data.message}")
            metrics["progress_updates"].append({
                "percentage": data.percentage,
                "stage": data.stage,
                "message": data.message,
            })

        @cloner.on_complete
        def on_complete(data):
            result["end_time"] = time.time()
            result["duration_seconds"] = data.duration_seconds
            result["output_path"] = data.output_path

            metrics["total_resources"] = data.total_resources
            metrics["successful_downloads"] = data.successful_downloads
            metrics["failed_downloads"] = data.failed_downloads
            metrics["skipped_downloads"] = data.skipped_downloads

            print(f"✅ Clone completed in {data.duration_seconds:.1f}s")
            print(f"📦 Downloaded: {data.successful_downloads}/{data.total_resources} assets")

        @cloner.on_resource_downloaded
        def on_download(data):
            # Track file types
            file_type = data.file_type or "unknown"
            if file_type not in metrics["file_types"]:
                metrics["file_types"][file_type] = {"count": 0, "examples": []}

            metrics["file_types"][file_type]["count"] += 1
            if len(metrics["file_types"][file_type]["examples"]) < 3:
                metrics["file_types"][file_type]["examples"].append(data.url)

        @cloner.on_resource_failed
        def on_failed(data):
            print(f"Failed: {data.url[:80]}... - {data.error}")

        @cloner.on_error
        def on_error(data):
            print(f"ERROR: {data.error}")
            result["error"] = str(data.error)
            result["traceback"] = data.traceback

        try:
            # Run clone
            output_path = cloner.clone(url)

            # Calculate metrics
            result["success"] = True
            result["metrics"] = metrics
            result["success_rate"] = (
                metrics["successful_downloads"] / metrics["total_resources"]
                if metrics["total_resources"] > 0 else 0
            )

            # Get output size
            total_size = sum(f.stat().st_size for f in Path(output_path).rglob('*') if f.is_file())
            result["output_size_mb"] = total_size / 1024 / 1024

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            print(f"🚨 Clone failed: {e}")

        return result

    def print_result(self, result: Dict):
        """Print formatted result"""

        if not result.get("success"):
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
            return

        metrics = result["metrics"]

        print(f"\n📊 Results:")
        print(f"  ⏱️  Duration: {result['duration_seconds']:.1f}s")
        print(f"  ✅ Success Rate: {result['success_rate']*100:.1f}%")
        print(f"  📦 Assets: {metrics['successful_downloads']}/{metrics['total_resources']}")
        print(f"  ❌ Failed: {metrics['failed_downloads']}")
        print(f"  💾 Size: {result['output_size_mb']:.2f} MB")
        print(f"  📁 Output: {result['output_path']}")

        if metrics["file_types"]:
            print(f"\n  📋 File Types Breakdown:")
            sorted_types = sorted(
                metrics["file_types"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )
            for file_type, data in sorted_types[:5]:  # Top 5
                print(f"     - {file_type}: {data['count']} files")

    def generate_report(self):
        """Generate HTML report with visualizations"""

        # Save raw results
        results_file = Path("experiments/demo_results.json")
        results_file.parent.mkdir(exist_ok=True)

        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"💾 Raw results saved: {results_file}")

        # Generate HTML report
        html = self.create_html_report()

        report_file = Path("experiments/demo_report.html")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"📄 HTML report generated: {report_file}")
        print(f"\n🌐 Opening report in browser...")

        # Open in browser
        webbrowser.open(f"file://{report_file.absolute()}")

        # Print summary table
        self.print_summary_table()

    def create_html_report(self) -> str:
        """Create beautiful HTML report"""

        # Prepare data for charts
        labels = [r["site_type"] for r in self.results if r.get("success")]
        success_rates = [r["success_rate"] * 100 for r in self.results if r.get("success")]
        durations = [r["duration_seconds"] for r in self.results if r.get("success")]
        sizes = [r["output_size_mb"] for r in self.results if r.get("success")]

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Website Cloner - Demo Benchmark Results</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            font-size: 2.5em;
            color: #667eea;
            margin-bottom: 10px;
            text-align: center;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 1.1em;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}
        .card h3 {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .card .value {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        .charts {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }}
        .chart-container {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
        }}
        .chart-container h3 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .success {{ color: #10b981; font-weight: bold; }}
        .failed {{ color: #ef4444; font-weight: bold; }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #eee;
            text-align: center;
            color: #666;
        }}
        .emoji {{ font-size: 1.3em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Website Cloner Benchmark</h1>
        <p class="subtitle">Quick demonstration testing 3 website architectures</p>

        <div class="summary-cards">
            <div class="card">
                <h3>Average Success Rate</h3>
                <div class="value">{sum(success_rates)/len(success_rates):.1f}%</div>
            </div>
            <div class="card">
                <h3>Total Assets Downloaded</h3>
                <div class="value">{sum(r["metrics"]["successful_downloads"] for r in self.results if r.get("success"))}</div>
            </div>
            <div class="card">
                <h3>Average Duration</h3>
                <div class="value">{sum(durations)/len(durations):.1f}s</div>
            </div>
            <div class="card">
                <h3>Total Output Size</h3>
                <div class="value">{sum(sizes):.1f} MB</div>
            </div>
        </div>

        <div class="charts">
            <div class="chart-container">
                <h3>📊 Success Rate by Site Type</h3>
                <canvas id="successChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>⏱️ Clone Duration by Site Type</h3>
                <canvas id="durationChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>💾 Output Size by Site Type</h3>
                <canvas id="sizeChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>📦 Assets Downloaded</h3>
                <canvas id="assetsChart"></canvas>
            </div>
        </div>

        <h2 style="margin-top: 40px; margin-bottom: 20px; color: #333;">Detailed Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Site Type</th>
                    <th>URL</th>
                    <th>Success Rate</th>
                    <th>Duration</th>
                    <th>Assets</th>
                    <th>Size</th>
                </tr>
            </thead>
            <tbody>
                {"".join([
                    f'''<tr>
                        <td><strong>{r["site_type"]}</strong></td>
                        <td>{r["url"]}</td>
                        <td class="success">{r["success_rate"]*100:.1f}%</td>
                        <td>{r["duration_seconds"]:.1f}s</td>
                        <td>{r["metrics"]["successful_downloads"]}/{r["metrics"]["total_resources"]}</td>
                        <td>{r["output_size_mb"]:.2f} MB</td>
                    </tr>'''
                    for r in self.results if r.get("success")
                ])}
            </tbody>
        </table>

        <div class="footer">
            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p style="margin-top: 10px;">Website Cloner v2.0 - Built with ❤️ and Python</p>
        </div>
    </div>

    <script>
        const chartConfig = {{
            responsive: true,
            maintainAspectRatio: true,
            plugins: {{
                legend: {{ display: false }}
            }}
        }};

        // Success Rate Chart
        new Chart(document.getElementById('successChart'), {{
            type: 'bar',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: 'Success Rate (%)',
                    data: {success_rates},
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                }}]
            }},
            options: {{ ...chartConfig, scales: {{ y: {{ beginAtZero: true, max: 100 }} }} }}
        }});

        // Duration Chart
        new Chart(document.getElementById('durationChart'), {{
            type: 'bar',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: 'Duration (seconds)',
                    data: {durations},
                    backgroundColor: 'rgba(118, 75, 162, 0.8)',
                }}]
            }},
            options: {{ ...chartConfig, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        // Size Chart
        new Chart(document.getElementById('sizeChart'), {{
            type: 'bar',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: 'Size (MB)',
                    data: {sizes},
                    backgroundColor: 'rgba(16, 185, 129, 0.8)',
                }}]
            }},
            options: {{ ...chartConfig, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        // Assets Chart
        new Chart(document.getElementById('assetsChart'), {{
            type: 'doughnut',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: 'Assets Downloaded',
                    data: {[r["metrics"]["successful_downloads"] for r in self.results if r.get("success")]},
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(16, 185, 129, 0.8)',
                    ]
                }}]
            }},
            options: chartConfig
        }});
    </script>
</body>
</html>
"""

    def print_summary_table(self):
        """Print ASCII summary table"""

        print("\n" + "=" * 80)
        print("SUMMARY TABLE")
        print("=" * 80)
        print(f"{'Site Type':<20} {'Success Rate':<15} {'Duration':<15} {'Assets':<15}")
        print("-" * 80)

        for result in self.results:
            if result.get("success"):
                print(
                    f"{result['site_type']:<20} "
                    f"{result['success_rate']*100:>6.1f}%        "
                    f"{result['duration_seconds']:>6.1f}s        "
                    f"{result['metrics']['successful_downloads']:>4}/{result['metrics']['total_resources']:<4}"
                )

        print("=" * 80)

        # Key insights
        print("\n💡 KEY INSIGHTS:")

        success_rates = [r["success_rate"] for r in self.results if r.get("success")]
        avg_success = sum(success_rates) / len(success_rates) * 100

        print(f"  • Average success rate: {avg_success:.1f}%")

        # Find best/worst
        best = max(self.results, key=lambda x: x.get("success_rate", 0) if x.get("success") else 0)
        worst = min(self.results, key=lambda x: x.get("success_rate", 1) if x.get("success") else 1)

        print(f"  • Best performance: {best['site_type']} ({best['success_rate']*100:.1f}%)")
        print(f"  • Needs improvement: {worst['site_type']} ({worst['success_rate']*100:.1f}%)")

        print("\n")


if __name__ == "__main__":
    benchmark = DemoBenchmark()
    benchmark.run_demo()
