#!/usr/bin/env bash
set -euo pipefail

ACR_NAME="${ACR_NAME:?Set ACR_NAME}"
IMAGE_NAME="${IMAGE_NAME:-ehr-fhir-genomics}"
TAG="${TAG:-v1}"

docker build -t "${IMAGE_NAME}:${TAG}" .
az acr login --name "${ACR_NAME}"
docker tag "${IMAGE_NAME}:${TAG}" "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${TAG}"
docker push "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${TAG}"
echo "Done: ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${TAG}"
