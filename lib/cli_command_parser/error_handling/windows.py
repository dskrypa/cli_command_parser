"""
Error handling for expected / unexpected exceptions on Windows systems.
"""

from __future__ import annotations

import ctypes
import sys

from .base import extended_error_handler

__all__ = ['handle_kb_interrupt']

RtlGetLastNtStatus = ctypes.WinDLL('ntdll').RtlGetLastNtStatus
RtlGetLastNtStatus.restype = ctypes.c_ulong
NT_STATUSES = {0xC000_00B1: 'STATUS_PIPE_CLOSING', 0xC000_014B: 'STATUS_PIPE_BROKEN'}


def handle_kb_interrupt(exc: KeyboardInterrupt) -> int:
    """
    Handles :class:`python:KeyboardInterrupt` by calling :func:`python:print` to avoid ending the program in a way that
    causes the next terminal prompt to be printed on the same line as the last (possibly incomplete) line of output.
    """
    try:
        print(flush=True)  # Flush forces any potential closed/broken pipe-related error to be caught/handled here
    except BrokenPipeError:
        pass
    except OSError as e:
        # Handle the closed/broken pipe incorrect errno bug if triggered during the above print
        if not handle_win_os_pipe_error(e):
            raise
    return 130


@extended_error_handler(OSError)
def handle_win_os_pipe_error(exc: OSError):
    """
    This is a workaround for `[Windows] I/O on a broken pipe may raise an EINVAL OSError instead of BrokenPipeError
    <https://github.com/python/cpython/issues/79935>`_, which is a bug in the way that the
    Windows error code for a broken pipe is translated into an errno value.  It should be translated to
    :data:`~errno.EPIPE`, but it uses :data:`~errno.EINVAL` (22) instead.

    Prevents the following when piping output to utilities such as ``| head``::

        Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
        OSError: [Errno 22] Invalid argument
    """
    if exc.errno == 22 and RtlGetLastNtStatus() in NT_STATUSES:
        try:
            sys.stdout.close()
        except OSError:
            pass
        return True

    return False
