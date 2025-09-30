# Feature Plans

- [x] stream the response normal and then render markdown only after the final chunk
- [x] Render user input in markdown, after user presses enter
- [x] add model name to each message object
- [x] add id to each message object (`message_id`)
- [x] customize the markdown rendering (headers)
- [x] within chat session open session menu to choose chats with `/chats`
- [x] add eval_count and prompt_eval_count to assistant message
- [x] when enable or disable markdown rendering during chat, the chat history should be cleared and re-rendered
- [x] multiline input for user
- [x] delete command for chat session menu
- [x] when user wants to creat new chat and quits models seleciton, they should return to the chat sessions menu
- [x] change approach of commands during chat session to have one command (`/menu`) which opens a menu where the user can select from the available options.
  - Available options:
    - `chats`: Open chat session menu and select a chat session to continue with
    - `models`: Choose LLM to continue with for the chat session
    - `markdown`: Toggle markdown rendering during chat
    - `thinking`: Toggle thinking rendering during chat
  - This feature does not affect `/edit` command.
- [x] workflow: during session, within breaks a LLM is requested to create a chat session summary. This could be used for the @chat workflow, so an LLM would be better in finding other chat sessions for the user request.
- [x] break llm response with "ESC" and store partial response in chat history
- [x] Give user possibility to change a specific user prompt and continue from this message again (see `manual_testing/edit_message.md`) while old messages will be deleted from the chat history
- [x] only list ollama models with `completion` functionality (see `OllamaClient().show(model).capabilities`)
- [x] add info to model overview if a model can use tools
- [x] add system prompt
- [x] Add tool usage
- [x] add folder with example tools users of the application can use to get started and to showcase the capabilities of the application + add documentation on how to create own tools
- [ ] autocomplete for commands during chat sessions

# Issues

- [ ] stream stops after a while and the complete output get displayed when LLM has finished (but should continuously stream)

# Open Questions

- how could adding an image to the user input be done?

# Feature Drafts

## Workflows with enhanced chat session structure

The LLM can choose workflows. Workflows in a chat session are performed with a sub-chat session. The sub-chat session message history is stored in the same chat session json file but uses a sub object `workflows` which contains for each workflow an array of message objects.
The reference to a message object from the origin chat history is given by the `message_id` field.

**Example of json structure**
```json
{
  "metadata": {
    "session_id": "ac6c58660e",
    "model": "gpt-oss:20b",
    "created_at": "2025-08-26T08:19:16.554406",
    "updated_at": "2025-08-26T08:20:13.907823",
    "message_count": 2,
  },
  "messages": [
    {
      "role": "user",
      "content": "Write the recipe of Menemen in Markdown",
      "timestamp": "2025-08-26T08:19:48.403307"
    },
    {
      "role": "assistant",
      "content": "# Menemen – Turkish Scrambled Egg Dish\n\n> **Menemen** (pronounced *meh-NEH-men*) is a classic Turkish breakfast staple made from eggs, tomatoes, green peppers, and spices. It’s simple, flavorful, and can be made in minutes. Enjoy it with crusty bread, fresh herbs, or a side of grilled sausage.\n\n---\n\n## Ingredients\n\n| Quantity | Item |\n|----------|------|\n| 2 Tbsp | Olive oil (or butter for a richer flavor) |\n| 1 medium onion, finely chopped (optional) |\n| 1 green bell pepper, diced |\n| 1 red bell pepper, diced |\n| 3–4 medium ripe tomatoes, diced (or 1 cup canned crushed tomatoes) |\n| 1 tsp paprika (sweet or smoked) |\n| 1/2 tsp ground cumin (optional) |\n| Salt & pepper to taste |\n| 4–6 eggs (adjust to desired consistency) |\n| 1 tbsp chopped fresh parsley or dill |\n| 1 tsp fresh lemon juice (optional) |\n| Crushed red pepper flakes (optional, for heat) |\n\n**Serving**  \n- Fresh crusty bread (baguette, Turkish pide, or a hearty rye)  \n- Grated feta or a dollop of Greek yogurt (optional)  \n\n---\n\n## Instructions\n\n1. **Sauté the base**  \n   - Heat the olive oil in a wide skillet over medium‑high heat.  \n   - Add the onion (if using) and sauté until translucent, about 2 min.  \n   - Toss in the diced bell peppers and cook until they soften, ~3 min.\n\n2. **Add tomatoes & seasonings**  \n   - Stir in the diced tomatoes, paprika, cumin, salt, and pepper.  \n   - Cook until the tomatoes break down and release their juices, ~5–7 min.  \n   - If you prefer a smoother texture, mash the tomatoes gently with a wooden spoon.\n\n3. **Incorporate the eggs**  \n   - Reduce the heat to medium.  \n   - Crack the eggs directly into the skillet (you can crack them into a bowl first if you’d rather avoid yolk separation).  \n   - Let them sit for a few seconds, then gently stir with a spatula, folding the mixture to form soft curds.  \n   - Continue cooking, stirring occasionally, until the eggs reach your preferred consistency—runny or slightly firmer.  \n   - Add a splash of lemon juice for brightness if desired.\n\n4. **Finish and garnish**  \n   - Sprinkle chopped parsley (or dill) over the top.  \n   - If you like a little heat, add a pinch of crushed red pepper flakes.  \n   - Taste and adjust salt/paprika as needed.\n\n5. **Serve immediately**  \n   - Plate the menemen hot.  \n   - Serve with slices of warm bread, a sprinkle of feta, or a side of spicy sausage for a heartier meal.\n\n---\n\n## Tips & Variations\n\n| Tip | Explanation |\n|-----|-------------|\n| **Use fresh tomatoes** | If in season, fresh tomatoes give a bright, sweet flavor. In winter, canned crushed tomatoes work well. |\n| **Add sausage** | Cook sliced Turkish sausage (sucuk) in the skillet first, then add the veggies. |\n| **Try different peppers** | Red, yellow, or green peppers yield varied colors and flavors. |\n| **Make it vegan** | Substitute eggs with chickpea flour batter or tofu scramble for a plant‑based version. |\n| **Spice it up** | Use cayenne or harissa for a fiery kick. |\n| **Serve on a plate** | Menemen is traditionally eaten from a shallow plate or skillet; keep it that way for authenticity! |\n\n---\n\n## Nutritional Snapshot (approx. per serving, 2 eggs)\n\n- Calories: 260 kcal  \n- Protein: 18 g  \n- Fat: 18 g  \n- Carbohydrates: 12 g  \n- Fiber: 3 g\n\n*(Values vary with ingredient choices and portion size.)*\n\nEnjoy this quick, comforting dish that captures the heart of Turkish home cooking!",
      "timestamp": "2025-08-26T08:20:13.907812"
    }
  ],
  "workflows": [
    {
      "metadata": {
        "session_id": "ac6c58660i",
        "message_object": "ac6c58661f",
        "model": "gpt-oss:20b",
        "created_at": "2025-08-26T08:20:16.554406",
        "updated_at": "2025-08-26T08:21:13.907823",
        "message_count": 2
      },
      "messages": [
        {
          "role": "user",
          "content": "Write the recipe of Menemen in Markdown",
          "timestamp": "2025-08-26T08:19:48.403307"
        },
        {
          "role": "assistant",
          "content": "# Menemen – Turkish Scrambled Egg Dish\n\n> **Menemen** (pronounced *meh-NEH-men*) is a classic Turkish breakfast staple made from eggs, tomatoes, green peppers, and spices. It’s simple, flavorful, and can be made in minutes. Enjoy it with crusty bread, fresh herbs, or a side of grilled sausage.\n\n---\n\n## Ingredients\n\n| Quantity | Item |\n|----------|------|\n| 2 Tbsp | Olive oil (or butter for a richer flavor) |\n| 1 medium onion, finely chopped (optional) |\n| 1 green bell pepper, diced |\n| 1 red bell pepper, diced |\n| 3–4 medium ripe tomatoes, diced (or 1 cup canned crushed tomatoes) |\n| 1 tsp paprika (sweet or smoked) |\n| 1/2 tsp ground cumin (optional) |\n| Salt & pepper to taste |\n| 4–6 eggs (adjust to desired consistency) |\n| 1 tbsp chopped fresh parsley or dill |\n| 1 tsp fresh lemon juice (optional) |\n| Crushed red pepper flakes (optional, for heat) |\n\n**Serving**  \n- Fresh crusty bread (baguette, Turkish pide, or a hearty rye)  \n- Grated feta or a dollop of Greek yogurt (optional)  \n\n---\n\n## Instructions\n\n1. **Sauté the base**  \n   - Heat the olive oil in a wide skillet over medium‑high heat.  \n   - Add the onion (if using) and sauté until translucent, about 2 min.  \n   - Toss in the diced bell peppers and cook until they soften, ~3 min.\n\n2. **Add tomatoes & seasonings**  \n   - Stir in the diced tomatoes, paprika, cumin, salt, and pepper.  \n   - Cook until the tomatoes break down and release their juices, ~5–7 min.  \n   - If you prefer a smoother texture, mash the tomatoes gently with a wooden spoon.\n\n3. **Incorporate the eggs**  \n   - Reduce the heat to medium.  \n   - Crack the eggs directly into the skillet (you can crack them into a bowl first if you’d rather avoid yolk separation).  \n   - Let them sit for a few seconds, then gently stir with a spatula, folding the mixture to form soft curds.  \n   - Continue cooking, stirring occasionally, until the eggs reach your preferred consistency—runny or slightly firmer.  \n   - Add a splash of lemon juice for brightness if desired.\n\n4. **Finish and garnish**  \n   - Sprinkle chopped parsley (or dill) over the top.  \n   - If you like a little heat, add a pinch of crushed red pepper flakes.  \n   - Taste and adjust salt/paprika as needed.\n\n5. **Serve immediately**  \n   - Plate the menemen hot.  \n   - Serve with slices of warm bread, a sprinkle of feta, or a side of spicy sausage for a heartier meal.\n\n---\n\n## Tips & Variations\n\n| Tip | Explanation |\n|-----|-------------|\n| **Use fresh tomatoes** | If in season, fresh tomatoes give a bright, sweet flavor. In winter, canned crushed tomatoes work well. |\n| **Add sausage** | Cook sliced Turkish sausage (sucuk) in the skillet first, then add the veggies. |\n| **Try different peppers** | Red, yellow, or green peppers yield varied colors and flavors. |\n| **Make it vegan** | Substitute eggs with chickpea flour batter or tofu scramble for a plant‑based version. |\n| **Spice it up** | Use cayenne or harissa for a fiery kick. |\n| **Serve on a plate** | Menemen is traditionally eaten from a shallow plate or skillet; keep it that way for authenticity! |\n\n---\n\n## Nutritional Snapshot (approx. per serving, 2 eggs)\n\n- Calories: 260 kcal  \n- Protein: 18 g  \n- Fat: 18 g  \n- Carbohydrates: 12 g  \n- Fiber: 3 g\n\n*(Values vary with ingredient choices and portion size.)*\n\nEnjoy this quick, comforting dish that captures the heart of Turkish home cooking!",
          "timestamp": "2025-08-26T08:20:13.907812"
        }
      ]
    }
  ]
}
```
