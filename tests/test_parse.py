import pytest

from reel.parse import _strip_md, _table_rows, parse_repo


def test_parses_the_sample_repo_end_to_end(sample_repo):
    info = parse_repo(sample_repo)
    assert info.title == "Pathfinder"
    assert info.tagline == "a route planner that explains its detours"
    assert info.intro.startswith("Most route planners give you a line on a map")
    assert "*" not in info.intro and "*" not in info.tagline            # markdown emphasis stripped
    assert len(info.differs) == 3
    assert info.differs[0][0] == "Explains every detour"
    assert "Dijkstra" in info.architecture
    names = [p.name for p, _ in info.screenshots]
    assert names == ["overview.png", "detour.png", "map.png"]
    assert info.screenshots[0][1] == "Route overview with the explained turn-by-turn list"   # alt text, from the README
    assert info.screenshots[2][1] == "Map"                                                     # not referenced in the README; caption from the filename
    assert info.readme_found is True


def test_a_folder_with_no_readme_still_returns_something_usable(tmp_path):
    (tmp_path / "myproject").mkdir()
    info = parse_repo(tmp_path / "myproject")
    assert info.readme_found is False
    assert info.title == "myproject" and info.tagline == "" and info.intro == "" and info.differs == [] and info.screenshots == []


def test_title_tagline_split_on_a_colon(tmp_path):
    (tmp_path / "README.md").write_text("# Foo: a thing that does stuff\n\nSome long enough intro paragraph goes here for real, honestly it does.\n", encoding="utf-8")
    info = parse_repo(tmp_path)
    assert info.title == "Foo" and info.tagline == "a thing that does stuff"


def test_title_without_a_colon_falls_back_to_the_first_paragraph_as_tagline(tmp_path):
    (tmp_path / "README.md").write_text("# Foo\n\nA short line.\n\nA second, much longer paragraph that is definitely long enough to count as the intro text here.\n", encoding="utf-8")
    info = parse_repo(tmp_path)
    assert info.title == "Foo" and info.tagline == "A short line."
    assert info.intro.startswith("A second, much longer paragraph")


def test_badge_lines_and_code_blocks_are_not_mistaken_for_prose(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Foo\n\n[![build](https://x.io/a.svg)](https://x.io)\n\n```\nsome code\n```\n\nThe actual intro paragraph is this one, long enough to be picked up by the parser for sure.\n",
        encoding="utf-8")
    info = parse_repo(tmp_path)
    assert info.intro.startswith("The actual intro paragraph")


def test_differs_table_with_more_than_two_columns_keeps_the_first_two(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Foo\n\nAn intro paragraph that is long enough to be picked up as the problem statement for this test case.\n\n"
        "## What makes it different\n\n| Idea | What it does | Alternative |\n|---|---|---|\n| Speed | Fast | Slow tools |\n| Cost | Cheap | Pricey tools |\n",
        encoding="utf-8")
    info = parse_repo(tmp_path)
    assert info.differs == [("Speed", "Fast", "Slow tools"), ("Cost", "Cheap", "Pricey tools")]


def test_screenshots_folder_is_scanned_even_without_readme_references(tmp_path):
    from PIL import Image
    (tmp_path / "README.md").write_text("# Foo\n\nIntro paragraph long enough to be real content for this little test fixture here.\n", encoding="utf-8")
    shots = tmp_path / "screenshots"
    shots.mkdir()
    Image.new("RGB", (400, 240)).save(shots / "a.png")
    Image.new("RGB", (400, 240)).save(shots / "b.png")
    tiny = Image.new("RGB", (32, 32))
    tiny.save(shots / "tiny-icon.png")
    info = parse_repo(tmp_path)
    names = {p.name for p, _ in info.screenshots}
    assert names == {"a.png", "b.png"}                     # the tiny icon is filtered out by size


def test_max_screenshots_is_respected(tmp_path):
    from PIL import Image
    (tmp_path / "README.md").write_text("# Foo\n\nIntro paragraph long enough to be real content for this little test fixture here.\n", encoding="utf-8")
    shots = tmp_path / "screenshots"
    shots.mkdir()
    for i in range(8):
        Image.new("RGB", (400, 240)).save(shots / f"s{i}.png")
    assert len(parse_repo(tmp_path, max_screenshots=3).screenshots) == 3


def test_parse_repo_rejects_a_file(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError, match="not a folder"):
        parse_repo(f)


def test_strip_md_handles_bold_italic_code_and_links():
    assert _strip_md("**bold** and *italic* and `code` and [a link](http://x)") == "bold and italic and code and a link"
    assert _strip_md("a single * with no partner") == "a single * with no partner"     # no closing star: left alone


def test_table_rows_skips_the_separator_and_header_rows():
    lines = ["| Idea | What it does |", "|---|---|", "| A | does a |", "| B | does b |"]
    assert _table_rows(lines) == [("A", "does a"), ("B", "does b")]
