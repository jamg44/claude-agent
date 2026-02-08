# claude agent

## agent setup

```sh
uv init
uv venv
source .venv/bin/activate

# Install dependencies
uv add anthropic python-dotenv
```

## tools structure

Diferencias menores:
OpenAI:

```py
python{
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "...",
        "parameters": { ... }  # <-- "parameters" en lugar de "input_schema"
    }
}
```

Anthropic:

```py
python{
    "name": "calculator",
    "description": "...",
    "input_schema": { ... }  # <-- "input_schema"
}
````

El schema interno (properties, required, etc.) es JSON Schema estándar en ambos.