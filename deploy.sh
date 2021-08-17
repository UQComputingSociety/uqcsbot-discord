#!/bin/bash

mkdir docker-cert
echo "${DOCKER_CA}" > docker-cert/ca.pem
echo "${DOCKER_KEY}" > docker-cert/key.pem
echo "${DOCKER_CERT}" > docker-cert/cert.pem

export DOCKER_CERT_PATH="$(pwd)/docker-cert"
export DOCKER_TLS_VERIFY=1

docker pull ghcr.io/uqcomputingsociety/uqcsbot-discord:latest
OLDCONTAINERS="$(docker ps -f label=uqcsbot-discord-ci -q)"
docker run -d \
  --name uqcsbot-discord \
  --label uqcsbot-discord-ci \
  ghcr.io/uqcomputingsociety/uqcsbot-discord:latest
for x in $OLDCONTAINERS; do
  docker rm -f ${x}
done