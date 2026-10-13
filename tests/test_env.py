import os
from pathlib import Path

from lecad.env import load_env_file


def test_load_env_file_does_not_override_existing(tmp_path: Path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("A=from_file\nB='two words'\n", encoding="utf-8")
    monkeypatch.setenv("A", "existing")
    monkeypatch.delenv("B", raising=False)
    load_env_file(env)
    assert os.environ["A"] == "existing"
    assert os.environ["B"] == "two words"
