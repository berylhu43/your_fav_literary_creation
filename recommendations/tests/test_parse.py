from recommendations import services as rec


def test_parse_valid():
    assert rec._parse('{"recommendations": [{"title": "Dune"}]}') == [{"title": "Dune"}]


def test_parse_missing_key():
    assert rec._parse('{"other": 1}') == []


def test_parse_malformed_json():
    assert rec._parse('{"recommendations": [') == []


def test_parse_none():
    assert rec._parse(None) == []


def test_parse_garbage():
    assert rec._parse("not json at all") == []


def test_parse_empty_string():
    assert rec._parse("") == []


def test_parse_bare_array_currently_crashes():
    assert rec._parse("[1, 2, 3]") == []
