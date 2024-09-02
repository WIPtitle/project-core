#!/bin/bash

# This is needed to generate the password for Postgres.
# Since there is no simple way to generate it without adding an installation step before docker compose,
# and since there is no simple way to pass env variables to other services, this script saves the credentials
# to a file mounted on a shared volume, and then export them as envs for Postgres.

CREDENTIALS_FILE=${PG_CREDENTIALS_FILE}
echo "Saving Postgres credentials to ${PG_CREDENTIALS_FILE}"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    POSTGRES_PASSWORD=$(openssl rand -base64 32)

    cat <<EOF > "$CREDENTIALS_FILE"
{
  "POSTGRES_USER": "project-user",
  "POSTGRES_PASSWORD": "$POSTGRES_PASSWORD",
  "POSTGRES_DB": "project-database"
}
EOF
fi

POSTGRES_USER=$(awk -F'"' '/POSTGRES_USER/ {print $4}' "$CREDENTIALS_FILE")
POSTGRES_PASSWORD=$(awk -F'"' '/POSTGRES_PASSWORD/ {print $4}' "$CREDENTIALS_FILE")
POSTGRES_DB=$(awk -F'"' '/POSTGRES_DB/ {print $4}' "$CREDENTIALS_FILE")

export POSTGRES_USER
export POSTGRES_PASSWORD
export POSTGRES_DB

exec docker-entrypoint.sh postgres
