import unittest

from src.models import WwiseObject
from src.validation import get_shared_parent_id, validate_unique_object_ids


def make_object(object_id: str, parent_id: str | None) -> WwiseObject:
    return WwiseObject(
        id=object_id,
        name=object_id,
        type="Sound",
        path=f"\\{object_id}",
        parent_id=parent_id,
        parent_name="Root",
    )


class ValidationTests(unittest.TestCase):
    def test_shared_parent_is_required(self) -> None:
        objects = [make_object("one", "parent"), make_object("two", "parent")]
        self.assertEqual(get_shared_parent_id("group", objects), "parent")

    def test_multiple_parents_are_rejected(self) -> None:
        objects = [make_object("one", "a"), make_object("two", "b")]
        with self.assertRaisesRegex(ValueError, "multiple parents"):
            get_shared_parent_id("group", objects)

    def test_missing_parent_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "without a valid parent"):
            get_shared_parent_id("group", [make_object("one", None)])

    def test_duplicate_guid_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_unique_object_ids(
                "group",
                [make_object("same", "parent"), make_object("same", "parent")],
            )


if __name__ == "__main__":
    unittest.main()
