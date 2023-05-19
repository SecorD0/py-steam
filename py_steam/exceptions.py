from typing import Optional

import requests


class ClientException(Exception):
    pass


class InvalidProxy(ClientException):
    pass


class HTTPError(ClientException):
    def __init__(self, response: Optional[requests.Response] = None):
        self.response = response

    def __str__(self):
        try:
            return f'{self.response.status_code}, {self.response.text}'

        except:
            return 'Something went wrong!'


class LoginIncorrect(ClientException):
    pass


class TooManyLoginFailures(ClientException):
    pass


class CaptchaRequired(ClientException):
    pass


class CaptchaRequiredLoginIncorrect(CaptchaRequired, LoginIncorrect):
    pass


class EmailCodeRequired(ClientException):
    pass


class TwoFactorCodeRequired(ClientException):
    pass


class UnsuccessfulLogout(ClientException):
    pass


class LoginRequired(ClientException):
    pass


class AccountException(Exception):
    pass


class InvalidUnlockCode(AccountException):
    pass


class ProfileException(Exception):
    pass


class InventoryUnavailable(ProfileException):
    pass


class ProfileUnavailable(ProfileException):
    pass
