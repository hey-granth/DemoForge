#!/bin/bash
set -e

# Forward SIGTERM and SIGINT to supervisord for graceful shutdown
_term() {
    echo "Caught signal — shutting down…"
    if [ -n "$SUPERVISOR_PID" ]; then
        kill -TERM "$SUPERVISOR_PID" 2>/dev/null || true
        wait "$SUPERVISOR_PID" 2>/dev/null || true
    fi
    exit 0
}

trap _term SIGTERM SIGINT

echo "============================================"
echo "  DemoForge — All-in-One Container"
echo "============================================"
echo ""
echo "  UI:     http://localhost:8080"
echo "  API:    http://localhost:8080/api"
echo "  Health: http://localhost:8080/api/health"
echo ""
echo "  Starting services: redis, api, worker, nginx"
echo "============================================"

# Start supervisord in the background so we can trap signals
/usr/bin/supervisord -c /etc/supervisord.conf &
SUPERVISOR_PID=$!

# Wait for supervisord to exit
wait "$SUPERVISOR_PID"

