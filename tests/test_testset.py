from eval.validate_testset import known_section_ids, load_testset, validate


def test_testset_is_valid_against_current_chunks() -> None:
    items = load_testset()
    assert validate(items, known_section_ids()) == []


def test_english_group_size_and_split() -> None:
    english = [i for i in load_testset() if i.group == "english"]
    assert len(english) == 90
    assert sum(i.split == "dev" for i in english) == 27


def test_overall_split_matches_the_plan() -> None:
    items = load_testset()
    assert len(items) == 200
    assert sum(i.split == "dev" for i in items) == 60
