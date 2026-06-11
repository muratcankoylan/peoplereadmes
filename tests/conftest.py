import json
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A minimal copy of the repo (schemas + manifest) for init tests."""
    shutil.copytree(REPO_ROOT / "schemas", tmp_path / "schemas")
    manifest = json.loads((REPO_ROOT / "manifest.json").read_text())
    (tmp_path / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (tmp_path / "personas").mkdir()
    return tmp_path
