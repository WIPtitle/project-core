#!/bin/bash

STATE_FILE="/tmp/health_status.json"
PORT=8000

perform_health_checks() {
    local json_servers=""

    if [ -n "$GPIO_MONITOR_URLS" ]; then
        IFS=',' read -ra GPIO_ARRAY <<< "$GPIO_MONITOR_URLS"
        for url in "${GPIO_ARRAY[@]}"; do
            url=$(echo "$url" | xargs)
            [ -z "$url" ] && continue

            [ -n "$json_servers" ] && json_servers="${json_servers},"

            if curl -sf -m 5 "$url" > /dev/null 2>&1; then
                status="healthy"
            else
                status="unreachable"
            fi

            json_servers="${json_servers}\"${url}\":\"${status}\""
        done
    fi

    if [ -n "$MP3_PLAYER_SERVER_URLS" ]; then
        IFS=',' read -ra MP3_ARRAY <<< "$MP3_PLAYER_SERVER_URLS"
        for entry in "${MP3_ARRAY[@]}"; do
            entry=$(echo "$entry" | xargs)
            [ -z "$entry" ] && continue

            if [[ "$entry" == *"@"* ]]; then
                url="${entry#*@}"
            else
                url="$entry"
            fi

            [ -n "$json_servers" ] && json_servers="${json_servers},"

            if curl -sf -m 5 "$url" > /dev/null 2>&1; then
                status="healthy"
            else
                status="unreachable"
            fi

            json_servers="${json_servers}\"${url}\":\"${status}\""
        done
    fi

    echo "{${json_servers}}" > "$STATE_FILE"

    echo "[$(date)] Health check completed"
}

(
    while true; do
        perform_health_checks
        sleep 60
    done
) &

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