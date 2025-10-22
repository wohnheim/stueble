import re

def snake_to_camel_case(snake_case: str):
    """
    turns snake_case into camelCase
    Parameters:
        snake_case (str): the snake_case string
    Returns:
        str: the camelCase string
    """
    camel_case = re.sub(r"_([a-z])", lambda m: m.group(1).upper(), snake_case)
    if "Qr" in camel_case:
        camel_case = camel_case.replace("Qr", "QR")
    return camel_case



def camel_to_snake_case(camel_case: str):
    """
    turns camelCase into snake_case
    Parameters:
        camel_case (str): the camelCase string
    Returns:
        snake_case (str): the snake_case string
    """
    snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_case).lower()
    if "_q_r_" in snake_case:
        snake_case = snake_case.replace("_q_r_", "_qr_")
    return snake_case