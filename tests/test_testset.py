from collections import Counter

from eval.validate_testset import known_section_ids, load_testset, validate


def test_testset_is_valid_against_current_chunks() -> None:
    items = load_testset()
    assert validate(items, known_section_ids()) == []


def test_every_group_has_dev_and_test_questions() -> None:
    splits = Counter((i.group, i.split) for i in load_testset())
    for group in ("english", "urdu", "roman_urdu", "out_of_scope"):
        assert splits[(group, "dev")] > 0 and splits[(group, "test")] > 0


def test_fbr_questions_are_test_only_and_cite_their_source() -> None:
    fbr = [i for i in load_testset() if i.source == "fbr"]
    assert fbr and all(i.split == "test" and i.source_url for i in fbr)


def test_translations_share_split_and_gold_with_their_source() -> None:
    items = load_testset()
    by_id = {i.id: i for i in items}
    for i in items:
        if i.source_id:
            src = by_id[i.source_id]
            assert (i.split, i.gold_section_ids) == (src.split, src.gold_section_ids)


def test_translations_share_their_source_answer_and_sections():
    items = {i.id: i for i in load_testset()}
    for item in items.values():
        if item.source_id:
            src = items[item.source_id]
            for key in ("reference_answer", "gold_section_ids", "acceptable_section_ids", "split"):
                assert getattr(item, key) == getattr(src, key), (item.id, key)
