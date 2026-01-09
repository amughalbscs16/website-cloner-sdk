"""
Core Experiment Engine for Website Cloner Benchmarking

This module provides the ExperimentRunner class for systematic testing
and benchmarking of the website cloner across different site types.
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Callable
from datetime import datetime
import time
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import ClonerSDK
from experiments.test_sites import TestSite


@dataclass
class ExperimentResult:
    """Complete result data from a single experiment"""

    # Site information
    site_name: str
    site_url: str
    site_category: str
    site_difficulty: str

    # Timing
    timestamp: str
    duration_seconds: float

    # Overall success
    success: bool
    error_message: Optional[str] = None

    # Resource statistics
    total_resources: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    success_rate: float = 0.0

    # File analysis
    output_path: Optional[str] = None
    output_size_mb: float = 0.0
    file_types: Dict[str, int] = field(default_factory=dict)

    # Performance metrics
    avg_download_speed_mbps: float = 0.0
    resources_per_second: float = 0.0

    # Quality metrics (to be extended)
    html_parsed: bool = False
    css_count: int = 0
    js_count: int = 0
    image_count: int = 0
    font_count: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class ExperimentRunner:
    """
    Core engine for running systematic experiments on website cloning.

    Features:
    - Single site testing
    - Batch experiment execution
    - Progress callbacks
    - Detailed metrics collection
    - Error handling and recovery
    """

    def __init__(
        self,
        headless: bool = True,
        output_dir: Path = None,
        cooldown_seconds: int = 3,
        verbose: bool = True
    ):
        """
        Initialize experiment runner.

        Args:
            headless: Run browser in headless mode
            output_dir: Directory for experiment results (auto-created)
            cooldown_seconds: Wait time between experiments
            verbose: Print progress messages
        """
        self.headless = headless
        self.output_dir = output_dir or Path("experiments/results")
        self.cooldown_seconds = cooldown_seconds
        self.verbose = verbose

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Callbacks
        self.on_experiment_start: Optional[Callable] = None
        self.on_experiment_complete: Optional[Callable] = None
        self.on_experiment_error: Optional[Callable] = None

    def run_single_experiment(self, site: TestSite) -> ExperimentResult:
        """
        Run experiment on a single test site.

        Args:
            site: TestSite object to clone

        Returns:
            ExperimentResult with complete metrics
        """
        if self.verbose:
            print(f"\n{'='*70}")
            print(f" Testing: {site.name}")
            print(f" URL: {site.url}")
            print(f" Category: {site.category} | Difficulty: {site.difficulty}")
            print(f"{'='*70}\n")

        # Notify start
        if self.on_experiment_start:
            self.on_experiment_start(site)

        # Initialize result
        result = ExperimentResult(
            site_name=site.name,
            site_url=site.url,
            site_category=site.category.value,
            site_difficulty=site.difficulty,
            timestamp=datetime.now().isoformat(),
            duration_seconds=0.0,
            success=False
        )

        start_time = time.time()

        try:
            # Create cloner instance
            cloner = ClonerSDK(headless=self.headless)

            # Collect metrics via events
            metrics = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'file_types': {},
                'total_bytes': 0
            }

            @cloner.on_complete
            def on_complete(data):
                metrics['total'] = data.total_resources
                metrics['success'] = data.successful_downloads
                metrics['failed'] = data.failed_downloads

            @cloner.on_resource_downloaded
            def on_resource_downloaded(data):
                # Track file types
                ext = data.resource_type or 'unknown'
                metrics['file_types'][ext] = metrics['file_types'].get(ext, 0) + 1

            @cloner.on_stats_update
            def on_stats(data):
                if hasattr(data, 'file_type_stats'):
                    for ext, count in data.file_type_stats.items():
                        metrics['file_types'][ext] = count

            # Run the clone
            output_path = cloner.clone(site.url)

            # Calculate duration
            duration = time.time() - start_time

            # Calculate output size
            output_size_mb = 0.0
            if output_path and Path(output_path).exists():
                output_size_mb = sum(
                    f.stat().st_size for f in Path(output_path).rglob('*') if f.is_file()
                ) / (1024 * 1024)

            # Populate result
            result.success = True
            result.duration_seconds = duration
            result.total_resources = metrics['total']
            result.successful_downloads = metrics['success']
            result.failed_downloads = metrics['failed']
            result.success_rate = (metrics['success'] / metrics['total'] * 100) if metrics['total'] > 0 else 0.0
            result.output_path = str(output_path) if output_path else None
            result.output_size_mb = output_size_mb
            result.file_types = metrics['file_types']
            result.resources_per_second = metrics['total'] / duration if duration > 0 else 0.0

            # File type counts
            result.css_count = metrics['file_types'].get('css', 0)
            result.js_count = metrics['file_types'].get('js', 0)
            result.image_count = sum(
                metrics['file_types'].get(ext, 0)
                for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'ico']
            )
            result.font_count = sum(
                metrics['file_types'].get(ext, 0)
                for ext in ['woff', 'woff2', 'ttf', 'eot', 'otf']
            )

            if self.verbose:
                print(f"\n Results:")
                print(f"   Duration:     {result.duration_seconds:.1f}s")
                print(f"   Success Rate: {result.success_rate:.1f}%")
                print(f"   Assets:       {result.successful_downloads}/{result.total_resources}")
                print(f"   Failed:       {result.failed_downloads}")
                print(f"   Output Size:  {result.output_size_mb:.2f} MB")
                print(f"   Output Path:  {result.output_path}")

            # Notify completion
            if self.on_experiment_complete:
                self.on_experiment_complete(result)

        except Exception as e:
            # Handle errors
            duration = time.time() - start_time
            result.success = False
            result.duration_seconds = duration
            result.error_message = str(e)

            if self.verbose:
                print(f"\n ERROR: {e}")

            # Notify error
            if self.on_experiment_error:
                self.on_experiment_error(result)

        return result

    def run_experiment_set(
        self,
        sites: List[TestSite],
        save_results: bool = True
    ) -> List[ExperimentResult]:
        """
        Run experiments on multiple sites sequentially.

        Args:
            sites: List of TestSite objects to test
            save_results: Auto-save results to JSON file

        Returns:
            List of ExperimentResult objects
        """
        results = []

        if self.verbose:
            print(f"\n{'='*70}")
            print(f" BATCH EXPERIMENT")
            print(f" Total Sites: {len(sites)}")
            print(f"{'='*70}\n")

        for i, site in enumerate(sites, 1):
            if self.verbose:
                print(f"\n[{i}/{len(sites)}] Starting experiment...")

            result = self.run_single_experiment(site)
            results.append(result)

            # Cooldown between experiments (except after last one)
            if i < len(sites) and self.cooldown_seconds > 0:
                if self.verbose:
                    print(f"\n Cooling down for {self.cooldown_seconds}s...")
                time.sleep(self.cooldown_seconds)

        # Auto-save results
        if save_results:
            self._save_results(results)

        # Print summary
        if self.verbose:
            self._print_summary(results)

        return results

    def _save_results(self, results: List[ExperimentResult]) -> Path:
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"experiment_{timestamp}.json"
        filepath = self.output_dir / filename

        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_experiments": len(results),
                "successful": sum(1 for r in results if r.success),
                "failed": sum(1 for r in results if not r.success),
            },
            "results": [r.to_dict() for r in results]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        if self.verbose:
            print(f"\n Results saved to: {filepath}")

        return filepath

    def _print_summary(self, results: List[ExperimentResult]):
        """Print summary table of results"""
        print(f"\n\n{'='*70}")
        print(" SUMMARY")
        print(f"{'='*70}\n")

        print(f"{'Site Name':<25} {'Success':<10} {'Duration':<12} {'Assets':<12}")
        print("-"*70)

        for r in results:
            status = "OK" if r.success else "FAILED"
            assets = f"{r.successful_downloads}/{r.total_resources}" if r.success else "N/A"
            print(f"{r.site_name:<25} {status:<10} {r.duration_seconds:>6.1f}s      {assets:<12}")

        print(f"\n{'='*70}")

        # Statistics
        successful = [r for r in results if r.success]
        if successful:
            avg_duration = sum(r.duration_seconds for r in successful) / len(successful)
            avg_success_rate = sum(r.success_rate for r in successful) / len(successful)
            total_size = sum(r.output_size_mb for r in successful)

            print(f"\n Statistics:")
            print(f"   Total Experiments:    {len(results)}")
            print(f"   Successful:           {len(successful)}")
            print(f"   Failed:               {len(results) - len(successful)}")
            print(f"   Avg Duration:         {avg_duration:.1f}s")
            print(f"   Avg Success Rate:     {avg_success_rate:.1f}%")
            print(f"   Total Output Size:    {total_size:.2f} MB")

        print(f"\n{'='*70}\n")


def quick_test(url: str, headless: bool = True) -> ExperimentResult:
    """
    Quick convenience function to test a single URL.

    Args:
        url: Website URL to test
        headless: Run in headless mode

    Returns:
        ExperimentResult
    """
    from experiments.test_sites import TestSite, SiteCategory

    site = TestSite(
        name=url,
        url=url,
        category=SiteCategory.SPECIAL,
        description="Quick test",
        difficulty="unknown"
    )

    runner = ExperimentRunner(headless=headless, verbose=True)
    return runner.run_single_experiment(site)


if __name__ == "__main__":
    # Demo usage
    from experiments.test_sites import QUICK_DEMO_SET

    print("Running quick demo experiment set...")
    runner = ExperimentRunner(headless=True, verbose=True)
    results = runner.run_experiment_set(QUICK_DEMO_SET)

    print(f"\nCompleted {len(results)} experiments.")
