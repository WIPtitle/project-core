#!/bin/bash

STATE_FILE="/tmp/health_status.json"
PORT=8000
DEVICES_MANAGER_URL="http://devices-manager:8000"

perform_health_checks() {
    local json_servers=""

    # Fetch GPIO servers from devices-manager config API
    gpio_urls=$(curl -sf -m 5 "$DEVICES_MANAGER_URL/config/gpio-servers" 2>/dev/null | \
        grep -o '"url":"[^"]*"' | sed 's/"url":"//g;s/"//g')

    for url in $gpio_urls; do
        [ -z "$url" ] && continue
        [ -n "$json_servers" ] && json_servers="${json_servers},"

        if curl -sf -m 5 "$url" > /dev/null 2>&1; then
            status="healthy"
        else
            status="unreachable"
        fi

        json_servers="${json_servers}\"${url}\":\"${status}\""
    done

    # Fetch MP3 servers from devices-manager config API
    mp3_urls=$(curl -sf -m 5 "$DEVICES_MANAGER_URL/config/mp3-servers" 2>/dev/null | \
        grep -o '"url":"[^"]*"' | sed 's/"url":"//g;s/"//g')

    for url in $mp3_urls; do
        [ -z "$url" ] && continue
        [ -n "$json_servers" ] && json_servers="${json_servers},"

        if curl -sf -m 5 "$url" > /dev/null 2>&1; then
            status="healthy"
        else
            status="unreachable"
        fi

        json_servers="${json_servers}\"${url}\":\"${status}\""
    done

    echo "{${json_servers}}" > "$STATE_FILE"

    echo "[$(date)] Health check completed"
}

(
    while true; do
        perform_health_checks
        sleep 60
    done
) &

# Wait a bit for devices-manager to be ready on first check
sleep 10
perform_health_checks

echo "Starting health check server on port $PORT..."

while true; do
    {
        read -r request

        response=$(cat "$STATE_FILE" 2>/dev/null || echo '{}')

        echo -e "HTTP/1.1 200 OK\r"
        echo -e "Content-Type: application/json\r"
        echo -e "Cache-Control: no-cache\r"
        echo -e "Connection: close\r"
        echo -e "\r"
        echo "$response"
    } | nc -l -p $PORT
done
