"""
Utility tools for mochi-coco.

This module provides simple utility functions that can be used as tools
by LLMs during chat sessions.
"""

import random
from datetime import datetime


def get_current_time() -> str:
    """
    Get the current date and time.

    Returns:
        str: Current date and time in a readable format.
    """
    now = datetime.now()
    return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def generate_random_number(min_value: int = 1, max_value: int = 100) -> str:
    """
    Generate a random number between two values.

    Args:
        min_value (int): The minimum value (inclusive). Defaults to 1.
        max_value (int): The maximum value (inclusive). Defaults to 100.

    Returns:
        str: A random number between min_value and max_value.
    """
    if min_value > max_value:
        return f"Error: Minimum value ({min_value}) cannot be greater than maximum value ({max_value})"

    random_num = random.randint(min_value, max_value)
    return f"Random number between {min_value} and {max_value}: {random_num}"


def flip_coin() -> str:
    """
    Flip a virtual coin.

    Returns:
        str: Either "Heads" or "Tails".
    """
    result = random.choice(["Heads", "Tails"])
    return f"Coin flip result: {result}"


def count_words(text: str) -> str:
    """
    Count the number of words in a text.

    Args:
        text (str): The text to count words in.

    Returns:
        str: The word count and character count.
    """
    if not text.strip():
        return "The text is empty."

    words = text.strip().split()
    word_count = len(words)
    char_count = len(text)
    char_count_no_spaces = len(text.replace(" ", ""))

    return f"Text analysis: {word_count} words, {char_count} characters (including spaces), {char_count_no_spaces} characters (excluding spaces)"


def reverse_text(text: str) -> str:
    """
    Reverse the given text.

    Args:
        text (str): The text to reverse.

    Returns:
        str: The reversed text.
    """
    if not text:
        return "Cannot reverse empty text."

    reversed_text = text[::-1]
    return f"Original: '{text}' → Reversed: '{reversed_text}'"


def roll_dice(sides: int = 6, count: int = 1) -> str:
    """
    Roll one or more dice with specified number of sides.

    Args:
        sides (int): Number of sides on each die. Defaults to 6.
        count (int): Number of dice to roll. Defaults to 1.

    Returns:
        str: The results of rolling the dice.
    """
    if sides < 2:
        return "Error: Dice must have at least 2 sides!"

    if count < 1:
        return "Error: Must roll at least 1 die!"

    if count > 20:
        return "Error: Cannot roll more than 20 dice at once!"

    rolls = [random.randint(1, sides) for _ in range(count)]

    if count == 1:
        return f"Rolled a {sides}-sided die: {rolls[0]}"
    else:
        total = sum(rolls)
        rolls_str = ", ".join(map(str, rolls))
        return f"Rolled {count} {sides}-sided dice: [{rolls_str}] (Total: {total})"
