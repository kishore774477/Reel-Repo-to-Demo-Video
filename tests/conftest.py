import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["REEL_DATA"] = tempfile.mkdtemp(prefix="reel-test-")      # never write into the project's data folder

from reel.sample import generate       # noqa: E402


@pytest.fixture(scope="session")
def sample_repo(tmp_path_factory):
    d = tmp_path_factory.mktemp("sample") / "pathfinder"
    generate(d)
    return d
