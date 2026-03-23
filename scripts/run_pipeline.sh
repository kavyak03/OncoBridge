#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${ENV_NAME:-ehr_genomics_env}"

if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  echo "Creating conda env: $ENV_NAME"
  conda env create -f environment.yml
fi

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

python -m ehr_fhir_genomics_toolkit.cli "$@"
