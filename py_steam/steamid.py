from typing import Tuple

from pretty_utils.type_functions.classes import AutoRepr

from py_steam.models import SteamUrl


class SteamID(AutoRepr):
    def __init__(self, id: str or int):
        self.steamid64, self.accountid = extract_steamids(id)
        self.profile_url = SteamUrl.COMMUNITY_URL + '/profiles/' + str(self.steamid64)


def extract_steamids(id: str or int = 0) -> Tuple[int, int]:
    value = str(id)
    steamid = 0
    accountid = 0

    if value.isdigit():
        value = int(value)
        if 0 < value < 2 ** 32:
            steamid = int(value + 76561197960265728)
            accountid = value

        elif value < 2 ** 64:
            steamid = value
            accountid = int(value - 76561197960265728)

    return steamid, accountid
