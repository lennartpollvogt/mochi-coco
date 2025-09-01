# What needs to be tested

- type in command `/edit` into chat
- get table of all message with the following columns:
  - message number
  - role (user or assistant)
  - message content (first 250 characters)
- type in message number
  - in case of message number of role `assistant` loop user for a correct input (only message numbers from role `user` are allowed). Ask user to provide a valid message number.
  - in case of message number of role `user`:
    - rerender all messages until the message of the given number
    - ask user for input (with `prompt_toolkit` for multiline input) and present the message content within this input field. The user can edit this message content.
    - user can do now the following:
      - edit the message content and submit the message. This will update the chat session file (based on session id) by replacing the old message objects with the old/new message objects.
      - abort (with `ctrl+c`) the edit process and return to the chat view with the original messages (rerender all messages from the json file of the chat session)
