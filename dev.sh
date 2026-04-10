#!/bin/bash
# ProductPhotoManager - Dev Mode (macOS/Linux)
set -e

echo ""
echo "  ===================================================="
echo "   Product Photo Manager - Dev Mode"
echo "  ===================================================="
echo ""

# Start PostgreSQL
echo "  [1/3] Starting PostgreSQL..."
docker-compose up -d db

# Wait for PostgreSQL
echo "  [*] Waiting for PostgreSQL..."
until docker-compose exec -T db pg_isready -U ppm_user -d productphotomanager > /dev/null 2>&1; do
    sleep 1
done
echo "  [OK] PostgreSQL ready"

# Install deps if needed
if [ ! -f "backend/__installed__" ]; then
    echo ""
    echo "  [2/3] Installing Python dependencies..."
    pip install -r backend/requirements.txt -q
    touch backend/__installed__
else
    echo "  [2/3] Python dependencies OK"
fi

if [ ! -d "frontend/node_modules" ]; then
    echo ""
    echo "  [3/3] Installing frontend dependencies..."
    cd frontend && npm install && cd ..
else
    echo "  [3/3] Frontend dependencies OK"
fi

echo ""
echo "  ===================================================="
echo "   Starting servers..."
echo "  ===================================================="
echo ""
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "   Login: admin / admin1234"
echo ""
echo "   Press Ctrl+C to stop all servers"
echo "  ===================================================="
echo ""

# Open browser after 3 seconds
(sleep 3 && open http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null) &

# Start backend and frontend
python -m uvicorn backend.api.main:app --reload --port 8000 &
BACKEND_PID=$!
cd frontend && npx vite --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

# Cleanup on exit
cleanup() {
    echo ""
    echo "  Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    docker-compose stop db 2>/dev/null
    echo "  Done!"
}
trap cleanup EXIT INT TERM

wait
