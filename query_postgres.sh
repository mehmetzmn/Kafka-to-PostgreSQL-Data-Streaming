#!/bin/bash

# Check if psql is available
if command -v psql &> /dev/null; then
    echo "Using local psql client..."
    PGPASSWORD=postgres psql "postgresql://postgres:postgres@localhost:5432/sensordata" -c "SELECT * FROM sensor_measurements;"
else
    echo "Using docker exec (psql not found locally)..."
    docker exec -it $(docker compose ps -q postgres) psql -U postgres -d sensordata -c "SELECT * FROM sensor_measurements;"
fi