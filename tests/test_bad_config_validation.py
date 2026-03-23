import pytest
from pathlib import Path
import yaml

from ehr_fhir_genomics_toolkit.config import load_config

def test_bad_config_missing_tiledb_expr_uri(tmp_path: Path):
    bad = {
        "sql": {"sqlalchemy_url": "sqlite:///data/mock_ehr.sqlite"},
        "tiledb": {"expression_uri": ""},  # invalid
        "provenance": {"log_dir": "run_logs"},
    }
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(Exception):
        load_config(str(p))

def test_bad_config_sql_url_blank(tmp_path: Path):
    bad = {
        "sql": {"sqlalchemy_url": ""},  # treated as absent
        "tiledb": {"expression_uri": "/tmp/expr"},
    }
    p = tmp_path / "bad2.yaml"
    p.write_text(yaml.safe_dump(bad), encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg.sql is None
