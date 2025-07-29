#!/bin/bash

# Test script for Docker Compose configuration
set -e

echo "Testing Docker Compose configuration..."

# Check if docker-compose.yml is valid
echo "1. Validating docker-compose.yml syntax..."
docker-compose config --quiet
echo "✓ Docker Compose configuration is valid"

# Check if services are defined correctly
echo "2. Checking services..."
services=$(docker-compose config --services)
expected_services="catmandu-core echo-cattackle"

for service in $expected_services; do
    if echo "$services" | grep -q "$service"; then
        echo "✓ Service '$service' is defined"
    else
        echo "✗ Service '$service' is missing"
        exit 1
    fi
done

# Check if network is defined
echo "3. Checking network configuration..."
if docker-compose config | grep -q "catmandu-network"; then
    echo "✓ Custom network 'catmandu-network' is defined"
else
    echo "✗ Custom network 'catmandu-network' is missing"
    exit 1
fi

# Check if volumes are defined
echo "4. Checking volume configuration..."
if docker-compose config | grep -q "update_data"; then
    echo "✓ Volume 'update_data' is defined"
else
    echo "✗ Volume 'update_data' is missing"
    exit 1
fi

if docker-compose config | grep -q "chat_logs"; then
    echo "✓ Volume 'chat_logs' is defined"
else
    echo "✗ Volume 'chat_logs' is missing"
    exit 1
fi

# Check if dependencies are configured
echo "5. Checking service dependencies..."
if docker-compose config | grep -A 20 "catmandu-core:" | grep -q "depends_on"; then
    echo "✓ catmandu-core has service dependencies configured"
else
    echo "✗ Service dependency is missing"
    exit 1
fi

# Check if ports are exposed
echo "6. Checking port configuration..."
if docker-compose config | grep -q "published: \"8000\""; then
    echo "✓ Port 8000 is exposed for catmandu-core"
else
    echo "✗ Port 8000 is not exposed"
    exit 1
fi

echo ""
echo "🎉 All Docker Compose configuration tests passed!"
echo ""
echo "To start the services, run:"
echo "  docker-compose up -d"
echo ""
echo "To view logs, run:"
echo "  docker-compose logs -f"
echo ""
echo "To stop the services, run:"
echo "  docker-compose down"
