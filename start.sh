#!/bin/bash
# Startup script for the full stack

set -e

echo "========================================="
echo "  Starting Full Stack Application"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if Docker is running
echo "1. Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi
print_success "Docker is running"
echo ""

# Check if Supabase CLI is installed
echo "2. Checking Supabase CLI..."
if ! command -v supabase &> /dev/null; then
    print_error "Supabase CLI is not installed. Install it from https://supabase.com/docs/guides/cli"
    exit 1
fi
print_success "Supabase CLI is installed"
echo ""

# Start Supabase
echo "3. Starting Supabase..."
print_info "This may take a few minutes on first run (pulling Docker images)..."
if supabase start; then
    print_success "Supabase started successfully"
else
    print_error "Failed to start Supabase"
    exit 1
fi
echo ""

# Get Supabase credentials
echo "4. Getting Supabase credentials..."
ANON_KEY=$(supabase status | grep "anon key:" | awk '{print $3}')
SERVICE_ROLE_KEY=$(supabase status | grep "service_role key:" | awk '{print $3}')

if [ -z "$ANON_KEY" ] || [ -z "$SERVICE_ROLE_KEY" ]; then
    print_error "Failed to get Supabase keys"
    exit 1
fi

# Update .env file
echo "5. Updating .env file..."
sed -i "s|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY=$ANON_KEY|" .env
sed -i "s|SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SERVICE_ROLE_KEY|" .env
sed -i "s|VITE_SUPABASE_ANON_KEY=.*|VITE_SUPABASE_ANON_KEY=$ANON_KEY|" .env
print_success "Environment variables updated"
echo ""

# Start Docker Compose services
echo "6. Starting Temporal and Frontend services..."
print_info "This will start Temporal, Temporal UI, Worker, and Frontend..."

if [ "$1" == "dev" ]; then
    print_info "Starting in DEVELOPMENT mode (with live reload)..."
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
else
    docker compose up -d
fi

if [ $? -eq 0 ]; then
    print_success "All services started successfully"
else
    print_error "Failed to start services"
    exit 1
fi
echo ""

# Wait for services to be healthy
echo "7. Waiting for services to be ready..."
sleep 5
print_success "Services should now be ready"
echo ""

# Display status
echo "========================================="
echo "  🎉 Stack is Ready!"
echo "========================================="
echo ""
echo "Access your services:"
echo "  📱 Frontend:        http://localhost:3000"
echo "  🗄️  Supabase Studio: http://localhost:54323"
echo "  ⏱️  Temporal UI:     http://localhost:8080"
echo "  🔧 Supabase API:    http://localhost:54321"
echo ""
echo "View logs:"
echo "  All services:       make logs"
echo "  Frontend only:      make logs-frontend"
echo "  Temporal worker:    make logs-temporal"
echo ""
echo "Stop services:"
echo "  Stop all:           make down"
echo "  Reset database:     make reset"
echo ""
print_info "Press Ctrl+C to stop watching logs..."
echo ""

# Follow logs
docker compose logs -f
