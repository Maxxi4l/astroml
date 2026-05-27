#!/bin/bash
# Docker Start Script for AstroML
# This script provides easy commands to start various AstroML Docker services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_status "Docker is running"
}

# Function to start core services
start_core() {
    print_status "Starting core services (PostgreSQL, Redis)..."
    docker-compose up -d postgres redis
    print_status "Core services started"
}

# Function to start ingestion services
start_ingestion() {
    print_status "Starting ingestion services..."
    docker-compose up -d ingestion streaming
    print_status "Ingestion services started"
}

# Function to start development environment
start_dev() {
    print_status "Starting development environment..."
    docker-compose --profile dev up -d
    print_status "Development environment started"
    print_status "Jupyter Lab available at http://localhost:8888"
}

# Function to start training (CPU)
start_training_cpu() {
    print_status "Starting CPU training service..."
    docker-compose --profile cpu up -d training-cpu
    print_status "CPU training service started"
}

# Function to start training (GPU)
start_training_gpu() {
    print_status "Starting GPU training service..."
    docker-compose --profile gpu up -d training-gpu
    print_status "GPU training service started"
    print_status "TensorBoard available at http://localhost:6006"
}

# Function to start Soroban development
start_soroban() {
    print_status "Starting Soroban development environment..."
    docker-compose --profile soroban up -d soroban-dev
    print_status "Soroban development environment started"
}

# Function to start monitoring
start_monitoring() {
    print_status "Starting monitoring stack..."
    docker-compose --profile monitoring up -d
    print_status "Monitoring stack started"
    print_status "Prometheus available at http://localhost:9090"
    print_status "Grafana available at http://localhost:3000 (admin/admin)"
}

# Function to start production
start_production() {
    print_status "Starting production services..."
    docker-compose --profile prod up -d
    print_status "Production services started"
}

# Function to start all services
start_all() {
    print_status "Starting all services..."
    docker-compose up -d
    print_status "All services started"
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    docker-compose down
    print_status "Services stopped"
}

# Function to stop all services including volumes
stop_all() {
    print_status "Stopping all services and removing volumes..."
    docker-compose down -v
    print_status "All services stopped and volumes removed"
}

# Function to show status
show_status() {
    print_status "Service status:"
    docker-compose ps
}

# Function to show logs
show_logs() {
    if [ -z "$1" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$1"
    fi
}

# Function to rebuild services
rebuild() {
    if [ -z "$1" ]; then
        print_status "Rebuilding all services..."
        docker-compose build --no-cache
    else
        print_status "Rebuilding service: $1..."
        docker-compose build --no-cache "$1"
    fi
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    docker-compose run --rm dev pytest tests/ -v
}

# Function to run Soroban tests
run_soroban_tests() {
    print_status "Running Soroban contract tests..."
    docker-compose --profile soroban-test run soroban-test
}

# Function to build Soroban contracts
build_soroban() {
    print_status "Building Soroban contracts..."
    docker-compose --profile soroban-build run soroban-build
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker system prune -f
    print_status "Cleanup completed"
}

# Function to show help
show_help() {
    echo "AstroML Docker Management Script"
    echo ""
    echo "Usage: ./docker-start.sh [command]"
    echo ""
    echo "Commands:"
    echo "  core              Start core services (PostgreSQL, Redis)"
    echo "  ingestion         Start ingestion services"
    echo "  dev               Start development environment"
    echo "  training-cpu      Start CPU training service"
    echo "  training-gpu      Start GPU training service"
    echo "  soroban           Start Soroban development environment"
    echo "  monitoring        Start monitoring stack (Prometheus, Grafana)"
    echo "  production        Start production services"
    echo "  all               Start all services"
    echo "  stop              Stop services"
    echo "  stop-all          Stop all services and remove volumes"
    echo "  status            Show service status"
    echo "  logs [service]    Show logs (all services or specific service)"
    echo "  rebuild [service] Rebuild services"
    echo "  test              Run tests"
    echo "  soroban-test      Run Soroban contract tests"
    echo "  soroban-build     Build Soroban contracts"
    echo "  cleanup           Clean up Docker resources"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./docker-start.sh core"
    echo "  ./docker-start.sh dev"
    echo "  ./docker-start.sh logs ingestion"
    echo "  ./docker-start.sh rebuild ingestion"
}

# Main script logic
main() {
    check_docker
    
    case "${1:-help}" in
        core)
            start_core
            ;;
        ingestion)
            start_core
            start_ingestion
            ;;
        dev)
            start_core
            start_dev
            ;;
        training-cpu)
            start_core
            start_training_cpu
            ;;
        training-gpu)
            start_core
            start_training_gpu
            ;;
        soroban)
            start_soroban
            ;;
        monitoring)
            start_core
            start_monitoring
            ;;
        production)
            start_core
            start_production
            ;;
        all)
            start_all
            ;;
        stop)
            stop_services
            ;;
        stop-all)
            stop_all
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        rebuild)
            rebuild "$2"
            ;;
        test)
            run_tests
            ;;
        soroban-test)
            run_soroban_tests
            ;;
        soroban-build)
            build_soroban
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
