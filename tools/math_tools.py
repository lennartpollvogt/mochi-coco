"""
Basic mathematical tools for mochi-coco.

This module provides simple arithmetic functions that can be used as tools
by LLMs during chat sessions.
"""



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


def multiply_numbers(a: float, b: float) -> str:
    """
    Multiply two numbers together.

    Args:
        a (float): The first number to multiply.
        b (float): The second number to multiply.

    Returns:
        str: The result of multiplying a and b.
    """
    result = a * b
    return f"{a} × {b} = {result}"


def divide_numbers(a: float, b: float) -> str:
    """
    Divide the first number by the second number.

    Args:
        a (float): The dividend (number to be divided).
        b (float): The divisor (number to divide by).

    Returns:
        str: The result of dividing a by b, or an error message if dividing by zero.
    """
    if b == 0:
        return "Error: Cannot divide by zero!"

    result = a / b
    return f"{a} ÷ {b} = {result}"


def power_calculation(base: float, exponent: float) -> str:
    """
    Calculate base raised to the power of exponent.

    Args:
        base (float): The base number.
        exponent (float): The exponent to raise the base to.

    Returns:
        str: The result of base^exponent.
    """
    result = base ** exponent
    return f"{base}^{exponent} = {result}"


def square_root(number: float) -> str:
    """
    Calculate the square root of a number.

    Args:
        number (float): The number to find the square root of.

    Returns:
        str: The square root of the number, or an error message if the number is negative.
    """
    if number < 0:
        return "Error: Cannot calculate square root of negative number!"

    result = number ** 0.5
    return f"√{number} = {result}"


def calculate_percentage(part: float, whole: float) -> str:
    """
    Calculate what percentage one number is of another.

    Args:
        part (float): The part value.
        whole (float): The whole value.

    Returns:
        str: The percentage with formatting, or an error message if whole is zero.
    """
    if whole == 0:
        return "Error: Cannot calculate percentage when whole is zero!"

    percentage = (part / whole) * 100
    return f"{part} is {percentage:.2f}% of {whole}"
