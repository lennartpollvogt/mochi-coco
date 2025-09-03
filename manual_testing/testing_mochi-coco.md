# Starting Mochi-Coco with Chat Sessions

This file contains the documentation of the manual test cases for the mochi-coco application.

## Starting Mochi-Coco

### Basic Flow

**Basic User Flow**
1. User types command `mochi-coco` into the terminal and submits with enter.
2. Application `mochi-coco` starts.
3. Application is loading chat session from folder `chat_sessions` within the root directory of the current working directory of the terminal.
4. Application shows the available chat sessions within a table with the columns `#`, `Session ID`, `Model`, `Preview`, `Messages`.
5. User is prompted for an input with the following options:
```terminal
Options:
• Select session (1-n)
• Type 'new' for new chat
• Type '/delete <number>' to delete a session
• Type 'q' to quit
```

### Chat Session Menu

**Selecting an existing chat session with available models**
> Requirements:
> - Basic User Flow
1. User types a number to select a session.
2. The application requests the Ollama server for the models which was previously used in the chat session (see column `Model`) and loads it.
5. User gets prompted to if they want to have markdown rendering enabled (`y`/`n`).
6. In case the user selects markdown rendering, the user gets prompted if they want to have the rendering of thinking blocks enabled (`y`/`n`).
7. Chat session starts.

**Creating a new chat session with available models**
> Requirements:
> - Basic User Flow
1. User types `new` and submits with enter.
2. Application requests the Ollama server for available models and shows them in a table with the following columns: `#`, `Model Name`, `Size (MB)`, `Family`, `Max. Ctx Length`.
3. User is prompted to select a model from a list of available models via number (`#`) or quit the selection process via `q`/`quit`.
4. User types in a number to select a model.
5. User gets prompted to if they want to have markdown rendering enabled (`y`/`n`).
6. In case the user selects markdown rendering, the user gets prompted if they want to have the rendering of thinking blocks enabled (`y`/`n`).
7. Chat session starts.

**Deleting a chat session**
> Requirements:
> - Basic User Flow
1. User types '/delete <number>' and submits with enter.
2. Application deletes the chat session with the specified number.
3. Application shows the remaining chat sessions in the terminal.
4. User is prompted again for an input with the following options:
```terminal
Options:
• Select session (1-n)
• Type 'new' for new chat
• Type '/delete <number>' to delete a session
• Type 'q' to quit
```

### Basic Flow Edge Cases

**Basic User Flow without existing chat sessions**
1. User types command `mochi-coco` into the terminal and submits with enter.
2. Application `mochi-coco` starts.
3. Application tries to load available chat sessions but can't find any.
4. Application skips chat session selection and prompts user for selecting a model (start of any test case with model selection).

**Quit chat session selection**
> Requirements:
> - Basic User Flow
1. User types 'q' and submits with enter.
2. Application quits the chat session selection.
3. Application shuts down.

**Creating a new chat session without available models**
> Requirements:
> - Basic User Flow
1. User types `new` and submits with enter.
2. The application requests the Ollama server for available models.
3. No models are available and user is informed that no models are available and they need to download a model first.

**Selecting an existing chat session without available models**
> Requirements:
> - Basic User Flow
1. User types a number to select a session.
2. The application requests the Ollama server for available models.
3. No models are available and user is informed that no models are available and they need to download a model first.**

## Chat Session Options

### Switching Models

**Switching model during chat session**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
1. User types in the chat `/models` and submits
2. Application requests the Ollama server for available models and shows them in a table with the following columns: `#`, `Model Name`, `Size (MB)`, `Family`, `Max. Ctx Length`.
3. User is prompted to select a model from a list of available models via number (`#`) or quit the selection process via `q`/`quit`.
4. User types in a number to select a model.
5. Chat session continues with new selected model.

**Quitting switching model during chat session**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
1. User types in the chat `/models` and submits
2. Application requests the Ollama server for available models and shows them in a table with the following columns: `#`, `Model Name`, `Size (MB)`, `Family`, `Max. Ctx Length`.
3. User is prompted to select a model from a list of available models via number (`#`) or quit the selection process via `q`/`quit`.
4. User types in `q` or `quit` and submits.
5. Chat session continues with old selected model.

**Try to switch model during chat session but with invalid input**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
1. User types in the chat `/models` and submits
2. Application requests the Ollama server for available models and shows them in a table with the following columns: `#`, `Model Name`, `Size (MB)`, `Family`, `Max. Ctx Length`.
3. User is prompted to select a model from a list of available models via number (`#`) or quit the selection process via `q`/`quit`.
4. User types in an invalid input and submits.
5. User gets prompted to type in a valid model number.

### Switching Chat

**Open chat session selection menu during chat session**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
1. User types in the chat `/chats` and submits
2. Application shows the available chat sessions within a table with the columns `#`, `Session ID`, `Model`, `Preview`, `Messages`.
3. User is prompted for an input with the following options:
```terminal
Options:
• Select session (1-n)
• Type 'new' for new chat
• Type '/delete <number>' to delete a session
• Type 'q' to quit
```

**Switching chat session during chat session**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
> - Open chat session selection menu during chat session
1. User types in a valid session number and submits
2. The application prompts the user if they want to have the loaded chat session rendered in markdown format. In case of `yes`, the user will also be prompted if they want to have thinking blocks rendered (only when rendering markdown is submitted with `yes`).
3. After user submits (whether `yes` or `no`) the application will load the selected chat session and renders it accordingly.
4. The user is prompted for a chat input for the loaded chat session.

**Quit switching chat session during chat session**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
> - Open chat session selection menu during chat session
1. User types in `q` or `quit`
2. The application will return to the previous chat session and prompts the user for a chat input.

**Invalid chat number while switching chat session during chat session**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
> - Open chat session selection menu during chat session
1. User types in an invalid session number and submits
2. The application prompts the user to type in a valid session number (loop)

### Toggle Markdown

**Toggle markdown rendering during chat session**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
1. The user types in `/markdown` during a chat session and submits
2. The application rerenders the chat session messages into markdown or plain text, based on the current mode (markdown or plain) while submitting the command.
3. The user is prompted to input a chat message

### Toggle Thinking Block

**Toggle thinking block rendering during chat session**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models --> *only possible when markdown mode is enabled*
1. User types `/thinking` and submits with enter.
2. The application rerenders the chat session messages into markdown and also the thinking blocks or not, based on the current state of thinking block rendering.
3. The user is prompted to input a chat message

### Edit User Prompt

**User opens edit menu during chat session**
> Requirements:
> - Basic User Flow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
1. User types `/edit` and submits with enter.
2. The application displays a table with of all chat messages in the chronical order with the following columns:
  - `#`
  - `Role`
  - `Preview` (first 250 characters)
  Only messages with the role `user` have a number (`#`).

**User submits and editted or unchanged user prompt**
> Requirements:
> - Basic User Fow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
> - User opens edit menu during chat session
1. User selects a message to edit by typing the number and submits with enter.
2. The chat session gets rerendered until the user prompt to edit. The application prompts to user to insert a new input, while the old user message is the content of the input field.
3. When the user submits or edits the message and then submits, all chat messages after the edited message are deleted from the chat session file and a new request to the Ollama server is made with the new chat history.

**Edit user prompt during chat session and cancel editting**
> Requirements:
> - Basic User Fow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
> - User opens edit menu during chat session
1. User

**User types in a not valid value in the edit menu**
> Requirements:
> - Basic User Fow
> - Selecting an existing chat session with available models OR Creating a new chat session with available models
> - User opens edit menu during chat session
1. User types in a not valid value in the edit menu (e.g. wrong number or any invalid input).
2. The application displays an message indicating that the input is invalid.
3. The application prompts the user to insert a correct input or cancel the edit with `quit` or `q`.
