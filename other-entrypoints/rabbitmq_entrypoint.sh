#!/bin/bash

# This is needed to generate the password for RabbitMQ.
# Since there is no simple way to generate it without adding an installation step before docker compose,
# and since there is no simple way to pass env variables to other services, this script saves the credentials
# to a file mounted on a shared volume, and then uses them to start RabbitMQ.

CREDENTIALS_FILE=${RBBT_CREDENTIALS_FILE}
echo "Saving RabbitMQ credentials to ${RBBT_CREDENTIALS_FILE}"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    RABBITMQ_PASSWORD=$(openssl rand -base64 32)

    cat <<EOF > "$CREDENTIALS_FILE"
{
  "RABBITMQ_USER": "project-user",
  "RABBITMQ_PASSWORD": "$RABBITMQ_PASSWORD"
}
EOF
fi

RABBITMQ_USER=$(awk -F'"' '/RABBITMQ_USER/ {print $4}' "$CREDENTIALS_FILE")
RABBITMQ_PASSWORD=$(awk -F'"' '/RABBITMQ_PASSWORD/ {print $4}' "$CREDENTIALS_FILE")

export RABBITMQ_DEFAULT_USER=$RABBITMQ_USER
export RABBITMQ_DEFAULT_PASS=$RABBITMQ_PASSWORD

rabbitmq-server
