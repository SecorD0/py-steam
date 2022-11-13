import enum
from collections import namedtuple


class Currency(enum.IntEnum):
    USD = 1
    GBP = 2
    EUR = 3
    CHF = 4
    RUB = 5
    PLN = 6
    BRL = 7
    JPY = 8
    NOK = 9
    IDR = 10
    MYR = 11
    PHP = 12
    SGD = 13
    THB = 14
    VND = 15
    KRW = 16
    TRY = 17
    UAH = 18
    MXN = 19
    CAD = 20
    AUD = 21
    NZD = 22
    CNY = 23
    INR = 24
    CLP = 25
    PEN = 26
    COP = 27
    ZAR = 28
    HKD = 29
    TWD = 30
    SAR = 31
    AED = 32
    # NOK = 33
    ARS = 34
    ILS = 35
    BYN = 36
    KZT = 37
    KWD = 38
    QAR = 39
    CRC = 40
    UYU = 41
    BGN = 42
    HRK = 43
    CZK = 44
    DKK = 45
    HUF = 46
    RON = 47


class TradeOfferState(enum.IntEnum):
    Invalid = 1
    Active = 2
    Accepted = 3
    Countered = 4
    Expired = 5
    Canceled = 6
    Declined = 7
    InvalidItems = 8
    ConfirmationNeed = 9
    CanceledBySecondaryFactor = 10
    StateInEscrow = 11


class SteamUrl:
    API_URL = 'https://api.steampowered.com'
    COMMUNITY_URL = 'https://steamcommunity.com'
    HELP_URL = 'https://help.steampowered.com'
    STORE_URL = 'https://store.steampowered.com'


class AjaxUrl:
    DO = SteamUrl.HELP_URL + '/en/wizard/AjaxDo'
    SEND = SteamUrl.HELP_URL + '/en/wizard/AjaxSend'


class Endpoint:
    CHAT_LOGIN = SteamUrl.API_URL + '/ISteamWebUserPresenceOAuth/Logon/v1'
    SEND_MESSAGE = SteamUrl.API_URL + '/ISteamWebUserPresenceOAuth/Message/v1'
    CHAT_LOGOUT = SteamUrl.API_URL + '/ISteamWebUserPresenceOAuth/Logoff/v1'
    CHAT_POLL = SteamUrl.API_URL + '/ISteamWebUserPresenceOAuth/Poll/v1'


class Game:
    PredefinedOptions = namedtuple('PredefinedOptions', ['app_id', 'context_id'])

    STEAM = PredefinedOptions(753, 6)
    DOTA2 = PredefinedOptions(570, 2)
    CS = PredefinedOptions(730, 2)
    TF2 = PredefinedOptions(440, 2)
    PUBG = PredefinedOptions(578080, 2)
    RUST = PredefinedOptions(252490, 2)
    H1Z1 = PredefinedOptions(433850, 1)
    PD2 = PredefinedOptions(218620, 2)
    UNTURNED = PredefinedOptions(304930, 2)

    def __init__(self, app_id: int, context_id: int) -> None:
        self.app_id = app_id
        self.context_id = context_id
