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

# Generate certificates if they don't exist
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "Generating new SSL certificates..."

    # Auto-detect local IP for SAN
    LOCAL_IP=$(hostname -i 2>/dev/null | awk '{print $1}')

    SAN="DNS:localhost,IP:127.0.0.1"
    if [ -n "$LOCAL_IP" ] && [ "$LOCAL_IP" != "127.0.0.1" ]; then
        SAN="$SAN,IP:$LOCAL_IP"
    fi

    echo "SAN: $SAN"

    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/C=IT/ST=State/L=City/O=Organization/CN=localhost" \
        -addext "subjectAltName=$SAN"

    echo "SSL certificates generated successfully"
else
    echo "SSL certificates already exist"
fi

echo "=== SSL setup completed ==="
