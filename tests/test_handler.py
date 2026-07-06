"""Unit tests for handler module."""

from src.handler import process


class TestProcess:
    def test_returns_ok_status(self):
        result = process({"key": "value"})
        assert result["status"] == "ok"

    def test_echoes_input(self):
        event = {"action": "ingest", "source": "oracle"}
        result = process(event)
        assert result["input"] == event

    def test_handles_empty_event(self):
        result = process({})
        assert result["status"] == "ok"
        assert result["input"] == {}
