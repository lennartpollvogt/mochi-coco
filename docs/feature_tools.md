# Tools in Mochi-Coco

## Example tools: Car Assistant

**file: tools/car_information.py**
```python
from typing import Literal

def get_car_info(info: Literal["oil_temperature", "fuel_level", "speed", "total_distance", "trip_distance"]):
    """
    Get information about the car.

    Args:
        info (Literal["oil_temperature", "fuel_level", "speed", "total_distance", "trip_distance"]): The type of information to retrieve.

    Returns:
        str: The requested information about the car.
    """
    if info == "oil_temperature":
        return "Oil temperature is 85°C."
    elif info == "fuel_level":
        return "Fuel level is 75%."
    elif info == "speed":
        return "Speed is 60 km/h."
    elif info == "total_distance":
        return "Total distance is 1000 km."
    elif info == "trip_distance":
        return "Trip distance is 50 km."
    else:
        raise ValueError(f"Invalid info: {info}")
```

**file: tools/weather.py
```python
def get_current_weather(city: str):
    """
    Get weather information for a city.

    Args:
        city (str): The name of the city.

    Returns:
        str: The weather information for the city.
    """
    return f"Weather in {city} is sunny."
```


**file: tools/__init__.py**
The `__init__.py` file is used to expose the tools for the cli application.
```python
from .weather import get_weather
from .car_information import get_car_info

__all__ = ["get_weather", "get_car_info"]

__car_assistant__ = ["get_weather", "get_car_info"]
```

## How the cli gets the tools and general concept

The cli gets the tools by looking for the `__init__.py` file within the `tools` folder in the root folder of the terminal directory. Within the `__init__.py` file it looks for the `__all__` variable and other variables with the `__` prefix and the `__` suffix (e.g. `__<name>__`). All tools in the `__all__` variable get listed as single tools for the `Available Tools` panel. The other variables with the `__` prefix and the `__` suffix are tool groups which are shown as `Tool groups` in the `Available Tools` panel.

The idea behind the 'single tools' within the `__all__` variable is to provide the user the possibility to select one or more tools to make them available for the LLM during a chat session. This is a very flexible approach and the user can customize which tools should be available for the LLM.
But, in some cases the user has a specific goal and wants to use a tool group. A tool group is a collection of tools that are related to a specific topic or domain. For example, a tool group for car information might include tools for getting weather information, getting car information, and getting car maintenance information. By selecting a tool group, the user can quickly enable all tools within the group for the LLM during a chat session. Only one tool group can be selected at a time.

> **Availability of tools**:
> This means, that a LLM gets only the tools presented which are selected by the user.

## LLMs and tools

Not all LLMs are capable of using tools. The capability of a LLM can be checked by using the `ollama` library.

**Checking tool usage capabilities from models:**

```python
import ollama

client = ollama.Client()

model_info = client.show(model='gpt-oss:20b')

print(model_info.capabilities)

>>> ['completion', 'tools', 'thinking']
```
If the model supports tools, within the capabilities array the `tools` value is present in the array.

## Tool consumption, tool selection and user flow

**Application process to collect tools within the `tools` folder:**
1. Start cli app with terminal command `mochi-coco`
2. application starts and looks for `tools` folder within the root folder of the terminal
3. within the `tools` folder it looks for the `__init__.py` file
4. within the `__init__.py` file it looks for the `__all__` variable and other variables with the `__` prefix and the `__` suffix (e.g. `__<name>__`)
5. All tools in the `__all__` variable get listed as single tools. The other variables with the `__` prefix and the `__` suffix are consumed as tool groups.

**How the tools are shown to the user: Available Tools-Panel**
```terminal
╭─ 🛠️ Available Tools  ────────────────────────────────────────────────────────────╮
│  Single tools                                                                    │
│ ╭─────┬───────────────────────────┬──────────────────────────────────────╮       │
│ │ #   │ Tool Name                 │ Tool Description                     │       │
│ ├─────┼───────────────────────────┼──────────────────────────────────────┤       │
│ │ 1   │ get_car_info              │ Get information about a car.         │       │
│ │ 2   │ get_current_weather       │ Get weather information for a city.  │       │
│ ╰─────┴───────────────────────────┴──────────────────────────────────────╯       │
│                                                                                  │
│  Tool groups                                                                     │
│ ╭─────┬───────────────────────────┬──────────────────────────────────────╮       │
│ │ #   │ Tool Group                │ Tool Description                     │       │
│ ├─────┼───────────────────────────┼──────────────────────────────────────┤       │
│ │ a   │ get_car_info              │ Get information about a car.         │       │
│ ╰─────┴───────────────────────────┴──────────────────────────────────────╯       │
│                                                                                  │
│                                                                                  │
│ 💡 Options:                                                                      │
│ • 🔢 Select multiple tools (1-7) by listing them (e.g. 1,3,5,7)                  │
│ OR select a tool group by choosing a single letter (a, b, c, d, e, f, g)         │
│ OR type `none` to choose no tools                                                │
│ • 👋 Type 'q' to quit                                                            │
╰──────────────────────────────────────────────────────────────────────────────────╯
```

**User flow within the cli application to enable tools before starting or loading a chat session:**
1. User is asked to select a chat session - if existing - or create a new one (in case of no existing session, a new session will be created and user starts from 2.).
2. User is asked to select a llm (model) for the chat session.
3. Application checks if the models is capable of using tools.
4. If the model is capable of using tools, the user is asked to select the tools or a tool group to be used. Otherwise, the tool selection is skipped.
```terminal
╭─ 🛠️ Available Tools  ────────────────────────────────────────────────────────────╮
│  Single tools                                                                    │
│ ╭─────┬───────────────────────────┬──────────────────────────────────────╮       │
│ │ #   │ Tool Name                 │ Tool Description                     │       │
│ ├─────┼───────────────────────────┼──────────────────────────────────────┤       │
│ │ 1   │ get_car_info              │ Get information about a car.         │       │
│ │ 2   │ get_current_weather       │ Get weather information for a city.  │       │
│ ╰─────┴───────────────────────────┴──────────────────────────────────────╯       │
│                                                                                  │
│  Tool groups                                                                     │
│ ╭─────┬───────────────────────────┬──────────────────────────────────────╮       │
│ │ #   │ Tool Group                │ Tool Description                     │       │
│ ├─────┼───────────────────────────┼──────────────────────────────────────┤       │
│ │ a   │ get_car_info              │ Get information about a car.         │       │
│ ╰─────┴───────────────────────────┴──────────────────────────────────────╯       │
│                                                                                  │
│                                                                                  │
│ 💡 Options:                                                                      │
│ • 🔢 Select multiple tools (1-7) by listing them (e.g. 1,3,5,7)                  │
│ OR select a tool group by choosing a single letter (e.g. a)                      │
│ OR type `none` to choose no tools                                                │
│ • 👋 Type 'q' to quit                                                            │
╰──────────────────────────────────────────────────────────────────────────────────╯
```
5. User can select a list of single tools (list of numbers) or a tool group (by sinlge letter).


**User flow within the cli application to enable tools within the chat session:**
1. Within a chat session user types in `/menu` and submits
2. Chat menu opens with the possiblity to open the submenu for `tools`.
```terminal
╭────────╮
│ 🧑 You │
╰────────╯
/menu
╭─ ⚙️  Chat Menu ─────────────────────────────────────────────────────────╮
│ ╭─────┬──────────────────────┬───────────────────────────────────╮      │
│ │ #   │ Command              │ Description                       │      │
│ ├─────┼──────────────────────┼───────────────────────────────────┤      │
│ │ 1   │ 💬 Switch Sessions   │ Change to different chat session  │      │
│ │ 2   │ 🤖 Change Model      │ Select a different AI model       │      │
│ │ 3   │ 📝 Toggle Markdown   │ Enable/disable markdown rendering │      │
│ │ 4   │ 🤔 Toggle Thinking   │ Show/hide thinking blocks         │      │
│ │ 5   │ 🔧 Change System     │ Select different system prompt    │      │
│ │ 6   │ 🛠️ Tools             │ Choose tools or a tool group      │      │
│ ╰─────┴──────────────────────┴───────────────────────────────────╯      │
│                                                                         │
│ 💡 Options:                                                             │
│ • Select an option (1-6)                                                │
│ • Type 'q' to cancel                                                    │
╰─────────────────────────────────────────────────────────────────────────╯
```
3. User types in `6` to open the tool menu
4. Application checks if the models is capable of using tools.
5. If the model is capable of using tools, the user is asked to select the tools or a tool group to be used. Otherwise, the user is informed and returns to the chat menu.
```terminal
╭─ 🛠️ Available Tools  ────────────────────────────────────────────────────────────╮
│  Single tools                                                                    │
│ ╭─────┬───────────────────────────┬──────────────────────────────────────╮       │
│ │ #   │ Tool Name                 │ Tool Description                     │       │
│ ├─────┼───────────────────────────┼──────────────────────────────────────┤       │
│ │ 1   │ get_car_info              │ Get information about a car.         │       │
│ │ 2   │ get_current_weather       │ Get weather information for a city.  │       │
│ ╰─────┴───────────────────────────┴──────────────────────────────────────╯       │
│                                                                                  │
│  Tool groups                                                                     │
│ ╭─────┬───────────────────────────┬──────────────────────────────────────╮       │
│ │ #   │ Tool Group                │ Tool Description                     │       │
│ ├─────┼───────────────────────────┼──────────────────────────────────────┤       │
│ │ a   │ get_car_info              │ Get information about a car.         │       │
│ ╰─────┴───────────────────────────┴──────────────────────────────────────╯       │
│                                                                                  │
│                                                                                  │
│ 💡 Options:                                                                      │
│ • 🔢 Select multiple tools (1-7) by listing them (e.g. 1,3,5,7)                  │
│ OR select a tool group by choosing a single letter (a, b, c, d, e, f, g)         │
│ OR type `none` to choose no tools                                                │
│ • 👋 Type 'q' to quit                                                            │
╰──────────────────────────────────────────────────────────────────────────────────╯
```
4. User can select a list of single tools (list of numbers) or a tool group (by letter).

## Tool examples for the mochi-coco cli repository

The mochi-coco repository should have `tool_examples` folder with several example tools.

Possible tools:
- `edit_file`: to enable the LLM to edit files within the directory.
- `cli`: to enable the LLM to interact with the CLI.
- `read_file`: to enable the LLM to read files within the directory.

## Tool's message object in the chat session

When the LLM uses a tool during a chat session, the tools response is saved within the chat session json file. Also the tool's message object is saved within the chat session json file.
```json
{
  "metadata": {
    "session_id": "05dd3d213a",
    "model": "gpt-oss:20b",
    "created_at": "2025-09-10T21:49:12.412127",
    "updated_at": "2025-09-10T21:49:40.460088",
    "message_count": 4,
    "summary": "The user greets and then asks for London’s weather, but the assistant explains it cannot access real‑time data and instead suggests various websites and apps where the user can check the current weather."
  },
  "messages": [
    {
      "role": "user",
      "content": "Hi",
      "message_id": "2abdccc5a4",
      "timestamp": "2025-09-10T21:49:15.532014"
    },
    {
      "role": "assistant",
      "content": "Hello! 👋 How can I help you today?",
      "model": "gpt-oss:20b",
      "message_id": "e55a1825e6",
      "timestamp": "2025-09-10T21:49:16.552930",
      "eval_count": 39,
      "prompt_eval_count": 68
    },
    {
      "role": "user",
      "content": "Get the weather of London",
      "message_id": "82cac9f3df",
      "timestamp": "2025-09-10T21:49:29.064869"
    },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
          {
              "function": {
                  "name": "get_weather",
                  "arguments": {
                      "city": "London"
                  }
              },
          }
      ]
      "model": "gpt-oss:20b",
      "message_id": "fbd17238b6",
      "timestamp": "2025-09-10T21:49:35.257029",
      "eval_count": 201,
      "prompt_eval_count": 94
    },
    {
      "role": "tool",
      "tool_name": "get_weather",
      "content": "Weather in London is sunny.",
      "message_id": "fbd17234de",
      "timestamp": "2025-09-10T21:50:35.257029",
    },
    {
      "role": "assistant",
      "content": "Great! Here's the weather for London: Weather in London is sunny.",
      "message_id": "fbd17233r5",
      "timestamp": "2025-09-10T21:50:35.257029",
      "eval_count": 301,
      "prompt_eval_count": 94
    }
  ]
}
```

## Example from official Ollama-Python repository for tool calling with streaming response

```python
import random
from typing import Iterator

from ollama import ChatResponse, Client


def get_temperature(city: str) -> int:
  """
  Get the temperature for a city in Celsius

  Args:
    city (str): The name of the city

  Returns:
    int: The current temperature in Celsius
  """
  # This is a mock implementation - would need to use a real weather API
  import random

  if city not in ['London', 'Paris', 'New York', 'Tokyo', 'Sydney']:
    return 'Unknown city'

  return str(random.randint(0, 35)) + ' degrees Celsius'


def get_conditions(city: str) -> str:
  """
  Get the weather conditions for a city
  """
  if city not in ['London', 'Paris', 'New York', 'Tokyo', 'Sydney']:
    return 'Unknown city'
  # This is a mock implementation - would need to use a real weather API
  conditions = ['sunny', 'cloudy', 'rainy', 'snowy']
  return random.choice(conditions)


available_functions = {
  'get_temperature': get_temperature,
  'get_conditions': get_conditions,
}


cities = ['London', 'Paris', 'New York', 'Tokyo', 'Sydney']
city = random.choice(cities)
city2 = random.choice(cities)
messages = [{'role': 'user', 'content': f'What is the temperature in {city}? and what are the weather conditions in {city2}?'}]
print('----- Prompt:', messages[0]['content'], '\n')

model = 'qwen3'
client = Client()
response: Iterator[ChatResponse] = client.chat(model, stream=True, messages=messages, tools=[get_temperature, get_conditions], think=True)

for chunk in response:
  if chunk.message.thinking:
    print(chunk.message.thinking, end='', flush=True)
  if chunk.message.content:
    print(chunk.message.content, end='', flush=True)
  if chunk.message.tool_calls:
    for tool in chunk.message.tool_calls:
      if function_to_call := available_functions.get(tool.function.name):
        print('\nCalling function:', tool.function.name, 'with arguments:', tool.function.arguments)
        output = function_to_call(**tool.function.arguments)
        print('> Function output:', output, '\n')

        # Add the assistant message and tool call result to the messages
        messages.append(chunk.message)
        messages.append({'role': 'tool', 'content': str(output), 'tool_name': tool.function.name})
      else:
        print('Function', tool.function.name, 'not found')

print('----- Sending result back to model \n')
if any(msg.get('role') == 'tool' for msg in messages):
  res = client.chat(model, stream=True, tools=[get_temperature, get_conditions], messages=messages, think=True)
  done_thinking = False
  for chunk in res:
    if chunk.message.thinking:
      print(chunk.message.thinking, end='', flush=True)
    if chunk.message.content:
      if not done_thinking:
        print('\n----- Final result:')
        done_thinking = True
      print(chunk.message.content, end='', flush=True)
    if chunk.message.tool_calls:
      # Model should be explaining the tool calls and the results in this output
      print('Model returned tool calls:')
      print(chunk.message.tool_calls)
else:
  print('No tool calls returned')
```
