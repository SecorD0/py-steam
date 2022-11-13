import re
from binascii import hexlify
from os import urandom

from py_steam import exceptions
from py_steam.crypto import sha1_hash


def login_required(func):
    """Check authorization in the account."""
    def func_wrapper(self, *args, **kwargs):
        if not self.client.logged_on:
            raise exceptions.LoginRequired('Use login method first')

        else:
            return func(self, *args, **kwargs)

    return func_wrapper


def generate_session_id():
    """Generate session ID."""
    return hexlify(sha1_hash(urandom(32)))[:32].decode('ascii')


def extract_int(text: str) -> int:
    """
    Extract the first sequence of digits an integer.

    :param str text: a text
    :return int: the extracted integer number
    """
    try:
        return int(re.sub('[^0-9]', '', text))

    except:
        return 0


def extract_float(text: str) -> float:
    """
    Extract the first sequence of digits a float.

    :param str text: a text
    :return int: the extracted float number
    """
    try:
        return float(re.sub('[^0-9.]', '', text))

    except:
        return 0.0
