import hmac
import os
import unittest

from app.api_keys import generate_api_key, hash_api_key, lookup_prefix, normalize_scopes


class ApiKeyTest(unittest.TestCase):
    def setUp(self):
        os.environ["API_KEY_PEPPER"] = "test-pepper"

    def test_generated_key_has_service_prefix(self):
        api_key = generate_api_key()

        self.assertTrue(api_key.startswith("hr_live_"))
        self.assertGreater(len(api_key), 40)

    def test_hash_does_not_store_raw_key(self):
        api_key = "hr_live_example-secret"
        key_hash = hash_api_key(api_key)

        self.assertNotIn(api_key, key_hash)
        self.assertTrue(hmac.compare_digest(key_hash, hash_api_key(api_key)))

    def test_lookup_prefix_is_not_full_key(self):
        api_key = generate_api_key()

        self.assertTrue(api_key.startswith(lookup_prefix(api_key)))
        self.assertLess(len(lookup_prefix(api_key)), len(api_key))

    def test_normalize_scopes_rejects_unknown_scope(self):
        with self.assertRaises(ValueError):
            normalize_scopes(["happyrobot", "superuser"])

    def test_normalize_scopes_accepts_admin(self):
        self.assertEqual(normalize_scopes(["admin"]), ["admin"])


if __name__ == "__main__":
    unittest.main()
