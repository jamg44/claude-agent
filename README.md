# Claude Agent - ReAct Pattern Implementation

> Learning project: Building AI agents from scratch without frameworks

## What is this?

A Python implementation of the ReAct (Reasoning + Acting) pattern for AI agents using Claude API. Built to understand agent fundamentals before using frameworks like LangChain.

## Features

- ✅ ReAct loop with tool calling
- ✅ Modular tool system (auto-discovery)
- ✅ Unit tests (no token usage)
- ✅ Integration tests (optional)
- ✅ Loop protection (max iterations)
- ✅ Persistent conversation memory (SQLite)
- ✅ Cross-conversation memory snippets (dynamic retrieval, bounded context)
- ✅ User-scoped memory isolation (multi-user ready)

## Quick Start
```bash
# Setup
uv venv
source .venv/bin/activate
uv sync

# Configure
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Run
python main.py

# Test (no tokens)
pytest test_tools.py -v

# Integration tests (uses tokens)
pytest -m integration -v
```

## Adding a New Tool

Create `tools/your_tool.py`:
```python
"""Your tool description"""

TOOL_DEFINITION = {
    "name": "your_tool",
    "description": "What it does",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "..."}
        },
        "required": ["param"]
    }
}

def execute(tool_input: dict) -> str:
    """Execute the tool"""
    return "result"
```

That's it! Auto-discovered on next run.

## Tool Schema Format

### Anthropic (Claude):
```python
{
    "name": "calculator",
    "input_schema": { ... }  # JSON Schema
}
```

### OpenAI:
```python
{
    "type": "function",
    "function": {
        "name": "calculator",
        "parameters": { ... }  # JSON Schema
    }
}
```

*Note: Internal schema (properties, required) is standard JSON Schema for both.*

## Learning Goals

- Understand ReAct pattern internals
- Build agents without framework magic
- Create production-ready code

## Next Steps

- [X] System prompts
- [X] Streaming responses
- [X] Persistent memory

## License

MIT