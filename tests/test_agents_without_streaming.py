"""Integration tests - these DO use tokens, run sparingly"""
import pytest
from main_without_streaming import run_agent
from io import StringIO
import sys


@pytest.mark.integration_no_streaming
def test_calculator_integration_no_streaming(capsys):
    """Test full agent with calculator"""
    run_agent("¿Cuánto es 10 + 5?")
    captured = capsys.readouterr()
    assert "15" in captured.out


@pytest.mark.integration_no_streaming
def test_weather_integration_no_streaming(capsys):
    """Test full agent with weather"""
    run_agent("¿Qué tiempo hace en Madrid?")
    captured = capsys.readouterr()
    assert "Madrid" in captured.out