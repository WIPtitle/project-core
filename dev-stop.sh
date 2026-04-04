#!/bin/bash
#
# Dev Environment Stopper
# Stops all dev services and restores original .env
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# PID files
GPIO_PID_FILE="$SCRIPT_DIR/.gpio-monitor.pid"
MP3_PID_FILE="$SCRIPT_DIR/.mp3-player-server.pid"
VALVE_PID_FILE="$SCRIPT_DIR/.valve-controller.pid"

echo -e "${YELLOW}Stopping dev environment...${NC}"

# Stop GPIO Monitor
if [ -f "$GPIO_PID_FILE" ]; then
    PID=$(cat "$GPIO_PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping GPIO Monitor (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null || true
        fi
    fi
    rm -f "$GPIO_PID_FILE"
    echo -e "GPIO Monitor: ${GREEN}Stopped${NC}"
else
    echo -e "GPIO Monitor: ${YELLOW}Not running${NC}"
fi

# Stop MP3 Player Server
if [ -f "$MP3_PID_FILE" ]; then
    PID=$(cat "$MP3_PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping MP3 Player Server (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null || true
        fi
    fi
    rm -f "$MP3_PID_FILE"
    echo -e "MP3 Player Server: ${GREEN}Stopped${NC}"
else
    echo -e "MP3 Player Server: ${YELLOW}Not running${NC}"
fi

# Stop Valve Controller
if [ -f "$VALVE_PID_FILE" ]; then
    PID=$(cat "$VALVE_PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping Valve Controller (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null || true
        fi
    fi
    rm -f "$VALVE_PID_FILE"
    echo -e "Valve Controller: ${GREEN}Stopped${NC}"
else
    echo -e "Valve Controller: ${YELLOW}Not running${NC}"
fi

# Stop Docker Compose
echo "Stopping Docker containers..."
docker compose down 2>/dev/null || true
echo -e "Docker Compose: ${GREEN}Stopped${NC}"

# Delete log files
rm -f "$SCRIPT_DIR/logs/gpio-monitor.log" "$SCRIPT_DIR/logs/mp3-player-server.log" "$SCRIPT_DIR/logs/valve-controller.log"
echo -e "Log files: ${GREEN}Deleted${NC}"

echo -e "\n${GREEN}Dev environment stopped successfully.${NC}"
