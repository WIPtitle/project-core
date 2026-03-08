#!/bin/bash
#
# Dev Environment Runner
# Starts GPIO Monitor, MP3 Player Server locally, and docker compose
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"
DATA_DIR="$SCRIPT_DIR/dev-data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# PID files
GPIO_PID_FILE="$SCRIPT_DIR/.gpio-monitor.pid"
MP3_PID_FILE="$SCRIPT_DIR/.mp3-player-server.pid"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Project Core - Dev Environment${NC}"
echo -e "${GREEN}========================================${NC}"

# Create directories
mkdir -p "$CONFIG_DIR"
mkdir -p "$DATA_DIR/mp3-storage"
mkdir -p "$SCRIPT_DIR/logs"

# Log files
GPIO_LOG="$SCRIPT_DIR/logs/gpio-monitor.log"
MP3_LOG="$SCRIPT_DIR/logs/mp3-player-server.log"

# Clear old logs on startup
> "$GPIO_LOG"
> "$MP3_LOG"
echo -e "${YELLOW}Logs cleared${NC}"

# Create config files if they don't exist
if [ ! -f "$CONFIG_DIR/gpio-monitor.json" ]; then
    echo '{"port": 8787, "monitored_pins": [], "pin_config": {}}' > "$CONFIG_DIR/gpio-monitor.json"
    echo -e "${YELLOW}Created: $CONFIG_DIR/gpio-monitor.json${NC}"
fi

if [ ! -f "$CONFIG_DIR/mp3-player-server.json" ]; then
    cat > "$CONFIG_DIR/mp3-player-server.json" << EOF
{
  "port": 8888,
  "storage_dir": "$DATA_DIR/mp3-storage",
  "audio_device": null
}
EOF
    echo -e "${YELLOW}Created: $CONFIG_DIR/mp3-player-server.json${NC}"
fi

# Export environment variables for dev paths
export GPIO_MONITOR_CONFIG_PATH="$CONFIG_DIR/gpio-monitor.json"
export MP3_PLAYER_SERVER_CONFIG_PATH="$CONFIG_DIR/mp3-player-server.json"

echo -e "${GREEN}Environment:${NC}"
echo -e "  GPIO_MONITOR_CONFIG_PATH=$GPIO_MONITOR_CONFIG_PATH"
echo -e "  MP3_PLAYER_SERVER_CONFIG_PATH=$MP3_PLAYER_SERVER_CONFIG_PATH"

# Cleanup function
CLEANUP_DONE=false
cleanup() {
    if [ "$CLEANUP_DONE" = true ]; then
        return
    fi
    CLEANUP_DONE=true

    echo -e "\n${YELLOW}Shutting down dev environment...${NC}"

    # Stop GPIO Monitor
    if [ -f "$GPIO_PID_FILE" ]; then
        PID=$(cat "$GPIO_PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Stopping GPIO Monitor (PID: $PID)..."
            kill "$PID" 2>/dev/null || true
        fi
        rm -f "$GPIO_PID_FILE"
    fi

    # Stop MP3 Player Server
    if [ -f "$MP3_PID_FILE" ]; then
        PID=$(cat "$MP3_PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Stopping MP3 Player Server (PID: $PID)..."
            kill "$PID" 2>/dev/null || true
        fi
        rm -f "$MP3_PID_FILE"
    fi

    # Stop docker compose
    echo "Stopping Docker containers..."
    docker compose down 2>/dev/null || true

    # Restore .git files in submodules
    for gitfile in "$SCRIPT_DIR"/microservices/*/.git.dev-bak; do
        [ -e "$gitfile" ] && mv "$gitfile" "${gitfile%.dev-bak}"
    done

    # Delete log files
    rm -f "$GPIO_LOG" "$MP3_LOG"

    echo -e "${GREEN}Dev environment stopped.${NC}"
}

trap cleanup SIGINT SIGTERM EXIT

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed${NC}"
    exit 1
fi

# Check .env exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

echo -e "${GREEN}Using .env configuration${NC}"

# Start GPIO Monitor
echo -e "\n${GREEN}Starting GPIO Monitor...${NC}"
cd "$SCRIPT_DIR/microservices/gpio-monitor"
python3 gpio-monitor-main.py > "$GPIO_LOG" 2>&1 &
echo $! > "$GPIO_PID_FILE"
echo -e "GPIO Monitor started on ${GREEN}http://localhost:8787${NC}"
echo -e "  Log: ${YELLOW}$GPIO_LOG${NC}"

# Start MP3 Player Server
echo -e "\n${GREEN}Starting MP3 Player Server...${NC}"
cd "$SCRIPT_DIR/microservices/mp3-player-server"
python3 mp3-player-server-main.py > "$MP3_LOG" 2>&1 &
echo $! > "$MP3_PID_FILE"
echo -e "MP3 Player Server started on ${GREEN}http://localhost:8888${NC}"
echo -e "  Log: ${YELLOW}$MP3_LOG${NC}"

# Wait for services to start
sleep 2

# Check if services are running
echo -e "\n${YELLOW}Checking services...${NC}"

if curl -s http://localhost:8787/api/pins > /dev/null 2>&1; then
    echo -e "GPIO Monitor: ${GREEN}OK${NC}"
else
    echo -e "GPIO Monitor: ${RED}FAILED${NC}"
fi

if curl -s http://localhost:8888/api/status > /dev/null 2>&1; then
    echo -e "MP3 Player Server: ${GREEN}OK${NC}"
else
    echo -e "MP3 Player Server: ${RED}FAILED${NC}"
fi

# Docker BuildKit with git submodules only sees committed files, not local modifications.
# Temporarily hide .git files in submodules so BuildKit reads the actual filesystem.
echo -e "\n${YELLOW}Preparing submodules for build...${NC}"
for gitfile in "$SCRIPT_DIR"/microservices/*/.git; do
    [ -e "$gitfile" ] && mv "$gitfile" "${gitfile}.dev-bak"
done

restore_git_files() {
    for gitfile in "$SCRIPT_DIR"/microservices/*/.git.dev-bak; do
        [ -e "$gitfile" ] && mv "$gitfile" "${gitfile%.dev-bak}"
    done
}

# Start Docker Compose
echo -e "\n${GREEN}Starting Docker Compose...${NC}"
echo -e "${YELLOW}Note: Services will connect to GPIO/MP3 via host.docker.internal${NC}"
echo ""

cd "$SCRIPT_DIR"
docker compose up --build
BUILD_EXIT=$?

# Restore .git files after build
restore_git_files

exit $BUILD_EXIT

# Cleanup will be called on exit
