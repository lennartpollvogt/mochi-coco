"""
Tools module for mochi-coco.

This file exports individual tools and defines tool groups for organized access.
Tools can be selected individually or by group during chat sessions.
"""

from .math_tools import (
    add_numbers,
    subtract_numbers,
    multiply_numbers,
    divide_numbers,
    power_calculation,
    square_root,
    calculate_percentage
)

from .utility_tools import (
    get_current_time,
    generate_random_number,
    flip_coin,
    count_words,
    reverse_text,
    roll_dice
)

# Individual tools available for selection
__all__ = [
    # Math tools
    'add_numbers',
    'subtract_numbers',
    'multiply_numbers',
    'divide_numbers',
    'power_calculation',
    'square_root',
    'calculate_percentage',
    # Utility tools
    'get_current_time',
    'generate_random_number',
    'flip_coin',
    'count_words',
    'reverse_text',
    'roll_dice'
]

# Tool groups for organized functionality
__math__ = [
    'add_numbers',
    'subtract_numbers',
    'multiply_numbers',
    'divide_numbers',
    'power_calculation',
    'square_root',
    'calculate_percentage'
]

__utilities__ = [
    'get_current_time',
    'generate_random_number',
    'flip_coin',
    'count_words',
    'reverse_text',
    'roll_dice'
]

__basic_calculator__ = [
    'add_numbers',
    'subtract_numbers',
    'multiply_numbers',
    'divide_numbers'
]

__fun_tools__ = [
    'flip_coin',
    'roll_dice',
    'reverse_text',
    'generate_random_number'
]
