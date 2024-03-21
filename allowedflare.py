import logging
from http.cookies import Morsel
from os import environ, getenv
from typing import Mapping

from jwt import InvalidTokenError, InvalidSignatureError, decode
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


def clean_username(username: str) -> str:
    """
    Remove @{suffix} from username, where suffix is `ALLOWEDFLARE_EMAIL_DOMAIN` or
    `ALLOWEDFLARE_PRIVATE_DOMAIN`. Set `ALLOWEDFLARE_EMAIL_DOMAIN=off` to leave the
    username unmodified.

    Compared to `RemoteUserBackend.clean_username()`, the `self` argument is omitted to make
    user-provided replacement easier.
    """
    suffix = getenv('ALLOWEDFLARE_EMAIL_DOMAIN', getenv('ALLOWEDFLARE_PRIVATE_DOMAIN', 'off'))
    return username.removesuffix(f'@{suffix}')


def authenticate(cookies: Mapping[str, Morsel | str]) -> tuple[str, str, dict]:
    """
    Return a tuple with suffix-trimmed username, failure/success message, and decoded token.

    On failure to authenticate, the username will be the empty string `''` and the token will be the
    empty dictionary `{}`.
    """
    url = getenv('ALLOWEDFLARE_ACCESS_URL', 'off')
    if url == 'off':
        return ('', 'Allowedflare is off', {})

    if 'CF_Authorization' not in cookies:
        return ('', 'Allowedflare could not find CF_Authorization cookie', {})

    morsel_or_string = cookies['CF_Authorization']
    if isinstance(morsel_or_string, Morsel):
        cookie = morsel_or_string.value
    else:
        cookie = morsel_or_string

    token = {'token': 'not parsed'}
    try:
        # TODO make this module-level and ensure cache is being used to smooth over intermittent network outages
        jwks_client = PyJWKClient(f'{url}/cdn-cgi/access/certs', timeout=3)
        signing_key = jwks_client.get_signing_key_from_jwt(cookie)
        token = decode(
            cookie,
            key=signing_key.key,
            audience=environ['ALLOWEDFLARE_AUDIENCE'],
            algorithms=['RS256'],
        )
    except InvalidTokenError as error:
        return ('', f'Allowedflare failed to decode CF_Authorization cookie {cookie} {error}', {})
    except InvalidSignatureError:
        return ('', f'Allowedflare found invalid signature in CF_Authorization cookie {token}', {})
    except Exception as error:
        return ('', f'Allowedflare unexpected {error} {token}', {})

    # It looks like people will have email, service tokens will have common_name
    unprocessed_name = token.get('email', token.get('common_name', ''))
    if not unprocessed_name:
        return (
            '',
            f'Allowedflare found neither common_name nor email in otherwise valid token {token}',
            {},
        )

    name = clean_username(unprocessed_name)
    return (name, f'Allowedflare authenticated {name}', token)
