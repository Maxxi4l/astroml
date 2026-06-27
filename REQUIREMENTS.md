# Python requirements files

Three requirements files live at the repo root. Pick the one that matches
your environment — they are *not* meant to be combined.

## Decision tree

```
Need to train models (GPU/CUDA available)?
└─ yes → pip install -r requirements.txt
└─ no
   └─ Need to run training or feature jobs (CPU only)?
      └─ yes → pip install -r requirements-cpu.txt
      └─ no
         └─ Just want to load Hydra config / parse dataframes /
            run unit tests that don't touch torch?
            └─ yes → pip install -r requirements-minimal.txt
```

## What each file ships

### `requirements.txt` — full GPU training stack
The everything-on-board file. Pulls the full GPU `torch` wheel,
`pytorch-lightning`, `mlflow`, the feature-store stack (redis, pyarrow,
fastparquet, networkx, click, rich), visualization (matplotlib, seaborn),
notebooks, and dev tooling (pytest + black + flake8 + mypy).

Use this on GPU CI runners and developer machines that build dashboards or
notebooks.

### `requirements-cpu.txt` — CPU-only training stack
Same shape as `requirements.txt` but pins the **CPU-only** torch wheels
from the official PyTorch CPU index:

```
torch>=2.0.0+cpu --index-url https://download.pytorch.org/whl/cpu
```

Drops `mlflow`, `scikit-learn` standalone (still pulled transitively via
some libs), the feature-store stack, visualization, dev tooling, and
notebooks — they're not needed for headless CPU jobs. Pick this when:

- You're building the Docker image for production / CI.
- You're running batch ingestion or model serving on a CPU box.
- You want the fastest possible `pip install` for a smoke test.

### `requirements-minimal.txt` — Hydra + dataframes only
The smallest viable set: `numpy`, `pandas`, `polars`, `pyyaml`,
`hydra-core`, `omegaconf`. Nothing else. Use it when:

- You just want to import `astroml.config` and resolve a Hydra schema.
- You're running config-only unit tests in CI.
- You're embedding a small piece of astroml into another service and want
  to keep the install footprint tiny.

## Pin policy

Where a package appears in more than one file, the lower bound is held in
sync across all of them. The actual lower bounds in use:

| package          | pin                | files                                           |
|------------------|--------------------|-------------------------------------------------|
| `numpy`          | `>=1.24`           | requirements.txt, -cpu.txt, -minimal.txt        |
| `pandas`         | `>=2.0`            | requirements.txt, -cpu.txt, -minimal.txt        |
| `polars`         | `>=1.0`            | requirements.txt, -cpu.txt, -minimal.txt        |
| `pyyaml`         | `>=6.0`            | requirements.txt, -cpu.txt, -minimal.txt        |
| `hydra-core`     | `>=1.3.0`          | requirements.txt, -cpu.txt, -minimal.txt        |
| `omegaconf`      | `>=2.3.0`          | requirements.txt, -cpu.txt, -minimal.txt        |
| `torch`          | `>=2.0.0` / `+cpu` | requirements.txt (GPU), -cpu.txt (CPU)          |
| `torch-geometric`| `>=2.3.0`          | requirements.txt, -cpu.txt                      |
| `sqlalchemy`     | `>=2.0`            | requirements.txt, -cpu.txt                      |
| `psycopg2-binary`| `>=2.9`            | requirements.txt, -cpu.txt                      |
| `aiohttp`        | `>=3.9`            | requirements.txt, -cpu.txt                      |
| `stellar-sdk`    | `>=9.0.0`          | requirements.txt, -cpu.txt                      |

If you bump one, run `grep -E "^<package>\b" requirements*.txt` to confirm
you've bumped them in lockstep.
