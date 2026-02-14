"""Tests with streaming functionality"""
import pytest
from main import run_agent


@pytest.mark.integration
def test_simple_response(capsys):
    """Test streaming with simple response (no tools)"""
    run_agent("Say hello in Spanish")

    captured = capsys.readouterr()
    assert len(captured.out) > 0
    assert "hola" in captured.out.lower() or "spanish" in captured.out.lower()


@pytest.mark.integration
def test_with_calculator(capsys):
    """Test streaming with tool use (calculator)"""
    run_agent("What is 25 + 17?")

    captured = capsys.readouterr()
    assert "calculator" in captured.out
    assert "42" in captured.out


@pytest.mark.integration
def test_with_system_prompt(capsys):
    """Test streaming with custom system prompt"""
    concise_prompt = "You are a concise assistant. Give one-word answers when possible."

    run_agent("What is 10 + 5?", system_prompt=concise_prompt)

    captured = capsys.readouterr()
    assert "calculator" in captured.out
    assert "15" in captured.out


@pytest.mark.integration
def test_multi_tool(capsys):
    """Test streaming with multiple tool calls"""
    run_agent("What's the weather in Madrid? Then add 5 to the temperature.")

    captured = capsys.readouterr()
    assert "get_weather" in captured.out
    assert "calculator" in captured.out
    assert "Madrid" in captured.out