from schedule_assistant.domain.notes import note_title


def test_explicit_title():
    assert note_title("  会议纪要  ", "abcdefghijklmn") == "会议纪要"


def test_blank_title_uses_first_ten_chars():
    assert note_title("", "abcdefghijklmnop") == "abcdefghij"
    assert note_title(None, "一二三四五六七八九十十一") == "一二三四五六七八九十"


def test_whitespace_stripped_from_content():
    assert note_title("   ", "a b\nc\td") == "abcd"
