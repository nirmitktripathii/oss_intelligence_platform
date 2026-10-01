from textkit import slugify


def test_plain_words():
    assert slugify("Hello World") == "hello-world"


def test_punctuation_is_dropped():
    assert slugify("Hello, World!") == "hello-world"


def test_repeated_separators_collapse():
    assert slugify("  a -- b  ") == "a-b"
