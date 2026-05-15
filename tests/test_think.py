from src.think import strip_think


def test_paired_block_removed():
    assert strip_think("<think>reasoning</think>answer") == "answer"


def test_multiple_blocks_removed():
    assert strip_think("<think>a</think>X<think>b</think>Y") == "XY"


def test_dangling_close_no_open():
    assert strip_think("chain of thought</think>the answer") == "the answer"


def test_dangling_close_uses_last():
    assert strip_think("r1</think>mid</think>final") == "final"


def test_unclosed_open_drops_to_end():
    assert strip_think("<think>still thinking and never closed") == ""


def test_paired_then_unclosed():
    assert strip_think("<think>a</think>Body<think>c") == "Body"


def test_no_tags_passthrough():
    assert strip_think("just a normal reply") == "just a normal reply"


def test_whitespace_trimmed():
    assert strip_think("<think>x</think>\n\n  Hello  ") == "Hello"


def test_case_insensitive():
    assert strip_think("<THINK>r</Think>done") == "done"


def test_whitespace_inside_tag():
    assert strip_think("< think >r</ think >done") == "done"


def test_empty_string():
    assert strip_think("") == ""
