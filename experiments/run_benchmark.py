"""
CLI Tool for Running Benchmarks

Usage:
    python experiments/run_benchmark.py quick        # 3 sites, ~3 min
    python experiments/run_benchmark.py competitive  # 5 sites, ~8 min
    python experiments/run_benchmark.py tier1        # Static sites only
    python experiments/run_benchmark.py tier2        # SSR sites only
    python experiments/run_benchmark.py tier3        # SPA sites only
    python experiments/run_benchmark.py full         # All 20 sites, ~30 min
    python experiments/run_benchmark.py custom URL1 URL2 URL3  # Custom URLs
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from experiments.experiment_engine import ExperimentRunner
from experiments.test_sites import (
    QUICK_DEMO_SET,
    COMPETITIVE_SET,
    FULL_BENCHMARK_SET,
    TIER_1_STATIC,
    TIER_2_SSR,
    TIER_3_SPA,
    TIER_4_HYBRID,
    TIER_5_HEAVY_JS,
    TIER_6_SPECIAL,
    TestSite,
    SiteCategory
)
from experiments.results_storage import ResultsStorage


def main():
    parser = argparse.ArgumentParser(
        description="Run website cloner benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python experiments/run_benchmark.py quick
  python experiments/run_benchmark.py tier3
  python experiments/run_benchmark.py custom https://example.com https://react.dev
        """
    )

    parser.add_argument(
        'mode',
        choices=['quick', 'competitive', 'tier1', 'tier2', 'tier3', 'tier4', 'tier5', 'tier6', 'full', 'custom'],
        help='Which benchmark set to run'
    )

    parser.add_argument(
        'urls',
        nargs='*',
        help='Custom URLs (only for custom mode)'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser in headless mode (default: True)'
    )

    parser.add_argument(
        '--no-headless',
        action='store_false',
        dest='headless',
        help='Run browser with visible window'
    )

    parser.add_argument(
        '--cooldown',
        type=int,
        default=3,
        help='Cooldown seconds between experiments (default: 3)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Custom output directory for results'
    )

    args = parser.parse_args()

    # Select test set
    test_sites = None
    mode_name = ""

    if args.mode == 'quick':
        test_sites = QUICK_DEMO_SET
        mode_name = "Quick Demo (3 sites)"
    elif args.mode == 'competitive':
        test_sites = COMPETITIVE_SET
        mode_name = "Competitive Comparison (5 sites)"
    elif args.mode == 'tier1':
        test_sites = TIER_1_STATIC
        mode_name = "Tier 1: Static Sites"
    elif args.mode == 'tier2':
        test_sites = TIER_2_SSR
        mode_name = "Tier 2: Server-Rendered Sites"
    elif args.mode == 'tier3':
        test_sites = TIER_3_SPA
        mode_name = "Tier 3: Single-Page Apps"
    elif args.mode == 'tier4':
        test_sites = TIER_4_HYBRID
        mode_name = "Tier 4: Hybrid Frameworks"
    elif args.mode == 'tier5':
        test_sites = TIER_5_HEAVY_JS
        mode_name = "Tier 5: Heavy JavaScript"
    elif args.mode == 'tier6':
        test_sites = TIER_6_SPECIAL
        mode_name = "Tier 6: Special Cases"
    elif args.mode == 'full':
        test_sites = FULL_BENCHMARK_SET
        mode_name = "Full Benchmark (20 sites)"
    elif args.mode == 'custom':
        if not args.urls:
            print("Error: Custom mode requires URLs")
            print("Usage: python experiments/run_benchmark.py custom URL1 URL2 URL3")
            sys.exit(1)

        test_sites = [
            TestSite(
                name=url,
                url=url,
                category=SiteCategory.SPECIAL,
                description="Custom URL",
                difficulty="unknown"
            )
            for url in args.urls
        ]
        mode_name = f"Custom Set ({len(test_sites)} sites)"

    # Print header
    print("="*70)
    print(" WEBSITE CLONER BENCHMARK")
    print("="*70)
    print(f"\n Mode: {mode_name}")
    print(f" Total Sites: {len(test_sites)}")
    print(f" Headless: {args.headless}")
    print(f" Cooldown: {args.cooldown}s")
    print()

    # Confirm for long runs
    if len(test_sites) >= 10:
        estimated_time = len(test_sites) * 90  # Rough estimate: 90s per site
        print(f" Estimated time: ~{estimated_time // 60} minutes")
        response = input("\n Continue? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)

    # Create runner
    output_dir = Path(args.output_dir) if args.output_dir else None
    runner = ExperimentRunner(
        headless=args.headless,
        output_dir=output_dir,
        cooldown_seconds=args.cooldown,
        verbose=True
    )

    # Run experiments
    results = runner.run_experiment_set(test_sites, save_results=True)

    # Load and print detailed summary
    storage = ResultsStorage(runner.output_dir)
    latest = storage.get_latest_run()

    if latest:
        print("\n" + "="*70)
        print(" DETAILED SUMMARY")
        print("="*70)
        storage.print_summary(latest)

        # Offer CSV export
        response = input("\n Export to CSV? (y/n): ")
        if response.lower() == 'y':
            csv_path = storage.export_to_csv(latest)
            print(f" Exported to: {csv_path}")

    print("\n Benchmark complete!")
    print(f" Results saved to: {runner.output_dir}")
    print()


if __name__ == "__main__":
    main()
