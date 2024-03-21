from sys import modules

from django.test import SimpleTestCase

from allowedflare import clean_username


class Test(SimpleTestCase):
    def test_clean_username_unmodified(self):
        with self.settings(
            ALLOWEDFLARE_EMAIL_DOMAIN='off', ALLOWEDFLARE_PRIVATE_DOMAIN='domain.com'
        ):
            self.assertEqual(clean_username('user@domain.com'), 'user@domain.com')
        with self.settings(
            ALLOWEDFLARE_EMAIL_DOMAIN='domain.com', ALLOWEDFLARE_PRIVATE_DOMAIN='domain.dev'
        ):
            self.assertEqual(clean_username('user@domain.com'), 'user')
        with self.settings(ALLOWEDFLARE_PRIVATE_DOMAIN='domain.com'):
            self.assertEqual(clean_username('user@domain.com'), 'user')

    def test_fetch_or_reuse_keys(self):
        # Warning: probably not parallel safe

        # Arrange: import
        try:
            del modules['allowedflare']
        except KeyError:
            pass
        import allowedflare

        # Assert: initial conditions
        self.assertEqual(allowedflare.cached_keys, [])
        self.assertEqual(allowedflare.cache_updated.timestamp(), 0)
        with self.settings(ALLOWEDFLARE_ACCESS_URL='https://domain.cloudflareaccess.com'):
            # Act: TODO mock
            keys = allowedflare.fetch_or_reuse_keys()

        # Assert: module level variables are updated
        self.assertEqual(allowedflare.cached_keys, keys)
        self.assertGreater(allowedflare.cache_updated.timestamp(), 0)

        # Cleanup
        del modules['allowedflare']
