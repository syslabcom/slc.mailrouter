import unittest

from slc.mailrouter.storage import FriendlyNameStorage


class TestStorage(unittest.TestCase):
    def test_storage(self):
        storage = FriendlyNameStorage()
        storage.add("abcdefghijkl0123456789", "test name")
        self.assertEqual(
            len(storage), 1,
        )
        self.assertEqual(
            storage[0], ("test name", "abcdefghijkl0123456789"),
        )
        self.assertEqual(
            storage.get("test name"), "abcdefghijkl0123456789",
        )
        self.assertEqual(
            storage.lookup("abcdefghijkl0123456789"), "test name",
        )
        self.assertIsNone(storage.get("who?"),)
        storage.remove("abcdefghijkl0123456789")
        self.assertRaises(
            IndexError, storage.__getitem__, 0,
        )
        self.assertIsNone(storage.get("test name"),)
