"""Python bindings for tm_dialog, TextMate's dialog tool."""

import os
import subprocess
import sys

support_lib = os.path.join(os.environ["TM_SUPPORT_PATH"], "lib")
if support_lib not in sys.path:
    sys.path.insert(0, support_lib)

from tm_helpers import from_plist, to_plist

DIALOG = os.environ["DIALOG"]
NIB_PATH = os.path.join(os.environ["TM_SUPPORT_PATH"], "nibs")


def item(value):
    """One entry in a menu, as tm_dialog wants it. None is a separator."""
    if value is None:
        return {"separator": 1}
    if isinstance(value, tuple):
        return {"title": value[0]}
    return {"title": value}


def run_dialog(arguments, request):
    """Send `request` to tm_dialog as a property list and read its answer."""
    process = subprocess.run(
        [DIALOG, *arguments],
        input=to_plist(request),
        capture_output=True,
        check=False,
    )
    return from_plist(process.stdout) if process.stdout else {}


def menu(options):
    """Show an inline menu and return what was picked.

    A list of strings returns the selected string. A list of (title, value)
    tuples displays the title and returns the value, which is why they are
    tuples rather than a dictionary: the order is the point. An entry of
    None draws a separator.
    """
    if not options:
        return None

    keyed = all(isinstance(option, (tuple, type(None))) for option in options)
    request = {"menuItems": [item(option) for option in options]}
    result = run_dialog(["-u"], request)

    if "selectedIndex" not in result:
        return None

    index = int(result["selectedIndex"])
    return options[index][1] if keyed else options[index]


def get_string(**options):
    """Ask for a string and return it, or None when the dialog was canceled.

    title  - the string in the title bar
    prompt - the label beside the text field
    string - what the field starts out holding
    """
    options.setdefault("title", "Enter String")
    options.setdefault("prompt", "String:")
    options.setdefault("string", "")

    result = run_dialog(["-cm", os.path.join(NIB_PATH, "RequestString")], options)
    if "result" not in result:
        return None
    return result["result"].get("returnArgument")
