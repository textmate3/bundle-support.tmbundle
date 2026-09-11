# Bundle Support

The shared libraries every other bundle's commands load, in Ruby and in Python. A mandatory bundle, seeded into the application and updated through the catalog.

`Support/shared/lib` is what `TM_SUPPORT_PATH` points at. A mistake in one of those files breaks every command that loads it, in every bundle, which is why the tests here are mostly about whether a library loads at all.

## Tests

From the bundle's directory:

```sh
ruby Support/shared/tests/lib_load_tests.rb
ruby Support/shared/tests/scan_dir_tests.rb
ruby Support/shared/tests/scriptmate_error_fd_tests.rb
"$TM_PYTHON" Support/shared/tests/python_helpers_tests.py
```

`TM_PYTHON` is set by TextMate for anything it runs. Outside the editor, any Python 3 works.
