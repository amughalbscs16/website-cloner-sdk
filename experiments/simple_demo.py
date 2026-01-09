"""
Simple 3-Site Demonstration
Uses the ExperimentRunner for consistent testing
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.experiment_engine import ExperimentRunner
from experiments.test_sites import QUICK_DEMO_SET

def main():
    print("="*70)
    print(" WEBSITE CLONER - DEMONSTRATION BENCHMARK")
    print("="*70)
    print()
    print(" Testing 3 sites: Static, React SPA, WordPress")
    print(" Using centralized experiment engine")
    print()

    # Create experiment runner
    runner = ExperimentRunner(
        headless=True,
        cooldown_seconds=3,
        verbose=True
    )

    # Run experiments on the quick demo set
    results = runner.run_experiment_set(QUICK_DEMO_SET, save_results=True)

    print("\n Experiment complete!")
    print(f" Results saved to: {runner.output_dir}")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()
