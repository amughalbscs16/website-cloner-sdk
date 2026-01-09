# Experiments & Benchmarking

This directory contains all experimental infrastructure for validating and improving the Website Cloner.

## 📁 Structure

```
experiments/
├── README.md                    # This file
├── RESEARCH_PLAN.md            # Full research-grade experimental framework
├── IMPLEMENTATION_SPEC.md      # Detailed implementation specifications
├── test_sites.py               # Centralized database of 20 test websites
├── experiment_engine.py        # Core ExperimentRunner class
├── results_storage.py          # Results management and analysis
├── simple_demo.py              # Quick 3-site demonstration (run this first!)
├── run_benchmark.py            # CLI for running different benchmark sets
├── compare_runs.py             # CLI for comparing experiment runs
├── demo_benchmark.py           # Full benchmark with HTML report generation
└── results/                    # Results will be saved here
    ├── experiment_*.json       # Experiment results
    └── experiment_*.csv        # CSV exports
```

## 🚀 Quick Start

### 1. Run Simple Demo (Recommended First)

Tests 3 websites (Static, React SPA, WordPress) in ~2-3 minutes:

```bash
python experiments/simple_demo.py
```

### 2. Run Specific Benchmark Sets

Use the CLI tool to run different benchmark configurations:

```bash
# Quick demo (3 sites)
python experiments/run_benchmark.py quick

# Test only SPAs
python experiments/run_benchmark.py tier3

# Full benchmark (20 sites, ~30 min)
python experiments/run_benchmark.py full

# Custom URLs
python experiments/run_benchmark.py custom https://example.com https://react.dev
```

### 3. Compare Experiment Runs

```bash
# List all previous runs
python experiments/compare_runs.py --list

# Auto-compare last 2 runs
python experiments/compare_runs.py

# Compare specific runs
python experiments/compare_runs.py experiment_20250118_120000.json experiment_20250118_150000.json
```

## 🗄️ Test Sites Database

**20 carefully selected websites** across 6 complexity tiers:

### Tier 1: Static (3 sites)
- ✅ `example.com` - Baseline test
- ✅ `motherfuckingwebsite.com` - Ultra-minimal
- ✅ `docs.python.org` - Static docs

### Tier 2: Server-Rendered (4 sites)
- ✅ `wordpress.org/news` - WordPress blog
- ✅ `djangoproject.com` - Django framework
- ✅ `rubyonrails.org` - Rails framework
- ✅ `wikipedia.org` - MediaWiki

### Tier 3: SPAs (3 sites)
- 🔥 `react.dev` - React SPA (critical test!)
- 🔥 `vuejs.org` - Vue SPA
- 🔥 `angular.io` - Angular SPA

### Tier 4: Hybrid (3 sites)
- ⚡ `nextjs.org` - Next.js (React + SSR)
- ⚡ `nuxt.com` - Nuxt (Vue + SSR)
- ⚡ `remix.run` - Remix (edge-first)

### Tier 5: Heavy JavaScript (3 sites)
- 💪 `figma.com/blog` - Heavy animations
- 💪 `notion.so/product` - Complex interactions
- 💪 `linear.app` - Smooth animations

### Tier 6: Special Cases (4 sites)
- 🎯 `tailwindcss.com` - CDN assets
- 🎯 `fonts.google.com` - Font files
- 🎯 `unsplash.com` - Lazy loading
- 🎯 `developer.mozilla.org` - Large docs

## 🧪 Pre-configured Test Sets

### Quick Demo Set (3 sites, ~3 min)
```python
from experiments.test_sites import QUICK_DEMO_SET

# Static, SPA, SSR
sites = QUICK_DEMO_SET
```

### Competitive Set (5 sites, ~8 min)
```python
from experiments.test_sites import COMPETITIVE_SET

# For comparing vs HTTrack, Wget, etc.
```

### Full Benchmark (20 sites, ~30 min)
```python
from experiments.test_sites import FULL_BENCHMARK_SET

# Complete evaluation
```

## 📊 Usage Examples

### Example 1: Test Specific Tier

```python
from experiments.test_sites import get_sites_by_category, SiteCategory
from src import clone_website

# Test all SPAs
spa_sites = get_sites_by_category(SiteCategory.SPA)
for site in spa_sites:
    print(f"Testing {site.name}...")
    clone_website(site.url)
```

### Example 2: Custom Test Set

```python
from experiments.test_sites import get_custom_set

# Create custom set by names
sites = get_custom_set(["React.dev", "Vue.js", "WordPress.org"])
```

### Example 3: Filter by Difficulty

```python
from experiments.test_sites import get_sites_by_difficulty

# Test only "easy" sites first
easy_sites = get_sites_by_difficulty("easy")
```

## 📈 Research Framework

See `RESEARCH_PLAN.md` for full details on:

- **5 Research Questions** with rigorous experimental design
- **Multi-dimensional quality metrics** (5D assessment framework)
- **Statistical analysis** (t-tests, ANOVA, effect sizes)
- **Competitive benchmarking** (vs HTTrack, Wget, etc.)
- **Ablation studies** (component importance)
- **Scalability analysis** (performance vs complexity)

## 🎯 What to Run Right Now

**For quick validation:**
```bash
python experiments/simple_demo.py
```

**For full benchmarking with visual report:**
```bash
python experiments/demo_benchmark.py
# Opens HTML report in browser
```

**For research-grade experiments:**
See `RESEARCH_PLAN.md` and implement the experiments incrementally.

## 💡 Adding New Test Sites

Edit `test_sites.py`:

```python
TIER_6_SPECIAL.append(
    TestSite(
        name="Your Site",
        url="https://yoursite.com",
        category=SiteCategory.SPECIAL,
        description="What makes it special",
        expected_assets=100,
        difficulty="medium",
        notes="Any important notes"
    )
)
```

## 📝 Results Storage

All experiment results are saved to:
- `experiments/results/*.json` - Raw data
- `experiments/results/*.html` - Visual reports
- `experiments/results/*.csv` - For spreadsheets

## 📊 Implementation Status

### Phase 1: Core Infrastructure ✅ COMPLETE
- ✅ Experiment engine (`experiment_engine.py`)
- ✅ Results storage system (`results_storage.py`)
- ✅ Test sites database (20 sites across 6 tiers)
- ✅ CLI tools (simple demo, benchmark runner, comparison)
- ✅ Documentation and usage examples

See `PHASE1_COMPLETE.md` for full details.

### Phase 2: Advanced Features ⏳ NEXT
- Statistical analysis (t-tests, ANOVA, effect sizes)
- Competitive benchmarking (vs HTTrack, Wget)
- HTML report generation with visualizations
- Automated improvement suggestions

### Phase 3: Web UI Integration ⏳ PLANNED
- API endpoints for experiments
- Web dashboard for running benchmarks
- Real-time progress visualization
- Results comparison interface

## 🔬 Next Steps

1. ✅ ~~Core infrastructure~~ (COMPLETE)
2. ⏳ Run full benchmark to establish baseline
3. ⏳ Identify top 3 failing test cases
4. ⏳ Implement fixes based on findings
5. ⏳ Statistical analysis and reporting
6. ⏳ Competitive comparison vs HTTrack
7. ⏳ Web UI integration

---

**Last Updated:** 2025-10-18
**Phase 1 Status:** ✅ Complete and Tested
**Total Test Sites:** 20
**CLI Tools:** 3 (demo, benchmark, compare)
**Ready to Use:** Yes ✅
