# Custom Agent User Guide

## Quick Start

1. Create a `./agents` directory in your project
2. Create a `<agent_name>` directory
3. Create a `<agent_name>.py` file and a `SKILL.md` file in the `<agent_name>` directory
4. Add metadata and the system prompt to the `SKILL.md` file with the following format:
```markdown
---
model: <model_name>
description: <agent_description>
---

<System Prompt>
```
The <model_name> will be used to call the correct model to complete the task. Select the appropriate model based on the task skill of the agent. The description will be used to describe the agent's capabilities for the LLM of your chat session to make better decisions.

example:
```markdown
---
model: qwen3-coder:latest
description: An AI with strong capabilities in math.
---

# Persona

You are an AI with strong skill in math.

# Task

You will be given math problems to solve.
...
```
5. In the `<agent_name>.py` file, provide the necessary tools (python functions) the agent can use to complete the task.

example:
```python
def add_numbers(a: float, b: float) -> str:
    """
    Add two numbers together.

    Args:
        a (float): The first number to add.
        b (float): The second number to add.

    Returns:
        str: The result of adding a and b.
    """
    result = a + b
    return f"{a} + {b} = {result}"

def subtract_numbers(a: float, b: float) -> str:
    """
    Subtract the second number from the first number.

    Args:
        a (float): The number to subtract from.
        b (float): The number to subtract.

    Returns:
        str: The result of subtracting b from a.
    """
    result = a - b
    return f"{a} - {b} = {result}"
```
6. create a `__init__.py` file with your tool functions and export them in `__all__` variable

example:
```python
from .tools import add, subtract
__all__ = ['add', 'subtract']
```
7. Start mochi-coco and a chat session
8. Type in `/agents` and select the agent/s you want to expose to the LLM of your current session.
9. Ask the LLM to use the agent to complete the task. You can also prompt within the system prompt the LLM to outsource specific tasks to dedicated agents.
