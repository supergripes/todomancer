from pathlib import Path

from todomancer.scanner import scan_directory


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_finds_line_comment_markers(tmp_path):
    write(
        tmp_path / "main.py",
        "def foo():\n"
        "    # TODO: refactor this\n"
        "    x = 10 // 3\n"
        "    return x\n",
    )

    items = scan_directory(tmp_path)

    assert len(items) == 1
    assert items[0].marker == "TODO"
    assert items[0].text == "refactor this"
    assert items[0].line == 2
    assert items[0].file == Path("main.py")


def test_does_not_false_positive_on_floor_division(tmp_path):
    write(tmp_path / "main.py", "x = 10 // 3  # not a marker\n")

    items = scan_directory(tmp_path)

    assert items == []


def test_finds_hash_style_marker(tmp_path):
    write(tmp_path / "script.sh", "# FIXME: broken on macOS\necho hi\n")

    items = scan_directory(tmp_path)

    assert len(items) == 1
    assert items[0].marker == "FIXME"


def test_finds_multiline_block_comment_marker(tmp_path):
    write(
        tmp_path / "app.js",
        "function f() {}\n"
        "/*\n"
        " * TODO: clean up this whole module\n"
        " * it's a mess\n"
        " */\n"
        "function g() {}\n",
    )

    items = scan_directory(tmp_path)

    assert len(items) == 1
    assert items[0].marker == "TODO"
    assert items[0].text == "clean up this whole module"
    assert items[0].line == 3


def test_finds_single_line_block_comment_marker(tmp_path):
    write(tmp_path / "app.js", "/* HACK: quick patch */\nfunction f() {}\n")

    items = scan_directory(tmp_path)

    assert len(items) == 1
    assert items[0].marker == "HACK"
    assert items[0].text == "quick patch"


def test_marker_is_case_insensitive_and_normalized(tmp_path):
    write(tmp_path / "main.py", "# todo: lowercase marker\n")

    items = scan_directory(tmp_path)

    assert items[0].marker == "TODO"


def test_context_includes_surrounding_lines_within_radius(tmp_path):
    # CONTEXT_RADIUS is 2, so with the marker on line 4 of 7, line1 and
    # line7 fall outside the +/-2 window and should not appear.
    write(
        tmp_path / "main.py",
        "line1\nline2\nline3\n# TODO: marker\nline5\nline6\nline7\n",
    )

    items = scan_directory(tmp_path)

    assert "line1" not in items[0].context
    assert "line2" in items[0].context
    assert "line3" in items[0].context
    assert "# TODO: marker" in items[0].context
    assert "line5" in items[0].context
    assert "line6" in items[0].context
    assert "line7" not in items[0].context


def test_ignores_files_outside_extension_whitelist(tmp_path):
    write(tmp_path / "data.bin", "# TODO: should not be scanned\n")

    items = scan_directory(tmp_path)

    assert items == []


def test_always_ignores_git_directory(tmp_path):
    write(tmp_path / ".git" / "config", "# TODO: inside git internals\n")
    write(tmp_path / "main.py", "# TODO: real one\n")

    items = scan_directory(tmp_path)

    assert len(items) == 1
    assert items[0].file == Path("main.py")


def test_respects_gitignore_directory_pattern(tmp_path):
    write(tmp_path / ".gitignore", "vendor/\n")
    write(tmp_path / "vendor" / "lib.py", "# TODO: should be ignored\n")
    write(tmp_path / "main.py", "# TODO: should be scanned\n")

    items = scan_directory(tmp_path)

    assert len(items) == 1
    assert items[0].file == Path("main.py")


def test_respects_gitignore_wildcard_pattern(tmp_path):
    write(tmp_path / ".gitignore", "generated_*.py\n")
    write(tmp_path / "generated_models.py", "# TODO: ignored via wildcard\n")
    write(tmp_path / "main.py", "# TODO: kept\n")

    items = scan_directory(tmp_path)

    assert len(items) == 1
    assert items[0].file == Path("main.py")


def test_respects_gitignore_negation(tmp_path):
    write(tmp_path / ".gitignore", "generated_*.py\n!generated_keep.py\n")
    write(tmp_path / "generated_drop.py", "# TODO: dropped\n")
    write(tmp_path / "generated_keep.py", "# TODO: kept\n")

    items = scan_directory(tmp_path)

    assert len(items) == 1
    assert items[0].file == Path("generated_keep.py")


def test_scans_multiple_files_and_returns_relative_paths(tmp_path):
    write(tmp_path / "a.py", "# TODO: a\n")
    write(tmp_path / "sub" / "b.py", "# FIXME: b\n")

    items = scan_directory(tmp_path)

    files = {str(item.file) for item in items}
    assert files == {"a.py", str(Path("sub") / "b.py")}
