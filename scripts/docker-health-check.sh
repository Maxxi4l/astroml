#!/bin/bash
# Docker health check and validation script for AstroML
# This script validates that all Docker services are properly running and healthy

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

print_section() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC} $1"
    ((FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠ WARN${NC} $1"
    ((WARNINGS++))
}

# Check if Docker is running
check_docker_running() {
    print_section "Docker Environment Check"
    
    if docker info > /dev/null 2>&1; then
        print_pass "Docker daemon is running"
    else
        print_fail "Docker daemon is not running"
        return 1
    fi
    
    if docker-compose --version > /dev/null 2>&1; then
        print_pass "Docker Compose is installed"
    else
        print_fail "Docker Compose is not installed"
        return 1
    fi
}

# Check if network exists
check_network() {
    print_section "Docker Network Check"
    
    if docker network ls | grep -q astroml-network; then
        print_pass "astroml-network exists"
    else
        print_warning "astroml-network does not exist (create with: docker-compose up -d)"
    fi
}

# Check individual services
check_service() {
    local service_name=$1
    local port=$2
    local protocol=${3:-http}
    
    if docker-compose ps | grep -q "$service_name"; then
        if docker-compose ps "$service_name" | grep -q "Up"; then
            print_pass "$service_name is running"
            
            # Try to reach the service if port is provided
            if [ -n "$port" ]; then
                if timeout 2 bash -c "cat < /dev/null > /dev/tcp/localhost/$port" 2>/dev/null; then
                    print_pass "$service_name is responding on port $port"
                else
                    print_warning "$service_name is running but not responding on port $port"
                fi
            fi
        else
            print_fail "$service_name is not running"
        fi
    else
        print_warning "$service_name is not deployed"
    fi
}

# Check running containers
check_services() {
    print_section "Service Health Checks"
    
    check_service "astroml-postgres" "5432"
    check_service "astroml-redis" "6379"
    check_service "astroml-ingestion" "8000"
    check_service "astroml-streaming" "8001"
    check_service "astroml-training-cpu" "6007"
    check_service "astroml-training-gpu" "6006"
    check_service "astroml-dev" "8002"
    check_service "astroml-production" "8000"
    check_service "astroml-prometheus" "9090"
    check_service "astroml-grafana" "3000"
}

# Check volumes
check_volumes() {
    print_section "Volume Checks"
    
    local volumes=(
        "astroml_postgres_data"
        "astroml_redis_data"
        "astroml_ingestion_logs"
        "astroml_training_models"
        "astroml_training_logs"
    )
    
    for volume in "${volumes[@]}"; do
        if docker volume ls | grep -q "$volume"; then
            print_pass "Volume $volume exists"
        else
            print_warning "Volume $volume does not exist"
        fi
    done
}

# Check .env file
check_env() {
    print_section "Environment Configuration Check"
    
    if [ -f ".env" ]; then
        print_pass ".env file exists"
    else
        if [ -f ".env.example" ]; then
            print_warning ".env file not found (copy from .env.example)"
        else
            print_fail ".env.example not found"
        fi
    fi
}

# Check images
check_images() {
    print_section "Docker Images Check"
    
    local images=(
        "python:3.11-slim"
        "postgres:15-alpine"
        "redis:7-alpine"
        "prom/prometheus"
        "grafana/grafana"
    )
    
    for image in "${images[@]}"; do
        if docker images | grep -q "$image"; then
            print_pass "Image $image is available"
        else
            print_warning "Image $image not pulled (will be pulled on first use)"
        fi
    done
}

# Check database connectivity
check_database() {
    print_section "Database Connectivity Check"
    
    if docker-compose ps postgres 2>/dev/null | grep -q "Up"; then
        if docker exec astroml-postgres pg_isready -U astroml -d astroml > /dev/null 2>&1; then
            print_pass "PostgreSQL database is responding"
        else
            print_fail "PostgreSQL database is not responding to connections"
        fi
    else
        print_warning "PostgreSQL is not running"
    fi
}

# Check Redis connectivity
check_redis() {
    print_section "Redis Connectivity Check"
    
    if docker-compose ps redis 2>/dev/null | grep -q "Up"; then
        if docker exec astroml-redis redis-cli ping > /dev/null 2>&1; then
            print_pass "Redis is responding"
        else
            print_fail "Redis is not responding to connections"
        fi
    else
        print_warning "Redis is not running"
    fi
}

# Generate summary report
generate_summary() {
    print_section "Health Check Summary"
    
    total=$((PASSED + FAILED + WARNINGS))
    
    echo ""
    echo -e "Total Checks: $total"
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All critical checks passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║       AstroML Docker Health Check & Validation        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    check_docker_running || exit 1
    check_network
    check_env
    check_images
    check_volumes
    check_services
    check_database
    check_redis
    generate_summary
}

# Run main function
main "$@"
