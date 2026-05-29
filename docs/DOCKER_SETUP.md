# Docker Setup Guide for AstroML

This guide provides comprehensive instructions for setting up and using the Docker environment for AstroML with the Feature Store implementation.

## Overview

The AstroML Docker environment provides:
- **Containerized development** with all dependencies pre-installed
- **Multi-service architecture** with PostgreSQL, Redis, and Feature Store
- **GPU support** for machine learning training
- **Development tools** including Jupyter Lab and testing utilities
- **Production-ready** deployment configurations
- **Monitoring** with Prometheus and Grafana

## Prerequisites

### System Requirements
- **Docker Engine** 20.10+ with Docker Compose v2
- **Docker Compose** v2 (or docker-compose standalone)
- **8GB+ RAM** for development environment
- **16GB+ RAM** for full environment with training
- **NVIDIA GPU** (optional) for GPU-accelerated training
- **20GB+ disk space** for Docker images and volumes

### Installation

#### Docker Desktop (Recommended)
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
# Follow the installation instructions for your OS
```

#### Docker Engine + Docker Compose (Linux)
```bash
# Install Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/Menjay7/astroml.git
cd astroml

# Copy environment configuration
cp .env.example .env

# Make development script executable (Linux/macOS)
chmod +x scripts/docker-dev.sh
```

### 2. Start Development Environment
```bash
# Build Docker images
./scripts/docker-dev.sh build

# Start development environment
./scripts/docker-dev.sh dev
```

### 3. Access Services
- **Jupyter Lab**: http://localhost:8888
- **TensorBoard**: http://localhost:6008
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Docker Services

### Core Services

#### PostgreSQL Database
- **Container**: `astroml-postgres`
- **Port**: 5432
- **Database**: `astroml`
- **User**: `astroml`
- **Password**: `astroml_password`

#### Redis Cache
- **Container**: `astroml-redis`
- **Port**: 6379
- **Purpose**: Caching and job queues

#### Feature Store
- **Container**: `astroml-feature-store`
- **Port**: 8000
- **Purpose**: Centralized feature management
- **Storage**: `/app/feature_store`

### Application Services

#### Ingestion Service
- **Container**: `astroml-ingestion`
- **Port**: 8001
- **Purpose**: Data ingestion and processing

#### Streaming Service
- **Container**: `astroml-streaming`
- **Port**: 8002
- **Purpose**: Real-time data streaming

#### Development Environment
- **Container**: `astroml-dev`
- **Port**: 8003 (API), 8888 (Jupyter), 6008 (TensorBoard)
- **Purpose**: Interactive development

#### Production Service
- **Container**: `astroml-production`
- **Port**: 8004
- **Purpose**: Production deployment

### Training Services

#### GPU Training
- **Container**: `astroml-training-gpu`
- **Port**: 6006 (TensorBoard)
- **GPU**: Required
- **Purpose**: GPU-accelerated ML training

#### CPU Training
- **Container**: `astroml-training-cpu`
- **Port**: 6007 (TensorBoard)
- **GPU**: Not required
- **Purpose**: CPU-based ML training

### Monitoring Services

#### Prometheus
- **Container**: `astroml-prometheus`
- **Port**: 9090
- **Purpose**: Metrics collection

#### Grafana
- **Container**: `astroml-grafana`
- **Port**: 3000
- **Purpose**: Visualization and dashboards

## Usage Guide

### Development Script

The `scripts/docker-dev.sh` script provides convenient commands:

```bash
# Build all Docker images
./scripts/docker-dev.sh build

# Start development environment
./scripts/docker-dev.sh dev

# Start Feature Store only
./scripts/docker-dev.sh feature-store

# Start full environment
./scripts/docker-dev.sh full

# Run tests
./scripts/docker-dev.sh test

# Run Feature Store tests
./scripts/docker-dev.sh test-feature-store

# Stop all services
./scripts/docker-dev.sh stop

# Clean up everything
./scripts/docker-dev.sh cleanup

# Show logs
./scripts/docker-dev.sh logs [service]

# Execute commands in container
./scripts/docker-dev.sh exec [service] [command]

# Show service status
./scripts/docker-dev.sh status
```

### Docker Compose Profiles

Use Docker Compose profiles to start specific service sets:

```bash
# Development environment
docker-compose --profile dev up -d

# Feature Store only
docker-compose --profile feature-store up -d

# Full environment
docker-compose --profile full up -d

# GPU training
docker-compose --profile gpu up -d

# CPU training
docker-compose --profile cpu up -d

# Monitoring
docker-compose --profile monitoring up -d
```

### Working with Containers

#### Access Shell
```bash
# Development container
docker-compose exec dev /bin/bash

# Feature Store container
docker-compose exec feature-store /bin/bash

# PostgreSQL container
docker-compose exec postgres psql -U astroml -d astroml
```

#### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f feature-store

# Recent logs
docker-compose logs --tail=100 feature-store
```

#### Execute Commands
```bash
# Run tests
docker-compose exec dev pytest tests/ -v

# Start Python shell
docker-compose exec dev python

# Run Feature Store example
docker-compose exec dev python examples/feature_store_example.py
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
# Database
DATABASE_URL=postgresql://astroml:astroml_password@localhost:5432/astroml

# Redis
REDIS_URL=redis://localhost:6379/0

# Feature Store
FEATURE_STORE_PATH=./feature_store
FEATURE_STORE_CACHE_SIZE=1000

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/astroml.log

# Development
ASTROML_ENV=development
DEBUG=true
```

### Volume Mounts

Persistent data is stored in Docker volumes:

- `postgres_data`: PostgreSQL data
- `redis_data`: Redis data
- `feature_store_data`: Feature Store data
- `training_models`: ML model files
- `dev_logs`: Development logs
- `dev_data`: Development data

### Port Configuration

Service ports can be customized in `docker-compose.yml`:

```yaml
ports:
  - "8000:8000"  # Feature Store
  - "8001:8000"  # Ingestion
  - "8888:8888"  # Jupyter Lab
  - "6006:6006"  # TensorBoard
```

## Development Workflow

### 1. Setup Development Environment
```bash
# Start development environment
./scripts/docker-dev.sh dev

# Access Jupyter Lab
# Open http://localhost:8888 in your browser
```

### 2. Work with Feature Store
```bash
# Execute Feature Store example
docker-compose exec dev python examples/feature_store_example.py

# Run Feature Store tests
docker-compose exec dev pytest tests/features/ -v

# Access Feature Store shell
docker-compose exec dev python -c "
from astroml.features import create_feature_store
store = create_feature_store('/app/feature_store)
print('Feature Store ready')
"
```

### 3. Run Tests
```bash
# Run all tests
./scripts/docker-dev.sh test

# Run Feature Store tests only
./scripts/docker-dev.sh test-feature-store

# Run specific test file
docker-compose exec dev pytest tests/features/test_feature_store.py -v
```

### 4. Training Models
```bash
# Start GPU training (requires GPU)
docker-compose --profile gpu up -d training-gpu

# Start CPU training
docker-compose --profile cpu up -d training-cpu

# Monitor training
# Open http://localhost:6006 (GPU) or http://localhost:6007 (CPU)
```

## Production Deployment

### 1. Build Production Images
```bash
# Build production image
docker-compose build production

# Tag for registry
docker tag astroml_production:latest your-registry/astroml:latest
```

### 2. Deploy Production Services
```bash
# Start production environment
docker-compose --profile prod up -d

# Scale services
docker-compose --profile prod up -d --scale production=3
```

### 3. Monitor Production
```bash
# Start monitoring
docker-compose --profile monitoring up -d

# Access Grafana
# Open http://localhost:3000 (admin/admin)
```

## Troubleshooting

### Common Issues

#### Docker Not Running
```bash
# Check Docker status
docker info

# Start Docker Desktop (Windows/macOS)
# Start Docker service (Linux)
sudo systemctl start docker
```

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :8000

# Change ports in docker-compose.yml
ports:
  - "8080:8000"  # Use different host port
```

#### Memory Issues
```bash
# Check Docker memory usage
docker stats

# Increase Docker memory allocation in Docker Desktop
# Or use resource limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

#### Volume Issues
```bash
# List volumes
docker volume ls

# Clean up volumes
docker volume prune

# Recreate volumes
docker-compose down -v
docker-compose up -d
```

### Debug Commands

#### Check Container Status
```bash
# Show all containers
docker-compose ps

# Show container details
docker inspect astroml-feature-store
```

#### Access Container Logs
```bash
# Show recent logs
docker-compose logs --tail=100 feature-store

# Follow logs
docker-compose logs -f feature-store

# Show logs from last hour
docker-compose logs --since="1h" feature-store
```

#### Health Checks
```bash
# Check container health
docker-compose ps

# Run health check manually
docker-compose exec feature-store python -c "import astroml.features"
```

### Performance Optimization

#### Build Optimization
```bash
# Use BuildKit for faster builds
export DOCKER_BUILDKIT=1
docker-compose build

# Use cache
docker-compose build --no-cache=false
```

#### Runtime Optimization
```bash
# Set resource limits
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

## Advanced Usage

### Custom Dockerfiles

Create custom Dockerfiles for specific use cases:

```dockerfile
# Custom Dockerfile for research
FROM astroml:development

# Install additional packages
RUN pip install jupyterlab-widgets plotly seaborn

# Copy research notebooks
COPY research/ /app/research/
```

### Multi-Stage Builds

Optimize image sizes with multi-stage builds:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
```

### Service Mesh

Integrate with service mesh (Istio, Linkerd):

```yaml
# Add service mesh annotations
apiVersion: apps/v1
kind: Deployment
metadata:
  annotations:
    sidecar.istio.io/inject: "true"
```

## Security Considerations

### Container Security
- Use non-root users
- Limit container capabilities
- Scan images for vulnerabilities
- Use image signing

### Network Security
- Use private networks
- Implement TLS encryption
- Configure firewall rules
- Monitor network traffic

### Data Security
- Encrypt sensitive data
- Use secrets management
- Implement access controls
- Regular security audits

## Best Practices

### Development
- Use volume mounts for code changes
- Enable hot reloading
- Use development tools
- Write tests for all features

### Production
- Use specific image tags
- Implement health checks
- Use resource limits
- Monitor performance

### Maintenance
- Regular image updates
- Volume cleanup
- Log rotation
- Security scanning

## Support

For issues and questions:
1. Check this documentation
2. Review logs and error messages
3. Search GitHub issues
4. Create new issue with details

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [AstroML Documentation](https://github.com/Menjay7/astroml)
- [Feature Store Documentation](FEATURE_STORE.md)
