"""Tool registry - auto-discovers and registers all tools"""
import importlib
import pkgutil
from pathlib import Path

# Auto-discover all modules in the tools package
tool_modules = []
package_dir = Path(__file__).parent

for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
    # Skip __init__ and any private modules
    if not module_name.startswith('_'):
        module = importlib.import_module(f'.{module_name}', package=__name__)
        tool_modules.append(module)

# Auto-build tool definitions list
TOOL_DEFINITIONS = [
    module.TOOL_DEFINITION
    for module in tool_modules
    if hasattr(module, 'TOOL_DEFINITION')
]

# Auto-build tool executors registry
TOOL_EXECUTORS = {}
for module in tool_modules:
    if hasattr(module, 'TOOL_DEFINITION') and hasattr(module, 'execute'):
        tool_name = module.TOOL_DEFINITION['name']
        TOOL_EXECUTORS[tool_name] = module.execute