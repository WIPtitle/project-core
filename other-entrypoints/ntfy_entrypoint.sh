#!/bin/ash

apk add openssl
apk add curl

check_and_create_credentials() {
  CREDENTIALS_FILE=${NTFY_CREDENTIALS_FILE}

  echo "Searching Ntfy credentials in ${NTFY_CREDENTIALS_FILE}"

  if [ ! -f "$CREDENTIALS_FILE" ]; then
      # if credential file does not exist, delete other files since it is a fresh installation
      [ -f /var/lib/ntfy/cache.db ] && rm /var/lib/ntfy/cache.db
      [ -f /var/lib/ntfy/auth.db ] && rm /var/lib/ntfy/auth.db

      echo "No credentials found, generating new credentials..."
      NTFY_WRITER_PASSWORD=$(openssl rand -base64 32)
      NTFY_READER_PASSWORD=$(openssl rand -base64 32)
      cat <<EOF > "$CREDENTIALS_FILE"
{
  "NTFY_TOPIC": "alarm-ntfy-topic",
  "NTFY_WRITER_USER": "alarm-ntfy-writer-user",
  "NTFY_WRITER_PASSWORD": "$NTFY_WRITER_PASSWORD",
  "NTFY_READER_USER": "alarm-ntfy-reader-user",
  "NTFY_READER_PASSWORD": "$NTFY_READER_PASSWORD"
}
EOF
  fi

  NTFY_TOPIC=$(awk -F'"' '/NTFY_TOPIC/ {print $4}' "$CREDENTIALS_FILE")
  NTFY_WRITER_USER=$(awk -F'"' '/NTFY_WRITER_USER/ {print $4}' "$CREDENTIALS_FILE")
  NTFY_WRITER_PASSWORD=$(awk -F'"' '/NTFY_WRITER_PASSWORD/ {print $4}' "$CREDENTIALS_FILE")
  NTFY_READER_USER=$(awk -F'"' '/NTFY_READER_USER/ {print $4}' "$CREDENTIALS_FILE")
  NTFY_READER_PASSWORD=$(awk -F'"' '/NTFY_READER_PASSWORD/ {print $4}' "$CREDENTIALS_FILE")

  # No base URL needed — ntfy deduces it from the Host header via the reverse proxy
  export NTFY_CACHE_FILE=/var/lib/ntfy/cache.db
  export NTFY_CACHE_DURATION=336h
  export NTFY_AUTH_FILE=/var/lib/ntfy/auth.db
  export NTFY_AUTH_DEFAULT_ACCESS=deny-all
  export NTFY_BEHIND_PROXY=true
  export NTFY_ATTACHMENT_CACHE_DIR=/var/lib/ntfy/attachments
  export NTFY_ATTACHMENT_EXPIRY_DURATION=336h
  export NTFY_ENABLE_LOGIN=true
  export NTFY_POLL_INTERVAL=30
  export NTFY_CORS_ALLOW_ORIGIN="*"

  export NTFY_ENABLE_WEB=true

  [ ! -f "$NTFY_CACHE_FILE" ] && touch "$NTFY_CACHE_FILE"
  [ ! -f "$NTFY_AUTH_FILE" ] && touch "$NTFY_AUTH_FILE"

  ntfy serve &
  NTFY_PID=$!

  NTFY_PASSWORD="$NTFY_WRITER_PASSWORD" ntfy user add "$NTFY_WRITER_USER"
  NTFY_PASSWORD="$NTFY_READER_PASSWORD" ntfy user add "$NTFY_READER_USER"

  ntfy access "$NTFY_WRITER_USER" "$NTFY_TOPIC" write-only
  ntfy access "$NTFY_READER_USER" "$NTFY_TOPIC" read-only
}

check_and_create_credentials

while true; do
  CREDENTIALS_FILE=${NTFY_CREDENTIALS_FILE}
  if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Credentials file deleted, stopping ntfy server..."
    if [ ! -z "$NTFY_PID" ]; then
      kill $NTFY_PID
    fi
    echo "Restarting..."
    check_and_create_credentials
  fi
  sleep 1
done
