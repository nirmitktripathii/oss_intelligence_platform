# slugify keeps punctuation and does not collapse separators

`slugify("Hello, World!")` returns `"hello,-world!"` but should return `"hello-world"`.
`slugify("  a -- b  ")` returns `"a----b"` but should return `"a-b"`.

Expected: only letters and digits survive, and any run of other characters becomes a single hyphen,
with no leading or trailing hyphen.

Two of the three tests in `tests/test_slug.py` fail.
