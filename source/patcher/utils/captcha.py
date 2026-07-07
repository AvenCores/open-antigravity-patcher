import random

from patcher.utils.console import warn, color, COLOR_CYAN


def generate_math_captcha():
    """Generate a unique math CAPTCHA (addition of two two-digit numbers).

    Returns:
        tuple[str, str]: (human readable question, expected answer string).
    """
    a = random.randint(10, 99)
    b = random.randint(10, 99)
    question = f"{a} + {b} = ?"
    answer = str(a + b)
    return question, answer


def confirm_with_captcha(message):
    """Show a warning and require the user to solve a math CAPTCHA.

    Args:
        message: Context/prompt shown to the user (e.g. the action they
            are about to confirm).

    Returns:
        bool: True if the user solved the CAPTCHA, False if they cancelled
        (empty input or KeyboardInterrupt).
    """
    # Local import avoids a circular dependency: captcha.py is used by
    # patcher modules, while cli.py imports those same modules.
    from patcher.cli import _read_console_line

    warn("Warning: this file appears to be already patched.")
    warn("Re-patching is most likely unnecessary and may cause issues.")
    warn("If you are sure, solve the CAPTCHA below to proceed.")

    while True:
        question, expected = generate_math_captcha()
        print(f"  [?] {message}")
        prompt = f"        {question} ({color('answer', COLOR_CYAN)}): "

        try:
            raw = _read_console_line(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return False

        if not raw:
            return False

        if raw == expected:
            return True

        warn("Incorrect answer. Try again with a new CAPTCHA.")
