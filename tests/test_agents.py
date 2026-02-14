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


@pytest.mark.integration
def test_cross_conversation_memory_same_user(capsys):
    """Test memory can be reused across different conversations for same user"""
    user_id = "integration-user-shared-memory"
    system_prompt = (
        "Responde en español. "
        "Si te preguntan por un dato personal previo del usuario, "
        "contesta de forma directa y breve."
    )

    # Conversation A: store a stable fact
    run_agent(
        "Recuerda que mi lenguaje favorito para scripts es Python.",
        user_id=user_id,
        system_prompt=system_prompt
    )
    capsys.readouterr()

    # Conversation B: ask for that fact (new conversation_id on purpose)
    run_agent(
        "¿Recuerdas cuál es mi lenguaje favorito para scripts?",
        user_id=user_id,
        system_prompt=system_prompt
    )

    captured = capsys.readouterr()
    assert "python" in captured.out.lower()


@pytest.mark.integration
def test_cross_conversation_memory_isolated_between_users(capsys):
    """Test user memories do not leak between different user_ids"""
    user_a = "integration-user-a"
    user_b = "integration-user-b"
    system_prompt = (
        "Responde en español. "
        "Si no sabes un dato del usuario, responde exactamente: NO_RECUERDO"
    )

    # Save memory for user A
    run_agent(
        "Recuerda que vivo en Sevilla.",
        user_id=user_a,
        system_prompt=system_prompt
    )
    capsys.readouterr()

    # Ask as user B (should not receive user A memory)
    run_agent(
        "¿Recuerdas en qué ciudad vivo?",
        user_id=user_b,
        system_prompt=system_prompt
    )

    captured = capsys.readouterr()
    output = captured.out.lower()
    assert "sevilla" not in output
    assert "no_recuerdo" in output