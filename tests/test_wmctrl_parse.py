"""Tests for wmctrl parsing."""

from workset.backends.wmctrl_parse import parse_wmctrl_line, parse_wmctrl_output, split_wm_class_field


def test_split_doubled_reverse_dns():
    assert split_wm_class_field("dev.warp.Warp.dev.warp.Warp") == (
        "dev.warp.Warp",
        "dev.warp.Warp",
    )


def test_split_simple():
    assert split_wm_class_field("Cursor.Cursor") == ("Cursor", "Cursor")
    assert split_wm_class_field("navigator.firefox") == ("navigator", "firefox")


def test_parse_wmctrl_with_pid_no_host():
    line = "0x01000005  0 612197 dev.warp.Warp.dev.warp.Warp  Manjaro Gnome Web App Fix"
    row = parse_wmctrl_line(line)
    assert row is not None
    assert row["wm_class"] == "dev.warp.Warp"
    assert row["title"] == "Manjaro Gnome Web App Fix"
    assert row["pid"] == 612197


def test_parse_wmctrl_without_pid():
    line = "0x04600005  0 Cursor.Cursor     main.py - project"
    row = parse_wmctrl_line(line)
    assert row is not None
    assert row["wm_class"] == "Cursor"
    assert "main.py" in row["title"]


def test_parse_output_multi():
    text = (
        "0x01  0 1 Foo.Foo  One\n"
        "0x02  1 Bar.Bar  Two\n"
    )
    rows = parse_wmctrl_output(text)
    assert len(rows) == 2
    assert rows[0]["wm_class"] == "Foo"
