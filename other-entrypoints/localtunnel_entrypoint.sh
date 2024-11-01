#!/bin/bash

npm install -g localtunnel@2.0.2

CREDENTIALS_FILE=${LT_CREDENTIALS_FILE}

echo "Searching Localtunnel credentials in ${LT_CREDENTIALS_FILE}"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "No credentials found, generating new credentials..."
    UUID=$(openssl rand -hex 16)
    cat <<EOF > "$CREDENTIALS_FILE"
{
  "UUID": "$UUID"
}
EOF
fi

UUID=$(awk -F'"' '/UUID/ {print $4}' "$CREDENTIALS_FILE")

SUBDOMAIN_FRONTEND="alarm-frontend-${UUID}"
SUBDOMAIN_BACKEND="alarm-backend-${UUID}"
SUBDOMAIN_NTFY="alarm-ntfy-${UUID}"

echo "Generated UUID: $UUID"
echo "Subdomains: Frontend - $SUBDOMAIN_FRONTEND, Backend - $SUBDOMAIN_BACKEND, Ntfy - $SUBDOMAIN_NTFY"

lt --subdomain ${SUBDOMAIN_FRONTEND} --port 80 --print-requests > frontend.log 2>&1 &
lt --subdomain ${SUBDOMAIN_BACKEND} --port 8000 --print-requests > backend.log 2>&1 &
lt --subdomain ${SUBDOMAIN_NTFY} --port 8080 --print-requests > ntfy.log 2>&1 &

get_url() {
  local LOG_FILE=$1
  while :; do
    URL=$(grep -o 'https://[^ ]*' "$LOG_FILE" | head -1)
    if [ -n "$URL" ];
      then echo $URL
      break
    fi
    sleep 1
    done
}

URL_FRONTEND=$(get_url frontend.log)
URL_BACKEND=$(get_url backend.log)
URL_NTFY=$(get_url ntfy.log)

echo "Tunnel URLs:"
echo "Frontend: $URL_FRONTEND"
echo "Backend: $URL_BACKEND"
echo "Ntfy: $URL_NTFY"

# Because I used an UUID it's basically impossible, but it can happen that an url is already in use: if so, localtunnel
# returns a random url. Saving the returned url in a credentials file is safer than assuming that the required url
# has been given.
cat <<EOF > "$CREDENTIALS_FILE"
{
  "UUID": "$UUID",
  "URL_FRONTEND": "$URL_FRONTEND",
  "URL_BACKEND": "$URL_BACKEND",
  "URL_NTFY": "$URL_NTFY"
}
EOF

tail -f /dev/null
