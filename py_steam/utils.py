import re
from binascii import hexlify
from os import urandom
from typing import Optional

from py_steam import exceptions
from py_steam.crypto import sha1_hash
from py_steam.models import SteamUrl


def login_required(func):
    """Check authorization in the account."""

    def func_wrapper(self, *args, **kwargs):
        if not self.client.logged_on:
            raise exceptions.LoginRequired('Use login method first')

        else:
            return func(self, *args, **kwargs)

    return func_wrapper


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
        return float(re.sub('[^0-9.,]', '', text).replace(',', '.'))

    except:
        return 0.0


def extract_currency(text: str) -> str:
    """
    Extract the text (currency) from the balance text.

    :param str text: a text
    :return int: the extracted text (currency)
    """
    try:
        return re.sub('[\s0-9.,-]', '', text)

    except:
        return ''


def generate_session_id():
    """Generate session ID."""
    return hexlify(sha1_hash(urandom(32)))[:32].decode('ascii')


def get_profile_url(s64_or_id: str or int) -> str:
    """
    Convert a SteamID64, a custom ID or a profile URL to the profile URL.

    :param str or int s64_or_id: a SteamID64, a custom ID or a profile URL
    :return str: the profile URL
    """
    try:
        s64_or_id = str(s64_or_id)
        if 'https://steamcommunity.com/' in s64_or_id:
            if s64_or_id[-1] == '/':
                s64_or_id = s64_or_id[:-1]

            return s64_or_id

        elif len(s64_or_id) == 17:
            return SteamUrl.COMMUNITY_URL + f'/profiles/{s64_or_id}'

        else:
            return SteamUrl.COMMUNITY_URL + f'/id/{s64_or_id}'


    except:
        pass


def s64_to_s32(s64: str or int) -> Optional[int]:
    try:
        return int(s64) & 0xFFffFFff

    except:
        pass
