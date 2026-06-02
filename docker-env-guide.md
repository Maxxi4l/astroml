# Docker Environment Configuration Guide
# This guide explains all environment variables used in AstroML Docker setup

## Quick Setup

To get started quickly:

```bash
# 1. Copy the environment template
cp .env.example .env

# 2. Update database passwords (IMPORTANT for production)
sed -i 's/your_secure_password_here/your_actual_password/g' .env

# 3. Start services
docker-compose up -d

# 4. Check health
./scripts/docker-health-check.sh
```

## Environment Variable Reference

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | astroml | Database name |
| `POSTGRES_USER` | astroml | Database user |
| `POSTGRES_PASSWORD` | astroml_password | Database password ⚠️ Change in production |
| `POSTGRES_HOST` | postgres | Database hostname |
| `POSTGRES_PORT` | 5432 | Database port |
| `DATABASE_URL` | postgresql://astroml:... | Full connection string |

### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | redis | Redis hostname |
| `REDIS_PORT` | 6379 | Redis port |
| `REDIS_PASSWORD` | (empty) | Redis password |
| `REDIS_URL` | redis://redis:6379/0 | Full connection string |
| `REDIS_DB` | 0 | Redis database number |

### Stellar Network Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `STELLAR_NETWORK_PASSPHRASE` | Public Global... | Network identifier |
| `STELLAR_HORIZON_URL` | https://horizon.stellar.org | Horizon API endpoint |
| `STELLAR_NETWORK` | public | Network environment |
| `STELLAR_SECRET_KEY` | (empty) | Stellar account secret key |

### Application Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level |
| `PYTHONPATH` | /app | Python path |
| `APP_ENV` | development | Application environment |
| `DEBUG` | False | Debug mode |

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | 0.0.0.0 | API listen address |
| `API_PORT` | 8000 | API listen port |
| `API_WORKERS` | 4 | Number of worker processes |
| `API_TIMEOUT` | 30 | Request timeout in seconds |

### Training Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TRAINING_BATCH_SIZE` | 32 | Training batch size |
| `TRAINING_EPOCHS` | 100 | Number of epochs |
| `TRAINING_LEARNING_RATE` | 0.001 | Learning rate |
| `TRAINING_VALIDATION_SPLIT` | 0.2 | Validation data split |
| `CUDA_VISIBLE_DEVICES` | 0 | GPU device IDs |

### Monitoring Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMETHEUS_RETENTION` | 15d | Metrics retention period |
| `GRAFANA_ADMIN_PASSWORD` | admin | Grafana admin password |
| `METRICS_PORT` | 8080 | Prometheus metrics port |

## Environment Templates for Different Scenarios

### Development Environment

```bash
APP_ENV=development
DEBUG=True
LOG_LEVEL=DEBUG
TRAINING_BATCH_SIZE=8
TRAINING_EPOCHS=10
```

### Production Environment

```bash
APP_ENV=production
DEBUG=False
LOG_LEVEL=WARNING
POSTGRES_PASSWORD=<strong_password>
REDIS_PASSWORD=<strong_password>
STELLAR_SECRET_KEY=<your_secret_key>
TRAINING_BATCH_SIZE=64
API_WORKERS=8
```

### Testing Environment

```bash
APP_ENV=testing
DEBUG=True
LOG_LEVEL=DEBUG
POSTGRES_DB=astroml_test
REDIS_DB=1
TRAINING_EPOCHS=1
TRAINING_BATCH_SIZE=4
```

## Secrets Management

⚠️ **IMPORTANT**: Never commit `.env` files to version control.

### Using Docker Secrets (Production)

For Docker Swarm deployments:

```bash
# Create secrets
echo "strong_password" | docker secret create postgres_password -
echo "secret_key" | docker secret create stellar_key -

# Reference in docker-compose.yml
secrets:
  - postgres_password
  - stellar_key
```

### Using Environment Variables

```bash
# Pass during docker-compose up
export POSTGRES_PASSWORD=strong_password
docker-compose up -d
```

### Secure Password Generation

```bash
# Generate random passwords
openssl rand -base64 32
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Validation

To validate your environment configuration:

```bash
# Run health checks
./scripts/docker-health-check.sh

# Test database connection
docker-compose exec postgres psql -U astroml -d astroml -c "SELECT 1"

# Test Redis connection
docker-compose exec redis redis-cli ping

# View service logs
docker-compose logs -f
```

## Troubleshooting

### Services won't start

1. Check environment variables:
   ```bash
   docker-compose config | grep -A 20 "environment:"
   ```

2. View service logs:
   ```bash
   docker-compose logs <service_name>
   ```

3. Verify ports are not in use:
   ```bash
   lsof -i :<port_number>
   ```

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose logs postgres

# Verify connection string
echo $DATABASE_URL

# Test connection manually
psql $DATABASE_URL -c "SELECT 1"
```

### Permission issues

```bash
# Fix ownership in containers
docker-compose exec <service> chown -R astroml:astroml /app

# Fix host-side mount permissions
sudo chown -R $USER:$USER ./data
```
