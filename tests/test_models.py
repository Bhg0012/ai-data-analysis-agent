"""qwen3.5:9b is the default model, with sensible fallbacks."""

from tally import config
from tally.ollama import DEFAULT_MODEL, RECOMMENDED_MODELS, resolve_model


def test_default_model_is_qwen():
    assert DEFAULT_MODEL == "qwen3.5:9b"
    assert RECOMMENDED_MODELS[0]["name"] == DEFAULT_MODEL


def test_fresh_settings_use_default(tmp_path, monkeypatch):
    monkeypatch.setenv("TALLY_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    assert config.load_settings()["model"] == "qwen3.5:9b"


def test_default_wins_over_other_installed_models():
    assert resolve_model(DEFAULT_MODEL, ["gpt-oss:20b", "qwen3.5:9b"]) == "qwen3.5:9b"


def test_user_choice_is_respected():
    assert resolve_model("gpt-oss:20b", ["gpt-oss:20b", "qwen3.5:9b"]) == "gpt-oss:20b"


def test_falls_back_when_default_not_downloaded():
    assert resolve_model(DEFAULT_MODEL, ["gpt-oss:20b"]) == "gpt-oss:20b"
    assert resolve_model(DEFAULT_MODEL, ["llama3.1:8b", "nomic-embed-text"]) == "llama3.1:8b"
    assert resolve_model(DEFAULT_MODEL, []) is None
