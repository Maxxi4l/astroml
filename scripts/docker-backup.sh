#!/bin/bash
# Docker backup script for AstroML
# Creates comprehensive backups of databases and configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/astroml_backup_$TIMESTAMP"

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_PATH"
print_status "Creating backup in $BACKUP_PATH"

# Backup PostgreSQL
print_status "Backing up PostgreSQL..."
docker-compose exec postgres pg_dump \
    -U astroml -d astroml --verbose \
    > "$BACKUP_PATH/postgres.sql" 2>&1 || print_error "PostgreSQL backup failed"

# Compress PostgreSQL backup
print_status "Compressing PostgreSQL backup..."
gzip "$BACKUP_PATH/postgres.sql"

# Backup Redis
print_status "Backing up Redis..."
docker-compose exec redis redis-cli BGSAVE > /dev/null
sleep 2

# Copy Redis dump file
docker cp astroml-redis:/data/dump.rdb "$BACKUP_PATH/redis-dump.rdb" 2>/dev/null || \
    print_warning "Redis dump file not found (AOF might be enabled instead)"

# Backup configurations
print_status "Backing up configurations..."
cp -v .env "$BACKUP_PATH/.env.backup" 2>/dev/null || print_warning ".env file not found"
cp -v docker-compose.yml "$BACKUP_PATH/docker-compose.yml.backup"
cp -v docker-compose.prod.yml "$BACKUP_PATH/docker-compose.prod.yml.backup" 2>/dev/null || true
cp -rv monitoring/ "$BACKUP_PATH/monitoring.backup" 2>/dev/null || print_warning "Monitoring config not found"
cp -rv config/ "$BACKUP_PATH/config.backup" 2>/dev/null || print_warning "Config directory not found"

# Backup application code
print_status "Backing up application code..."
tar -czf "$BACKUP_PATH/astroml-code.tar.gz" astroml/ --exclude='*.pyc' --exclude='__pycache__'

# Generate backup manifest
print_status "Generating backup manifest..."
cat > "$BACKUP_PATH/MANIFEST.txt" <<EOF
AstroML Backup Manifest
Generated: $(date)
Backup Directory: $BACKUP_PATH

Contents:
- postgres.sql.gz: PostgreSQL database dump
- redis-dump.rdb: Redis database snapshot
- .env.backup: Environment configuration
- docker-compose.yml.backup: Docker Compose configuration
- docker-compose.prod.yml.backup: Production Docker Compose configuration
- monitoring.backup/: Monitoring configurations
- config.backup/: Application configurations
- astroml-code.tar.gz: Application source code

Backup Verification:
EOF

# Verify backup files
print_status "Verifying backup files..."
cd "$BACKUP_PATH"
ls -lh >> MANIFEST.txt
echo "" >> MANIFEST.txt
echo "SHA256 Checksums:" >> MANIFEST.txt
sha256sum * >> MANIFEST.txt 2>/dev/null || true
cd - > /dev/null

# Calculate total size
TOTAL_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
print_status "Backup completed successfully"
print_status "Backup location: $BACKUP_PATH"
print_status "Backup size: $TOTAL_SIZE"

# Archive backup
print_status "Creating compressed archive..."
tar -czf "$BACKUP_DIR/astroml_backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" "astroml_backup_$TIMESTAMP"

# Clean up uncompressed backup if requested
if [ "${2:-}" = "--compress" ]; then
    print_status "Removing uncompressed backup..."
    rm -rf "$BACKUP_PATH"
fi

print_status "Backup process complete"
print_status "Archive: $BACKUP_DIR/astroml_backup_$TIMESTAMP.tar.gz"

# Optional: Upload to remote storage
if [ -n "${BACKUP_UPLOAD_URL:-}" ]; then
    print_status "Uploading backup to remote storage..."
    curl -X POST -F "file=@$BACKUP_DIR/astroml_backup_$TIMESTAMP.tar.gz" "$BACKUP_UPLOAD_URL"
fi
