import io
import tempfile
import unittest
from unittest.mock import patch

from fastapi import UploadFile

from chatbot.repositories.files import list_files, safe_path, save_upload, workspace


class FileTest(unittest.IsolatedAsyncioTestCase):
    async def test_uploads_are_scoped_and_listed(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "chatbot.repositories.files.settings.tool_workspace", directory
        ):
            root = workspace("user", "conversation")
            result = await save_upload(
                root,
                UploadFile(filename="notes.txt", file=io.BytesIO(b"hello")),
            )

            self.assertEqual(result["name"], "uploaded/notes.txt")
            self.assertEqual(result["size"], 5)
            self.assertEqual(result["source"], "uploaded")
            self.assertEqual(list_files(root), [result])
            self.assertEqual(
                safe_path(root, "uploaded/notes.txt").read_text(), "hello"
            )

    async def test_upload_rejects_unsafe_and_duplicate_names(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "chatbot.repositories.files.settings.tool_workspace", directory
        ):
            root = workspace("user", "conversation")
            await save_upload(
                root,
                UploadFile(filename="notes.txt", file=io.BytesIO(b"first")),
            )
            with self.assertRaises(FileExistsError):
                await save_upload(
                    root,
                    UploadFile(filename="notes.txt", file=io.BytesIO(b"second")),
                )
            with self.assertRaises(ValueError):
                await save_upload(
                    root,
                    UploadFile(filename="../secret.txt", file=io.BytesIO(b"bad")),
                )
            self.assertEqual(
                safe_path(root, "uploaded/notes.txt").read_text(), "first"
            )


if __name__ == "__main__":
    unittest.main()
