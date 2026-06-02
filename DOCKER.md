# AstroML Docker Documentation Index

Welcome to the AstroML Docker documentation. This comprehensive guide covers all aspects of using Docker with AstroML.

## Documentation Structure

### Getting Started
- **[Docker Quick Reference](./DOCKER_QUICK_REFERENCE.md)** - Start here! Quick commands and common tasks
- **[Full Docker Setup Guide](./docs/DOCKER_SETUP.md)** - Complete setup instructions and service descriptions

### Configuration & Environment
- **[Environment Configuration Guide](./docker-env-guide.md)** - Environment variables, templates, and best practices
- **[.env.example](./.env.example)** - Template for environment variables

### Deployment & Operations
- **[Production Deployment Guide](./DOCKER_PRODUCTION_DEPLOYMENT.md)** - Complete production deployment checklist
- **[Production Compose Override](./docker-compose.prod.yml)** - Production-specific configurations

### Running Services
- **[Main docker-compose.yml](./docker-compose.yml)** - Main service definitions
- **[docker-start.sh](./scripts/docker-start.sh)** - Helper script for managing services
- **[docker-health-check.sh](./scripts/docker-health-check.sh)** - Health verification script
- **[docker-backup.sh](./scripts/docker-backup.sh)** - Backup and restore script

### Troubleshooting & Support
- **[Troubleshooting Guide](./DOCKER_TROUBLESHOOTING.md)** - Common issues and solutions
- **[Docker Entrypoint Scripts](./docker-entrypoint-*.sh)** - Container initialization scripts

## Quick Navigation

### I want to...

#### Start Using Docker
1. Install Docker and Docker Compose (see Prerequisites section below)
2. Read [Docker Quick Reference](./DOCKER_QUICK_REFERENCE.md)
3. Run `./scripts/docker-start.sh core` to start core services
4. Visit [http://localhost:8000](http://localhost:8000) for the API

#### Set Up Development Environment
1. Copy `.env.example` to `.env`
2. Run `./scripts/docker-start.sh dev`
3. Access Jupyter Lab at [http://localhost:8888](http://localhost:8888)
4. See [Environment Configuration Guide](./docker-env-guide.md) for options

#### Run ML Training
1. CPU Training: `./scripts/docker-start.sh training-cpu`
2. GPU Training: `./scripts/docker-start.sh training-gpu`
3. Monitor at [http://localhost:6006](http://localhost:6006) (TensorBoard)

#### Set Up Production
1. Review [Production Deployment Guide](./DOCKER_PRODUCTION_DEPLOYMENT.md)
2. Create `.env.prod` from `.env.example`
3. Run `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
4. Execute health checks: `./scripts/docker-health-check.sh`

#### Monitor Services
1. Prometheus: [http://localhost:9090](http://localhost:9090)
2. Grafana: [http://localhost:3000](http://localhost:3000) (admin/admin)
3. Run `docker stats` for real-time resource usage

#### Backup & Restore Data
1. Backup: `./scripts/docker-backup.sh ./backups`
2. Restore: See [Troubleshooting Guide](./DOCKER_TROUBLESHOOTING.md#disaster-recovery)

#### Debug Issues
1. Check [Troubleshooting Guide](./DOCKER_TROUBLESHOOTING.md)
2. Run health checks: `./scripts/docker-health-check.sh`
3. View logs: `docker-compose logs -f <service>`

## Core Concepts

### Docker Architecture

```
┌─────────────────────────────────────────┐
│          AstroML Application            │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │  Ingestion   │  │   Training   │   │
│  │  Container   │  │  Container   │   │
│  └──────────────┘  └──────────────┘   │
│         ↓                ↓              │
│  ┌──────────────┐  ┌──────────────┐   │
│  │  PostgreSQL  │  │    Redis     │   │
│  │  Container   │  │  Container   │   │
│  └──────────────┘  └──────────────┘   │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │ Prometheus   │  │   Grafana    │   │
│  │  Container   │  │  Container   │   │
│  └──────────────┘  └──────────────┘   │
│                                         │
└─────────────────────────────────────────┘
        Docker Network (astroml-network)
```

### Services Overview

| Service | Purpose | Port | Docker Target |
|---------|---------|------|---------------|
| PostgreSQL | Data storage | 5432 | - |
| Redis | Caching & jobs | 6379 | - |
| Ingestion | Data ingestion | 8000 | ingestion |
| Streaming | Real-time streaming | 8001 | ingestion |
| Training (CPU) | ML training | 6007 | training-cpu |
| Training (GPU) | ML training w/ GPU | 6006 | training |
| Development | Dev environment | 8002 | development |
| Production | Production service | 8000 | production |
| Prometheus | Metrics | 9090 | - |
| Grafana | Visualization | 3000 | - |

## Prerequisites

### System Requirements

**Minimum:**
- 4GB RAM
- 2 CPU cores
- 20GB disk space
- Docker 20.10+
- Docker Compose 2.0+

**Recommended:**
- 8GB+ RAM
- 4+ CPU cores
- 50GB+ disk space
- Docker 20.10+
- Docker Compose 2.0+

**For GPU Training:**
- NVIDIA GPU
- NVIDIA Docker runtime
- CUDA 12.1+

### Installation

#### Install Docker

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

**macOS:**
```bash
brew install --cask docker
```

**Windows:**
Download Docker Desktop from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)

#### Install Docker Compose

Usually included with Docker Desktop. For Linux, if needed:
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

Verify installation:
```bash
docker --version
docker-compose --version
```

#### Install NVIDIA Docker (for GPU support)

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

Verify NVIDIA Docker:
```bash
docker run --rm --gpus all nvidia/cuda:12.1-runtime-ubuntu22.04 nvidia-smi
```

## Quick Start (30 seconds)

```bash
# 1. Clone repository
git clone https://github.com/stellar/astroml.git
cd astroml

# 2. Copy environment template
cp .env.example .env

# 3. Start services
docker-compose up -d postgres redis ingestion

# 4. Check status
docker-compose ps

# 5. Test services
curl http://localhost:8000/health
```

## Usage Examples

### Start Specific Service Combinations

```bash
# Core infrastructure only
./scripts/docker-start.sh core

# Development environment
./scripts/docker-start.sh dev

# Data ingestion pipeline
./scripts/docker-start.sh ingestion

# ML training
./scripts/docker-start.sh training-cpu    # CPU only
./scripts/docker-start.sh training-gpu    # GPU support

# Full monitoring stack
./scripts/docker-start.sh monitoring

# Production deployment
./scripts/docker-start.sh production

# Everything
./scripts/docker-start.sh all
```

### Access Services

```bash
# API
curl http://localhost:8000

# Jupyter Lab (dev environment)
open http://localhost:8888

# Prometheus (metrics)
open http://localhost:9090

# Grafana (dashboards)
open http://localhost:3000  # admin / admin

# PostgreSQL
psql -h localhost -U astroml -d astroml

# Redis CLI
redis-cli -h localhost
```

### Manage Services

```bash
# View status
./scripts/docker-start.sh status

# View logs
./scripts/docker-start.sh logs [service]

# Rebuild service
./scripts/docker-start.sh rebuild [service]

# Stop services
./scripts/docker-start.sh stop

# Stop and remove everything
./scripts/docker-start.sh stop-all
```

## Environment Setup

See [Environment Configuration Guide](./docker-env-guide.md) for:
- Complete list of environment variables
- Configuration templates for different scenarios
- Secrets management best practices
- Validation procedures

## Common Issues

See [Troubleshooting Guide](./DOCKER_TROUBLESHOOTING.md) for solutions to:
- Build issues
- Container startup problems
- Networking errors
- Database connection issues
- Performance problems
- Memory and disk issues

## Advanced Topics

### Build Customization

Edit `Dockerfile` to:
- Add additional system dependencies
- Install additional Python packages
- Modify build stages
- Change base images

### Multi-Architecture Builds

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t astroml:latest .
```

### Private Registry

```bash
docker login registry.example.com
docker build -t registry.example.com/astroml:latest .
docker push registry.example.com/astroml:latest
```

### Docker Swarm Deployment

For clustering:
```bash
docker swarm init
docker stack deploy -c docker-compose.prod.yml astroml
```

### Kubernetes Deployment

See [Kubernetes setup](./k8s/) for:
- Deployments
- Services
- StatefulSets
- ConfigMaps
- Secrets

## Related Documentation

- [Production Deployment](./DOCKER_PRODUCTION_DEPLOYMENT.md)
- [Main README](./README.md)
- [Installation Guide](./README.md#installation)
- [API Documentation](./docs/index.md)
- [Contributing Guide](./CONTRIBUTING.md)

## Getting Help

- 📚 [Full Docker Setup Guide](./docs/DOCKER_SETUP.md)
- 🚀 [Quick Reference](./DOCKER_QUICK_REFERENCE.md)
- 🔧 [Troubleshooting](./DOCKER_TROUBLESHOOTING.md)
- ⚙️ [Environment Guide](./docker-env-guide.md)
- 🐛 [GitHub Issues](https://github.com/stellar/astroml/issues)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on:
- Reporting Docker-related issues
- Contributing Docker improvements
- Testing Docker configurations

## License

AstroML is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.
