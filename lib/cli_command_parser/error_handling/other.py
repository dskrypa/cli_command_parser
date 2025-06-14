"""
Error handling for expected / unexpected exceptions on non-Windows systems.
"""

from __future__ import annotations

__all__ = ['handle_kb_interrupt']


def handle_kb_interrupt(exc: KeyboardInterrupt) -> int:
    """
    Handles :class:`python:KeyboardInterrupt` by calling :func:`python:print` to avoid ending the program in a way that
    causes the next terminal prompt to be printed on the same line as the last (possibly incomplete) line of output.
    """
    try:
        print(flush=True)  # Flush forces any potential closed/broken pipe-related error to be caught/handled here
    except BrokenPipeError:
        pass
    # 130 (= 128 + SIGINT (2)) is used/expected by Bash; see: https://tldp.org/LDP/abs/html/exitcodes.html
    return 130
