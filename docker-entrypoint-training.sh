# Docker entrypoint script for AstroML Training Service
# This script initializes the training environment and starts training

#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}[INFO]${NC} Starting AstroML Training Service"

# Function to wait for database
wait_for_db() {
    echo -e "${YELLOW}[WAIT]${NC} Waiting for PostgreSQL to be ready..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" > /dev/null 2>&1; then
            echo -e "${GREEN}[INFO]${NC} PostgreSQL is ready"
            return 0
        fi
        
        echo -e "${YELLOW}[WAIT]${NC} PostgreSQL not ready yet. Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}[ERROR]${NC} PostgreSQL failed to become ready"
    return 1
}

# Wait for database
wait_for_db

# Print environment info
echo -e "${GREEN}[INFO]${NC} Environment Information:"
echo -e "${GREEN}[INFO]${NC} Python version: $(python --version)"
echo -e "${GREEN}[INFO]${NC} PyTorch version: $(python -c 'import torch; print(torch.__version__)' 2>/dev/null || echo 'Not installed')"
echo -e "${GREEN}[INFO]${NC} CUDA available: $(python -c 'import torch; print(torch.cuda.is_available())' 2>/dev/null || echo 'N/A')"

# Create necessary directories
mkdir -p /app/models /app/data /app/logs

# Start the training service
echo -e "${GREEN}[INFO]${NC} Starting training service..."
exec python -m astroml.training.train_gcn
