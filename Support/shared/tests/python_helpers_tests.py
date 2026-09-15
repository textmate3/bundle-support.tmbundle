"""Tests for the shared Python helpers.

The same bet the Ruby lib_load_tests makes: a module that does not import
breaks every bundle command that uses it, and catching that here is much
cheaper than finding it in an error window. Three of these four modules
imported names that Python removed, so nothing that used them could run.

Run from the bundle's directory:

    "$TM_PYTHON" Support/shared/tests/python_helpers_tests.py
"""

import os
import shutil
import subprocess
import sys
import unittest

SUPPORT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_PATH = os.path.join(SUPPORT_PATH, "lib")

os.environ.setdefault("TM_SUPPORT_PATH", SUPPORT_PATH)
os.environ.setdefault("DIALOG", "/nonexistent/tm_dialog")
sys.path.insert(0, LIB_PATH)

import dialog
import tm_helpers
import webpreview


class ImportsCleanly(unittest.TestCase):
    """Every shared module has to import on the Python the application pins."""

    MODULES = ["tm_helpers", "dialog", "webpreview"]

    def test_each_module_imports_in_a_fresh_interpreter(self):
        for name in self.MODULES:
            with self.subTest(module=name):
                result = subprocess.run(
                    [sys.executable, "-c", "import %s" % name],
                    capture_output=True,
                    text=True,
                    env={**os.environ, "PYTHONPATH": LIB_PATH},
                )
                self.assertEqual(result.returncode, 0, result.stderr)


class PropertyLists(unittest.TestCase):
    def test_a_dictionary_round_trips(self):
        original = {"menuItems": [{"title": "One"}, {"separator": 1}], "count": 2}
        self.assertEqual(tm_helpers.from_plist(tm_helpers.to_plist(original)), original)

    def test_to_plist_answers_bytes_since_that_is_what_tm_dialog_reads(self):
        self.assertIsInstance(tm_helpers.to_plist({"a": 1}), bytes)

    def test_from_plist_takes_a_string_as_well_as_bytes(self):
        plist = tm_helpers.to_plist({"a": 1})
        self.assertEqual(tm_helpers.from_plist(plist.decode("utf-8")), {"a": 1})


class CurrentWord(unittest.TestCase):
    def setUp(self):
        for name in ("TM_SELECTED_TEXT", "TM_CURRENT_WORD", "TM_CURRENT_LINE", "TM_LINE_INDEX"):
            os.environ.pop(name, None)

    def test_a_selection_wins_over_everything(self):
        os.environ["TM_SELECTED_TEXT"] = "chosen"
        os.environ["TM_CURRENT_WORD"] = "ignored"
        self.assertEqual(tm_helpers.current_word(r"[A-Za-z_]*"), "chosen")

    def test_both_directions_reach_around_the_caret(self):
        os.environ["TM_CURRENT_WORD"] = "sentence"
        os.environ["TM_CURRENT_LINE"] = "a sentence here"
        os.environ["TM_LINE_INDEX"] = "6"
        self.assertEqual(tm_helpers.current_word(r"[A-Za-z_]*"), "sentence")

    def test_left_stops_at_the_caret(self):
        os.environ["TM_CURRENT_WORD"] = "sentence"
        os.environ["TM_CURRENT_LINE"] = "a sentence here"
        os.environ["TM_LINE_INDEX"] = "6"
        self.assertEqual(tm_helpers.current_word(r"[A-Za-z_]*", "left"), "sent")

    def test_right_starts_at_the_caret(self):
        os.environ["TM_CURRENT_WORD"] = "sentence"
        os.environ["TM_CURRENT_LINE"] = "a sentence here"
        os.environ["TM_LINE_INDEX"] = "6"
        self.assertEqual(tm_helpers.current_word(r"[A-Za-z_]*", "right"), "ence")

    def test_no_word_and_no_selection_is_empty(self):
        self.assertEqual(tm_helpers.current_word(r"[A-Za-z_]*"), "")


class Shell(unittest.TestCase):
    def test_a_list_runs_without_a_shell(self):
        self.assertEqual(tm_helpers.sh([sys.executable, "-c", "print('hi')"]), "hi\n")

    def test_a_string_goes_through_the_shell(self):
        self.assertEqual(tm_helpers.sh("echo hi"), "hi\n")

    def test_escaping_survives_a_round_trip_through_the_shell(self):
        awkward = "a b'c\"d$e;f"
        self.assertEqual(tm_helpers.sh("printf %%s %s" % tm_helpers.sh_escape(awkward)), awkward)


class EnvPython(unittest.TestCase):
    def setUp(self):
        self.saved = {name: os.environ.get(name) for name in ("TM_PYTHON", "TM_FIRST_LINE")}
        for name in self.saved:
            os.environ.pop(name, None)

    def tearDown(self):
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_tm_python_is_what_the_application_resolved_so_it_is_the_answer(self):
        os.environ["TM_PYTHON"] = sys.executable
        interpreter, _ = tm_helpers.env_python()
        self.assertEqual(interpreter, sys.executable)

    def test_a_shebang_on_the_file_wins_over_tm_python(self):
        os.environ["TM_PYTHON"] = "/nonexistent/python"
        os.environ["TM_FIRST_LINE"] = "#!%s" % sys.executable
        interpreter, _ = tm_helpers.env_python()
        self.assertEqual(interpreter, sys.executable)

    def test_a_shebang_naming_nothing_is_ignored_rather_than_returned(self):
        os.environ["TM_PYTHON"] = sys.executable
        os.environ["TM_FIRST_LINE"] = "#!/usr/bin/env python"
        interpreter, _ = tm_helpers.env_python()
        self.assertEqual(interpreter, sys.executable)

    def test_the_version_is_a_tuple_of_integers_that_orders_correctly(self):
        os.environ["TM_PYTHON"] = sys.executable
        _, version = tm_helpers.env_python()
        self.assertEqual(version, sys.version_info[:3])
        # The old two digit integer answered 31 for Python 3.14, which sorts
        # below Python 3.9. This is the case that motivated the change.
        self.assertGreater((3, 14, 0), (3, 9, 6))


class Shebang(unittest.TestCase):
    def test_an_absolute_interpreter_that_exists_is_returned(self):
        self.assertEqual(tm_helpers.interpreter_from_shebang("#!%s" % sys.executable), sys.executable)

    def test_an_absolute_interpreter_that_does_not_exist_is_not(self):
        self.assertEqual(tm_helpers.interpreter_from_shebang("#!/nonexistent/python"), "")

    def test_env_is_not_the_interpreter_the_word_after_it_is(self):
        self.assertEqual(tm_helpers.interpreter_from_shebang("#!/usr/bin/env sh"), shutil.which("sh"))

    def test_env_naming_something_not_on_path_answers_nothing(self):
        self.assertEqual(tm_helpers.interpreter_from_shebang("#!/usr/bin/env nosuchthing"), "")

    def test_env_dash_s_names_the_interpreter_after_the_flag(self):
        line = '#!/usr/bin/env -S "%s"' % sys.executable
        self.assertEqual(tm_helpers.interpreter_from_shebang(line), sys.executable)

    def test_a_line_that_is_not_a_shebang_answers_nothing(self):
        self.assertEqual(tm_helpers.interpreter_from_shebang("import sys"), "")


class Menu(unittest.TestCase):
    def test_a_plain_string_becomes_a_title(self):
        self.assertEqual(dialog.item("One"), {"title": "One"})

    def test_a_tuple_shows_its_first_element(self):
        self.assertEqual(dialog.item(("Shown", "returned")), {"title": "Shown"})

    def test_none_is_a_separator(self):
        self.assertEqual(dialog.item(None), {"separator": 1})

    def test_an_empty_menu_answers_nothing_without_running_the_dialog(self):
        self.assertIsNone(dialog.menu([]))


class WebPreview(unittest.TestCase):
    def test_the_script_path_is_quoted_once(self):
        self.assertNotIn('"', webpreview.WEBPREVIEW)
        self.assertTrue(webpreview.WEBPREVIEW.endswith("webpreview.sh") or webpreview.WEBPREVIEW.endswith("webpreview.sh'"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
