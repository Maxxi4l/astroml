# AstroML

## Dynamic Graph Machine Learning Framework for the Stellar Network

**AstroML** is a research-driven Python framework for building **dynamic graph machine learning models** on the Stellar Development Foundation Stellar blockchain.

It treats blockchain data as a **multi-asset, time-evolving graph**, enabling advanced ML research on transaction networks such as fraud detection, anomaly detection, and behavioral modeling.

---

## ✨ Features

AstroML provides end-to-end tooling for:

- Ledger ingestion and normalization
- Dynamic transaction graph construction
- Feature engineering for blockchain accounts
- Graph Neural Networks (GNNs)
- Self-supervised node embeddings
- Anomaly detection
- Temporal modeling
- Reproducible ML experimentation
- Model registry with versioning and metrics tracking

---

## 📦 Model Registry

The Model Registry provides version control for your trained models, enabling you to track model versions, performance metrics, and activate specific versions for production use.

**Key Features:**
- Register new model versions with auto‑generated or custom version tags
- Track performance metrics alongside model artifacts
- Activate specific model versions for inference
- Configurable model storage location

For full documentation, see [docs/model-registry.md](./docs/model-registry.md)

---

## 🧠 Core Idea

Blockchain networks are naturally **graph-structured systems**:

| Blockchain Concept | Graph Representation |
| ------------------ | -------------------- |
| Accounts           | Nodes                |
| Transactions       | Directed edges       |
| Assets             | Edge types           |
| Time               | Dynamic dimension    |

Most analytics tools rely on static heuristics or SQL queries.

**AstroML instead enables:**

- Dynamic graph learning
- Temporal GNNs
- Representation learning
- Research-grade experimentation

---

## 🎯 Target Users

AstroML is designed for:

- ML researchers
- Graph ML engineers
- Fraud detection teams
- Blockchain data scientists

---

## 🏗 Architecture Overview

### High-Level Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AstroML: Ingestion → Graph → Train                   │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │ Stellar      │
                              │ Ledgers      │
                              └──────┬───────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │  1. INGESTION LAYER             │
                    │  ├─ Ledger backfill (Polars)   │
                    │  ├─ Incremental ingestion      │
                    │  ├─ State tracking (idempotent)│
                    │  └─ PostgreSQL storage         │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │  2. NORMALIZATION LAYER         │
                    │  ├─ Raw Stellar schema          │
                    │  │  (Ledger, Transaction, Op)   │
                    │  ├─ Graph mirror layer          │
                    │  │  (GraphAccount, GraphEdge)   │
                    │  └─ Composite indexes           │
                    │     (account_id, timestamp)     │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │  3. GRAPH BUILDING LAYER        │
                    │  ├─ Time-windowed snapshots     │
                    │  ├─ Edge construction           │
                    │  ├─ Node indexing               │
                    │  └─ Graph validation            │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │  4. FEATURE ENGINEERING         │
                    │  ├─ Transaction frequency       │
                    │  ├─ Asset diversity             │
                    │  ├─ Structural importance       │
                    │  │  (degree, betweenness, PR)   │
                    │  ├─ Feature store & versioning  │
                    │  └─ Point-in-time queries       │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │  5. TRAINING LAYER              │
                    │  ├─ Temporal train/test split   │
                    │  ├─ Link prediction task        │
                    │  ├─ Negative sampling           │
                    │  ├─ PyTorch Geometric models    │
                    │  │  (GCN, GraphSAGE, GAT)       │
                    │  └─ Early stopping              │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │  6. BENCHMARKING & EVALUATION   │
                    │  ├─ Reproducible configs        │
                    │  ├─ Random seed tracking        │
                    │  ├─ Metric computation          │
                    │  │  (AUC, Precision, Recall)    │
                    │  ├─ Memory profiling            │
                    │  └─ Result persistence          │
                    └────────────────┬────────────────┘
                                     │
                              ┌──────▼──────┐
                              │ Baseline    │
                              │ Results     │
                              └─────────────┘
```

### Data Flow Details

```
Stellar Ledger Data
    ↓
[Ingestion Service]
    ├─ Fetch ledgers (1000000-1100000)
    ├─ Track state (.astroml_state/ingestion_state.json)
    └─ Store in PostgreSQL
    ↓
[Database Schema]
    ├─ Raw Layer: Ledger, Transaction, Operation, Account, Asset
    ├─ Graph Layer: GraphAccount, GraphEdge, GraphTransactionDetail
    └─ Indexes: (account_id, timestamp) composite
    ↓
[Graph Snapshot]
    ├─ Query operations by time window
    ├─ Create Edge objects (src, dst, timestamp, asset, amount)
    ├─ Build node_index mapping
    └─ Validate graph (isolated nodes, self-loops, density)
    ↓
[Feature Store]
    ├─ Compute node features (frequency, diversity, centrality)
    ├─ Compute edge features (asset type, amount, direction)
    ├─ Version features with metadata
    └─ Store in SQLite + Parquet
    ↓
[Temporal Split]
    ├─ Sort edges by timestamp
    ├─ Split at cutoff (80% train, 20% test)
    └─ Ensure no future data leaks into training
    ↓
[Link Prediction Task]
    ├─ Context window: edges before cutoff
    ├─ Future window: edges after cutoff
    ├─ Positive labels: future edges
    ├─ Negative sampling: random non-edges
    └─ Binary classification objective
    ↓
[Model Training]
    ├─ LinkPredictor(encoder + decoder)
    ├─ Adam optimizer with early stopping
    ├─ Compute AUC, Precision, Recall, F1
    └─ Track training/validation losses
    ↓
[Benchmark Results]
    ├─ config.json (full configuration + seed)
    ├─ result.json (metrics + performance)
    └─ metadata.json (run_id, timestamp, linking files)
```

### Module Organization

```
astroml/
├── ingestion/           # Ledger ingestion & state tracking
│   ├── service.py       # IngestionService (incremental, idempotent)
│   ├── state.py         # StateStore (tracks processed ledgers)
│   └── backfill.py      # Bulk ledger loading
├── db/                  # Database layer
│   ├── schema.py        # SQLAlchemy ORM models
│   └── session.py       # Database connection management
├── features/            # Feature engineering
│   ├── feature_store.py # Enterprise feature management
│   ├── graph/
│   │   └── snapshot.py  # Time-windowed graph construction
│   ├── frequency.py     # Transaction frequency features
│   ├── asset_diversity.py
│   └── gnn/             # Graph neural network layers
├── models/              # ML models
│   ├── link_predictor.py
│   ├── gcn.py
│   ├── sage.py
│   └── deep_svdd.py
├── tasks/               # Training tasks
│   └── link_prediction_task.py
├── training/            # Training utilities
│   ├── temporal_split.py # Prevent data leakage
│   └── train_link_prediction.py
├── benchmarking/        # Benchmarking framework
│   ├── core.py          # ModelBenchmark orchestrator
│   ├── config.py        # Configuration management
│   └── metrics.py       # Metric computation
├── quick_start.py       # Quick start pipeline
└── cli.py               # Command-line interface
```

---

## 🚀 Quick Start

### Option 1: Using Make (Recommended)

```bash
# Run quick start with default settings (100 ledgers, 50 accounts, 10 epochs)
make quickstart

# Run with more data for thorough testing
make quickstart-verbose
```

### Option 2: Using Python Module

```bash
# Run quick start with default settings
python -m astroml.quick_start

# Run with custom parameters
python -m astroml.quick_start --num-ledgers 200 --num-accounts 100 --epochs 20 --seed 42
```

### Option 3: Using CLI

```bash
# Run quick start command
python -m astroml quickstart --num-ledgers 100 --num-accounts 50 --epochs 10 --seed 42
```

### What Quick Start Does

The quick start pipeline:

1. **Generates sample data**: Creates 100 synthetic ledgers with 50 accounts and realistic transactions
2. **Builds transaction graph**: Constructs a time-windowed graph with ~2000 edges
3. **Validates graph**: Checks for isolated nodes, self-loops, and computes statistics
4. **Trains baseline model**: Trains a LinkPredictor model for 10 epochs
5. **Saves reproducible results**: Stores config, results, and metadata for reproducibility

**Output**:

```
benchmark_results/quickstart/
├── config.json          # Full configuration with random seed
├── result.json          # Training metrics and performance
└── metadata.json        # Run metadata linking config and result
```

**Example output**:

```
================================================================================
AstroML Quick Start: Ingestion → Graph → Train Pipeline
================================================================================

[Step 1/5] Generating sample ledger data...
Generated 100 ledgers with 50 accounts

[Step 2/5] Building transaction graph...
Built graph with 2000 edges and 50 nodes

[Step 3/5] Creating benchmark configuration...

[Step 4/5] Training baseline model...
Epoch 0: Train Loss = 0.6931, Val Loss = 0.6892
Epoch 5: Train Loss = 0.4521, Val Loss = 0.4612
Training complete. Best metrics: {'auc': 0.92, 'precision': 0.88, 'recall': 0.85}

[Step 5/5] Saving benchmark results...
Saved config to benchmark_results/quickstart/config.json
Saved result to benchmark_results/quickstart/result.json
Saved metadata to benchmark_results/quickstart/metadata.json

✓ Quick start completed successfully!
Results saved to: benchmark_results/quickstart
================================================================================
```

---

## 🔄 Full Setup

### Using Docker (Recommended)

For the quickest setup with all dependencies, use Docker:

```bash
# Clone and navigate to repository
git clone https://github.com/Traqora/astroml.git
cd astroml

# Start with Docker
cp .env.example .env
./scripts/docker-start.sh core

# Access services
curl http://localhost:8000            # API
open http://localhost:3000            # Grafana
```

📚 **Full Docker Setup**: See [DOCKER.md](./DOCKER.md) for comprehensive documentation including:
- [Docker Quick Reference](./DOCKER_QUICK_REFERENCE.md) - Quick commands and common tasks
- [Environment Configuration](./docker-env-guide.md) - Configuration guide
- [Production Deployment](./DOCKER_PRODUCTION_DEPLOYMENT.md) - Production setup
- [Troubleshooting](./DOCKER_TROUBLESHOOTING.md) - Common issues and solutions

### Local Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/Traqora/astroml.git
cd astroml
```

### 2. Create environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Note:** Three requirements files are available. See [REQUIREMENTS.md](REQUIREMENTS.md) for guidance on which to use based on your environment (GPU training, CPU-only, or minimal config-only).

### 3. Configure database

A lightweight Docker Compose setup is provided to spin up PostgreSQL and Redis with persistent volumes. Simply run:

```bash
docker compose up -d
```

This starts only the database and cache, letting you run Python scripts and training natively on your machine. Alternatively, you can configure your own database and update `config/database.yaml`.

---

## 📥 Data Ingestion

Backfill ledgers:

```bash
python -m astroml.ingestion.backfill \
  --start-ledger 1000000 \
  --end-ledger 1100000
```

---

## 🕸 Build Graph Snapshot

Create a rolling time window graph:

```bash
python -m astroml.graph.build_snapshot --window 30d
```

---

## 🧪 Synthetic Fraud Pattern Injection

Create benchmark datasets by injecting controlled fraud structures into a clean ledger copy:

```bash
python -m astroml.ingestion.synthetic_fraud_injector \
  --input data/clean_ledger.jsonl \
  --output data/ledger_with_fraud.jsonl \
  --summary outputs/fraud_injection_summary.json \
  --sybil-clusters 3 \
  --sybil-cluster-size 8 \
  --wash-loops 2 \
  --wash-loop-size 5
```

The injector appends transactions tagged with `synthetic_fraud=true` and `fraud_pattern` (`sybil_cluster` or `wash_trading_loop`) for downstream benchmarking.

---

## 🤖 Train Baseline GCN

```bash
python -m astroml.training.train_gcn
```

---

## 📊 Example Use Cases

- [Liquidity Monitoring for the Stellar Community Fund](docs/scf-liquidity-monitoring.md)
- Fraud / scam detection
- Account clustering
- Transaction risk scoring
- Temporal behavior modeling
- Self-supervised embeddings
- Network anomaly detection

---

## 🔬 Research Goals

AstroML emphasizes:

- Reproducibility
- Modular experimentation
- Scalable ingestion
- Temporal graph learning
- Production-ready ML pipelines

---

## 🛠 Tech Stack

- Python
- PyTorch / PyTorch Geometric
- PostgreSQL
- NetworkX / graph tooling

---

## 📌 Roadmap

- [ ] Real-time streaming ingestion
- [ ] Temporal GNN models
- [ ] Contrastive learning pipelines
- [ ] Feature store
- [ ] Model benchmarking suite
- [ ] Docker deployment

---

## 🤝 Contributing

Contributions are welcome!

```bash
fork → branch → commit → PR
```

Please open issues for bugs or feature requests.

---

## 📜 License

MIT License
