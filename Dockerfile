FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY pyproject.toml README.md LICENSE /app/
COPY ehr_fhir_genomics_toolkit /app/ehr_fhir_genomics_toolkit
COPY configs /app/configs
COPY config.mock.yaml config.yaml.example config.realdata.template.yaml /app/

RUN python -m pip install --upgrade pip \
    && python -m pip install .

USER appuser

ENTRYPOINT ["ehr-fhir-genomics-toolkit"]
CMD ["--help"]
