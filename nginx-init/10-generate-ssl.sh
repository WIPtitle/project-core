#!/bin/sh

echo "=== SSL Certificate Generation Script ==="

# Install openssl if needed
if ! command -v openssl >/dev/null 2>&1; then
    echo "Installing openssl..."
    apk add --no-cache openssl
fi

CERT_DIR="/etc/nginx/ssl"
CERT_FILE="$CERT_DIR/self-signed.crt"
KEY_FILE="$CERT_DIR/self-signed.key"

mkdir -p $CERT_DIR

# Extract hostname from PUBLIC_HOST_URL
if [ -n "$PUBLIC_HOST_URL" ]; then
    HOST_ONLY=$(echo "$PUBLIC_HOST_URL" | sed -e 's|^[^/]*//||' -e 's|/.*$||' -e 's|:.*$||')
else
    HOST_ONLY="localhost"
fi

echo "Host: $HOST_ONLY"

# Generate certificates if they don't exist
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "Generating new SSL certificates..."

    if echo "$HOST_ONLY" | grep -qE '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'; then
        SAN="IP:$HOST_ONLY,DNS:localhost"
    else
        SAN="DNS:$HOST_ONLY,DNS:*.$HOST_ONLY,DNS:localhost,IP:127.0.0.1"
    fi

    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/C=IT/ST=State/L=City/O=Organization/CN=$HOST_ONLY" \
        -addext "subjectAltName=$SAN"

    echo "SSL certificates generated successfully"
else
    echo "SSL certificates already exist"
fi

echo "=== SSL setup completed ==="