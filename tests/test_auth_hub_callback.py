import unittest

from flask import Flask, request

from auth_hub import CALLBACK_URL_QUERY_KEYS, redirect_target_from_request_args

app = Flask(__name__)


class AuthHubCallbackQueryTests(unittest.TestCase):
    def test_priority_callbackurl_before_next(self):
        with app.test_request_context("/?next=/a&callbackUrl=/b"):
            self.assertEqual(redirect_target_from_request_args(request), "/b")

    def test_next_when_no_callbackurl(self):
        with app.test_request_context("/?next=%2Fhistorico"):
            self.assertEqual(redirect_target_from_request_args(request), "/historico")

    def test_return_url_alias(self):
        with app.test_request_context("/?returnUrl=%2Fx"):
            self.assertEqual(redirect_target_from_request_args(request), "/x")

    def test_empty_returns_none(self):
        with app.test_request_context("/"):
            self.assertIsNone(redirect_target_from_request_args(request))

    def test_keys_tuple_nonempty(self):
        self.assertIn("callbackUrl", CALLBACK_URL_QUERY_KEYS)
        self.assertIn("destination", CALLBACK_URL_QUERY_KEYS)


if __name__ == "__main__":
    unittest.main()
