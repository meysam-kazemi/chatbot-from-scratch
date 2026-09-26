import unittest
import uuid

import jwt
from pydantic import ValidationError

from chatbot.schemas.auth import Credentials, RegisterRequest
from chatbot.security.password import hash_password, verify_password
from chatbot.security.tokens import (
    create_access_token,
    create_refresh_token,
    get_user_id_from_token,
)


class AuthTest(unittest.TestCase):
    def test_passwords_are_hashed_and_verified(self):
        hashed = hash_password("correct horse battery staple")
        self.assertNotEqual(hashed, "correct horse battery staple")
        self.assertTrue(verify_password("correct horse battery staple", hashed))
        self.assertFalse(verify_password("wrong password", hashed))

    def test_tokens_enforce_their_type(self):
        user_id = uuid.uuid4()
        self.assertEqual(
            get_user_id_from_token(create_access_token(user_id)), user_id
        )
        self.assertEqual(
            get_user_id_from_token(create_refresh_token(user_id), "refresh"),
            user_id,
        )
        with self.assertRaises(jwt.InvalidTokenError):
            get_user_id_from_token(create_refresh_token(user_id))

    def test_credentials_normalize_email_and_validate_password(self):
        credentials = Credentials(email="User@Example.COM", password="password123")
        self.assertEqual(credentials.email, "user@example.com")
        with self.assertRaises(ValidationError):
            Credentials(email="not-an-email", password="short")

    def test_registration_normalizes_and_validates_username(self):
        registration = RegisterRequest(
            email="user@example.com",
            username="  Some_User  ",
            password="password123",
        )
        self.assertEqual(registration.username, "some_user")
        with self.assertRaises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                username="not valid!",
                password="password123",
            )


if __name__ == "__main__":
    unittest.main()
