"""
Results Storage and Management System

Handles storage, retrieval, and analysis of experiment results.
Supports JSON, CSV export, and results comparison.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import csv


class ResultsStorage:
    """
    Centralized storage system for experiment results.

    Features:
    - Load/save results in JSON format
    - Export to CSV for spreadsheet analysis
    - List all previous runs
    - Compare multiple runs
    - Summary statistics
    """

    def __init__(self, results_dir: Path = None):
        """
        Initialize results storage.

        Args:
            results_dir: Directory for storing results
        """
        self.results_dir = results_dir or Path("experiments/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def save_results(
        self,
        results: List[Dict],
        metadata: Dict = None,
        filename: str = None
    ) -> Path:
        """
        Save experiment results to JSON file.

        Args:
            results: List of result dictionaries
            metadata: Optional metadata about the run
            filename: Custom filename (auto-generated if None)

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_{timestamp}.json"

        filepath = self.results_dir / filename

        # Build metadata
        if metadata is None:
            metadata = {}

        metadata.update({
            "timestamp": datetime.now().isoformat(),
            "total_experiments": len(results),
            "successful": sum(1 for r in results if r.get('success', False)),
            "failed": sum(1 for r in results if not r.get('success', False)),
        })

        # Save to JSON
        data = {
            "metadata": metadata,
            "results": results
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath

    def load_results(self, filename: str) -> Dict:
        """
        Load results from JSON file.

        Args:
            filename: Name of results file

        Returns:
            Dictionary with metadata and results
        """
        filepath = self.results_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Results file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_all_runs(self) -> List[Dict]:
        """
        List all experiment runs with basic info.

        Returns:
            List of dictionaries with run information
        """
        runs = []

        for filepath in sorted(self.results_dir.glob("experiment_*.json")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                metadata = data.get('metadata', {})
                runs.append({
                    'filename': filepath.name,
                    'timestamp': metadata.get('timestamp', 'unknown'),
                    'total_experiments': metadata.get('total_experiments', 0),
                    'successful': metadata.get('successful', 0),
                    'failed': metadata.get('failed', 0),
                    'filepath': str(filepath)
                })
            except Exception as e:
                # Skip invalid files
                continue

        return runs

    def get_latest_run(self) -> Optional[Dict]:
        """
        Get the most recent experiment run.

        Returns:
            Dictionary with metadata and results, or None if no runs exist
        """
        runs = self.list_all_runs()
        if not runs:
            return None

        latest = runs[-1]
        return self.load_results(latest['filename'])

    def export_to_csv(
        self,
        results_data: Dict,
        output_filename: str = None
    ) -> Path:
        """
        Export results to CSV format.

        Args:
            results_data: Results dictionary (from load_results)
            output_filename: Custom CSV filename

        Returns:
            Path to CSV file
        """
        results = results_data.get('results', [])

        if not results:
            raise ValueError("No results to export")

        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"experiment_{timestamp}.csv"

        filepath = self.results_dir / output_filename

        # Extract all possible fields
        fieldnames = set()
        for result in results:
            fieldnames.update(result.keys())

        fieldnames = sorted(fieldnames)

        # Write CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        return filepath

    def compare_runs(self, filename1: str, filename2: str) -> Dict:
        """
        Compare two experiment runs.

        Args:
            filename1: First results file
            filename2: Second results file

        Returns:
            Dictionary with comparison statistics
        """
        run1 = self.load_results(filename1)
        run2 = self.load_results(filename2)

        results1 = run1.get('results', [])
        results2 = run2.get('results', [])

        # Calculate statistics
        def calc_stats(results):
            successful = [r for r in results if r.get('success', False)]
            if not successful:
                return {
                    'count': len(results),
                    'successful': 0,
                    'avg_duration': 0,
                    'avg_success_rate': 0,
                    'total_size_mb': 0
                }

            return {
                'count': len(results),
                'successful': len(successful),
                'avg_duration': sum(r.get('duration_seconds', 0) for r in successful) / len(successful),
                'avg_success_rate': sum(r.get('success_rate', 0) for r in successful) / len(successful),
                'total_size_mb': sum(r.get('output_size_mb', 0) for r in successful)
            }

        stats1 = calc_stats(results1)
        stats2 = calc_stats(results2)

        return {
            'run1': {
                'filename': filename1,
                'timestamp': run1.get('metadata', {}).get('timestamp', 'unknown'),
                'stats': stats1
            },
            'run2': {
                'filename': filename2,
                'timestamp': run2.get('metadata', {}).get('timestamp', 'unknown'),
                'stats': stats2
            },
            'comparison': {
                'duration_change': stats2['avg_duration'] - stats1['avg_duration'],
                'success_rate_change': stats2['avg_success_rate'] - stats1['avg_success_rate'],
                'size_change_mb': stats2['total_size_mb'] - stats1['total_size_mb']
            }
        }

    def get_summary_stats(self, results_data: Dict) -> Dict:
        """
        Calculate summary statistics for a results set.

        Args:
            results_data: Results dictionary

        Returns:
            Dictionary with summary statistics
        """
        results = results_data.get('results', [])
        successful = [r for r in results if r.get('success', False)]

        if not successful:
            return {
                'total_experiments': len(results),
                'successful': 0,
                'failed': len(results),
                'success_percentage': 0
            }

        # Overall stats
        stats = {
            'total_experiments': len(results),
            'successful': len(successful),
            'failed': len(results) - len(successful),
            'success_percentage': len(successful) / len(results) * 100,

            # Timing
            'total_duration': sum(r.get('duration_seconds', 0) for r in successful),
            'avg_duration': sum(r.get('duration_seconds', 0) for r in successful) / len(successful),
            'min_duration': min(r.get('duration_seconds', 0) for r in successful),
            'max_duration': max(r.get('duration_seconds', 0) for r in successful),

            # Resources
            'total_resources': sum(r.get('total_resources', 0) for r in successful),
            'avg_resources_per_site': sum(r.get('total_resources', 0) for r in successful) / len(successful),
            'total_successful_downloads': sum(r.get('successful_downloads', 0) for r in successful),
            'total_failed_downloads': sum(r.get('failed_downloads', 0) for r in successful),
            'avg_success_rate': sum(r.get('success_rate', 0) for r in successful) / len(successful),

            # Size
            'total_size_mb': sum(r.get('output_size_mb', 0) for r in successful),
            'avg_size_mb': sum(r.get('output_size_mb', 0) for r in successful) / len(successful),
        }

        # By category
        categories = {}
        for r in successful:
            cat = r.get('site_category', 'unknown')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)

        stats['by_category'] = {}
        for cat, cat_results in categories.items():
            stats['by_category'][cat] = {
                'count': len(cat_results),
                'avg_duration': sum(r.get('duration_seconds', 0) for r in cat_results) / len(cat_results),
                'avg_success_rate': sum(r.get('success_rate', 0) for r in cat_results) / len(cat_results),
            }

        return stats

    def print_summary(self, results_data: Dict):
        """
        Print formatted summary of results.

        Args:
            results_data: Results dictionary
        """
        metadata = results_data.get('metadata', {})
        stats = self.get_summary_stats(results_data)

        print(f"\n{'='*70}")
        print(" EXPERIMENT SUMMARY")
        print(f"{'='*70}\n")

        print(f" Timestamp: {metadata.get('timestamp', 'unknown')}")
        print(f" Total Experiments: {stats['total_experiments']}")
        print(f" Successful: {stats['successful']} ({stats['success_percentage']:.1f}%)")
        print(f" Failed: {stats['failed']}")

        print(f"\n Duration:")
        print(f"   Total: {stats['total_duration']:.1f}s")
        print(f"   Average: {stats['avg_duration']:.1f}s")
        print(f"   Min/Max: {stats['min_duration']:.1f}s / {stats['max_duration']:.1f}s")

        print(f"\n Resources:")
        print(f"   Total Downloads: {stats['total_successful_downloads']}")
        print(f"   Total Failed: {stats['total_failed_downloads']}")
        print(f"   Average Success Rate: {stats['avg_success_rate']:.1f}%")

        print(f"\n Output Size:")
        print(f"   Total: {stats['total_size_mb']:.2f} MB")
        print(f"   Average per Site: {stats['avg_size_mb']:.2f} MB")

        if stats.get('by_category'):
            print(f"\n By Category:")
            for cat, cat_stats in stats['by_category'].items():
                print(f"   {cat}:")
                print(f"     Count: {cat_stats['count']}")
                print(f"     Avg Duration: {cat_stats['avg_duration']:.1f}s")
                print(f"     Avg Success: {cat_stats['avg_success_rate']:.1f}%")

        print(f"\n{'='*70}\n")


def demo_usage():
    """Demonstrate usage of ResultsStorage"""
    storage = ResultsStorage()

    # List all runs
    print("All experiment runs:")
    runs = storage.list_all_runs()
    for run in runs:
        print(f"  {run['filename']}: {run['total_experiments']} experiments, {run['successful']} successful")

    # Get latest
    if runs:
        latest = storage.get_latest_run()
        print("\nLatest run summary:")
        storage.print_summary(latest)


if __name__ == "__main__":
    demo_usage()
