class ClientException(Exception):
    pass


class InvalidProxy(ClientException):
    pass


class HTTPError(ClientException):
    pass


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
