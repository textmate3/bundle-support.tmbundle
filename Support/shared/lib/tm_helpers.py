"""Helpers for writing TextMate commands in Python.

Property lists go through the standard library's plistlib. This module used
to ship its own copy of plistlib, from before Python had one, and aliased the
two functions that were removed from Python in 3.9.
"""

import os
import plistlib
import re
import shlex
import shutil
import subprocess
import sys


def to_plist(value):
    """Serialize `value` as an XML property list, as bytes.

    Bytes rather than a string, because that is what tm_dialog reads on its
    standard input and what plistlib produces.
    """
    return plistlib.dumps(value)


def from_plist(data):
    """Read an XML property list from bytes or a string."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return plistlib.loads(data)


def current_word(pattern, direction="both"):
    """Return the word around the caret, from the environment.

    pattern   - a regular expression matching word characters, such as r"[A-Za-z_]*".
    direction - one of "both", "left", "right".
    """
    if os.environ.get("TM_SELECTED_TEXT"):
        return os.environ["TM_SELECTED_TEXT"]

    if not os.environ.get("TM_CURRENT_WORD"):
        return ""

    line = os.environ["TM_CURRENT_LINE"]
    index = int(os.environ["TM_LINE_INDEX"])
    before, after = line[:index], line[index:]
    word_characters = re.compile(pattern)

    word = ""
    if direction in ("left", "both"):
        match = word_characters.match(before[::-1])
        if match:
            word = match.group(0)[::-1]
    if direction in ("right", "both"):
        match = word_characters.match(after)
        if match:
            word += match.group(0)
    return word


def interpreter_from_shebang(first_line):
    """Return the interpreter a shebang names, or "" when it names nothing usable.

    `#!/usr/bin/env python` names env, not a Python, so the word after env is
    what matters and it has to be found on PATH. Since macOS has no `python`
    at all, that spelling normally resolves to nothing, which is exactly the
    case this has to answer "" for rather than returning /usr/bin/env.
    """
    match = re.match(r"^#!\s*(\S+)(.*)$", first_line)
    if not match:
        return ""

    interpreter, arguments = match.group(1), match.group(2).split()
    if os.path.basename(interpreter) == "env":
        # `env -S "$SOMETHING"` is how one bundle names its own wrapper.
        arguments = [word for word in arguments if word != "-S"]
        if not arguments:
            return ""
        interpreter = os.path.expandvars(arguments[0].strip('"\''))

    found = interpreter if os.path.sep in interpreter else shutil.which(interpreter)
    return found if found and os.access(found, os.X_OK) else ""


def env_python():
    """Return the Python to run, and its version as a tuple of integers.

    TM_PYTHON is what the application sets to the Python it resolved, so it
    is the answer whenever it is there. A shebang on the current file wins
    over it, since a person who wrote one meant it.

    The version used to come back as a two digit integer built by reading the
    first and third characters of the version string, which answered 31 for
    Python 3.14. A tuple says what it means and keeps ordering.
    """
    interpreter = interpreter_from_shebang(os.environ.get("TM_FIRST_LINE", ""))
    if not interpreter:
        interpreter = os.environ.get("TM_PYTHON") or sys.executable

    reported = sh([interpreter, "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"])
    version = tuple(int(part) for part in reported.strip().split(".") if part.isdigit())
    return interpreter, version


def sh(command):
    """Run `command` and return its standard output as a string.

    A string goes through the shell, which is what callers that source a
    script and then call a function in it need. A list does not, which is
    what everything else should use.
    """
    result = subprocess.run(
        command,
        shell=isinstance(command, str),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def sh_escape(value):
    """Quote `value` for use in a shell command."""
    return shlex.quote(value)
