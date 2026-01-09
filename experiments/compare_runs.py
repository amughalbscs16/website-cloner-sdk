"""
CLI Tool for Comparing Experiment Runs

Usage:
    python experiments/compare_runs.py                           # Compare last 2 runs
    python experiments/compare_runs.py run1.json run2.json       # Compare specific runs
    python experiments/compare_runs.py --list                    # List all runs
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from experiments.results_storage import ResultsStorage


def list_runs(storage: ResultsStorage):
    """List all available experiment runs"""
    runs = storage.list_all_runs()

    if not runs:
        print("No experiment runs found.")
        return

    print("="*70)
    print(" AVAILABLE EXPERIMENT RUNS")
    print("="*70)
    print()

    print(f"{'Filename':<35} {'Date':<20} {'Total':<8} {'Success':<8}")
    print("-"*70)

    for run in runs:
        print(f"{run['filename']:<35} {run['timestamp'][:19]:<20} {run['total_experiments']:<8} {run['successful']:<8}")

    print()
    print(f"Total runs: {len(runs)}")
    print(f"Results directory: {storage.results_dir}")
    print()


def compare_runs(storage: ResultsStorage, file1: str, file2: str):
    """Compare two experiment runs"""
    try:
        comparison = storage.compare_runs(file1, file2)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    except Exception as e:
        print(f"Error comparing runs: {e}")
        return

    # Print comparison
    print("="*70)
    print(" EXPERIMENT COMPARISON")
    print("="*70)
    print()

    run1 = comparison['run1']
    run2 = comparison['run2']
    comp = comparison['comparison']

    print(f" Run 1: {run1['filename']}")
    print(f"   Timestamp: {run1['timestamp']}")
    print(f"   Experiments: {run1['stats']['count']}")
    print(f"   Successful: {run1['stats']['successful']}")
    print(f"   Avg Duration: {run1['stats']['avg_duration']:.1f}s")
    print(f"   Avg Success Rate: {run1['stats']['avg_success_rate']:.1f}%")
    print(f"   Total Size: {run1['stats']['total_size_mb']:.2f} MB")

    print()

    print(f" Run 2: {run2['filename']}")
    print(f"   Timestamp: {run2['timestamp']}")
    print(f"   Experiments: {run2['stats']['count']}")
    print(f"   Successful: {run2['stats']['successful']}")
    print(f"   Avg Duration: {run2['stats']['avg_duration']:.1f}s")
    print(f"   Avg Success Rate: {run2['stats']['avg_success_rate']:.1f}%")
    print(f"   Total Size: {run2['stats']['total_size_mb']:.2f} MB")

    print()
    print(" Changes (Run 2 vs Run 1):")
    print("-"*70)

    # Duration change
    duration_change = comp['duration_change']
    duration_pct = (duration_change / run1['stats']['avg_duration'] * 100) if run1['stats']['avg_duration'] > 0 else 0
    duration_indicator = "FASTER" if duration_change < 0 else "SLOWER" if duration_change > 0 else "SAME"
    print(f"   Duration: {duration_change:+.1f}s ({duration_pct:+.1f}%) - {duration_indicator}")

    # Success rate change
    success_change = comp['success_rate_change']
    success_indicator = "BETTER" if success_change > 0 else "WORSE" if success_change < 0 else "SAME"
    print(f"   Success Rate: {success_change:+.1f}% - {success_indicator}")

    # Size change
    size_change = comp['size_change_mb']
    size_pct = (size_change / run1['stats']['total_size_mb'] * 100) if run1['stats']['total_size_mb'] > 0 else 0
    print(f"   Output Size: {size_change:+.2f} MB ({size_pct:+.1f}%)")

    print()
    print("="*70)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Compare website cloner experiment runs",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'files',
        nargs='*',
        help='Two result files to compare (e.g., experiment_20250101_120000.json)'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available experiment runs'
    )

    parser.add_argument(
        '--results-dir',
        type=str,
        default=None,
        help='Custom results directory'
    )

    args = parser.parse_args()

    # Create storage
    results_dir = Path(args.results_dir) if args.results_dir else None
    storage = ResultsStorage(results_dir)

    # List mode
    if args.list:
        list_runs(storage)
        return

    # Compare mode
    if len(args.files) == 0:
        # Auto-compare last 2 runs
        runs = storage.list_all_runs()
        if len(runs) < 2:
            print("Error: Need at least 2 experiment runs to compare.")
            print("Run 'python experiments/compare_runs.py --list' to see available runs.")
            return

        file1 = runs[-2]['filename']
        file2 = runs[-1]['filename']
        print(f"Auto-comparing last 2 runs:\n  {file1}\n  {file2}\n")
        compare_runs(storage, file1, file2)

    elif len(args.files) == 2:
        # Compare specified files
        compare_runs(storage, args.files[0], args.files[1])

    else:
        print("Error: Please provide exactly 2 files to compare, or none to auto-compare last 2 runs.")
        print()
        print("Examples:")
        print("  python experiments/compare_runs.py")
        print("  python experiments/compare_runs.py run1.json run2.json")
        print("  python experiments/compare_runs.py --list")


if __name__ == "__main__":
    main()
