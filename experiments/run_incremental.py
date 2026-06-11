"""Incremental benchmark runner: saves results after EVERY site.

Robust to interruption — unlike run_benchmark.py, a killed run keeps all
completed results. Re-running skips sites already recorded.

Usage: python experiments/run_incremental.py [results_file.json]
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.experiment_engine import ExperimentRunner
from experiments.test_sites import FULL_BENCHMARK_SET


def main():
    results_path = Path(
        sys.argv[1] if len(sys.argv) > 1
        else "experiments/results/incremental_full.json"
    )
    results_path.parent.mkdir(parents=True, exist_ok=True)

    if results_path.exists():
        data = json.loads(results_path.read_text(encoding="utf-8"))
    else:
        data = {"metadata": {"started": datetime.now().isoformat()}, "results": []}

    done = {r["site_url"] for r in data["results"]}
    pending = [s for s in FULL_BENCHMARK_SET if s.url not in done]
    print(f"{len(done)} sites already done, {len(pending)} pending")

    runner = ExperimentRunner(headless=True, cooldown_seconds=2, verbose=True)

    for site in pending:
        result = runner.run_single_experiment(site)
        data["results"].append(result.to_dict())
        data["metadata"]["updated"] = datetime.now().isoformat()
        results_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"[saved] {len(data['results'])}/{len(FULL_BENCHMARK_SET)} -> {results_path}")

    print("\nAll sites complete.")


if __name__ == "__main__":
    main()
