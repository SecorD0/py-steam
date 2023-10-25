import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup as BS
from pretty_utils.type_functions.classes import AutoRepr

from py_steam import exceptions
from py_steam.models import SteamUrl, AjaxUrl
from py_steam.utils import extract_float, login_required, extract_currency


@dataclass
class Balance:
    balance_text: str
    balance: float
    currency: Optional[str]


@dataclass
class Limit:
    limited: bool = False
    spent: float = 5.00


class Bans(AutoRepr):
    def __init__(
            self, vac_banned: bool = False, vac_bans: List[str] = None, game_bans: List[str] = None,
            trade_banned: bool = False, community_banned: bool = False, community_ban_reason: Optional[str] = None
    ) -> None:
        self.vac_banned: bool = vac_banned
        self.vac_bans: List[str] = vac_bans
        self.game_bans: List[str] = game_bans
        self.trade_banned: bool = trade_banned
        self.community_banned: bool = community_banned
        self.community_ban_reason: str = community_ban_reason


class AccountInfo(AutoRepr):
    """
    An instance with account info.

    Attributes:
        username (str): a username.
        balance (Optional[Balance]): a balance.
        country (Optional[str]): a country.
        email_address (str): an email address.
        email_status (str): a email status.
        phone_number_ending (Optional[str]): last digits of phone number.
        steam_guard_status (str): a Steam Guard status.
        limit (Optional[Limit]): whether the account is limited.
        bans (Optional[Bans]): gaming ban list.

    """

    def __init__(
            self, username: str = '', balance: Optional[Balance] = None, country: Optional[str] = None,
            email_address: str = '', email_status: str = '', phone_number_ending: Optional[str] = None,
            steam_guard_status: str = '', limit: Optional[Limit] = None, bans: Optional[Bans] = None
    ) -> None:
        """
        Initialize a class.

        Args:
            username (str): a username.
            balance (Optional[Balance]): a balance.
            country (Optional[str]): a country.
            email_address (str): an email address.
            email_status (str): a email status.
            phone_number_ending (Optional[str]): last digits of phone number.
            steam_guard_status (str): a Steam Guard status.
            limit (Optional[Limit]): whether the account is limited.
            bans (Optional[Bans]): gaming ban list.

        """
        self.username: str = username
        self.balance: Optional[Balance] = balance
        self.country: Optional[str] = country
        self.email_address: str = email_address
        self.email_status: str = email_status
        self.phone_number_ending: Optional[str] = phone_number_ending
        self.steam_guard_status: str = steam_guard_status
        self.limit: Optional[Limit] = limit
        self.bans: Optional[Bans] = bans


class Account:
    """
    This class allows you to interact with the account.

    Attributes:
        s (str): ID of the support request.
        client (WebClient): the client instance.
        req_get (requests.get): an alias of 'requests.session.get'.
        req_post (requests.post): an alias of 'requests.session.post'.

    """

    def __init__(self, client) -> None:
        """
        Initialize a class.

        Args:
            client (WebClient): the client instance.

        """
        self.s = None
        self.client = client
        self.req_get: requests.get = self.client.session.get
        self.req_post: requests.post = self.client.session.post

    @login_required
    def __get_balance(self, soup: BS) -> Optional[Balance]:
        try:
            balance_text = soup.find('div', class_='accountData price').text
            balance = extract_float(balance_text)
            currency = extract_currency(balance_text)
            return Balance(balance_text=balance_text, balance=balance, currency=currency)

        except:
            pass

    @login_required
    def __get_data_fields(self, soup: BS) -> Optional[dict]:
        try:
            data_fields = soup.find_all(class_='account_data_field')
            country = data_fields[0].get_text(strip=True)
            email_address = data_fields[1].get_text(strip=True)
            email_status = data_fields[2].get_text(strip=True).lower()
            if len(data_fields) == 5:
                phone_number_ending = re.sub('[^0-9]', '', data_fields[3].get_text(strip=True))
                steam_guard_status = str(data_fields[4].parent)

            else:
                phone_number_ending = None
                steam_guard_status = str(data_fields[3].parent)

            if 'sg_fair' in steam_guard_status:
                steam_guard_status = 'email'

            elif 'sg_good' in steam_guard_status:
                steam_guard_status = 'mobile authenticator'

            else:
                steam_guard_status = 'disabled'

            return {
                'country': country, 'email_address': email_address, 'phone_number_ending': phone_number_ending,
                'email_status': email_status, 'steam_guard_status': steam_guard_status
            }

        except:
            pass

    @login_required
    def is_limited(self) -> Optional[Limit]:
        try:
            limit = Limit()
            soup = BS(self.req_get(SteamUrl.HELP_URL).text, 'html.parser')
            element = soup.find('div', class_='help_event_limiteduser_spend help_highlight_text')
            if element:
                spent = extract_float(element.find('span').text.split(' / ')[0])
                limit.limited = True
                limit.spent = spent

            return limit

        except:
            pass

    @login_required
    def get_bans(self) -> Optional[Bans]:
        bans = Bans(vac_bans=[], game_bans=[])
        try:
            bans_info = self.client.profile.get_bans(self.client.steamid)
            soup = BS(self.req_get(SteamUrl.WIZARD_URL + '/VacBans').text, 'html.parser')
            headers = soup.find_all('div', class_='vac_ban_header')
            for header in headers:
                if 'VAC' in header.get_text(strip=True):
                    games = header.parent.find('div', class_='refund_info_box').find_all(
                        'span', class_='help_highlight_text'
                    )
                    for game in games:
                        bans.vac_bans.append(game.get_text(strip=True))

                else:
                    games = header.parent.find('div', class_='refund_info_box').find_all(
                        'span', class_='help_highlight_text'
                    )
                    for game in games:
                        bans.game_bans.append(game.get_text(strip=True))

            if bans.vac_bans:
                bans.vac_banned = True

            bans.trade_banned = bans_info['trade']
            bans.community_banned = bans_info['community']
            soup = BS(self.req_get(SteamUrl.STORE_URL + '/supportmessages/').text, 'html.parser')
            reason = soup.find('div', class_='support_message_content').find('h1')
            if reason:
                bans.community_ban_reason = reason.get_text(strip=True)

        except:
            pass

        return bans

    @login_required
    def get_account_info(self) -> AccountInfo:
        account_info = AccountInfo()
        account_info.username = self.client.username
        try:
            soup = BS(self.req_get(SteamUrl.STORE_URL + '/account/').text, 'html.parser')
            account_info.balance = self.__get_balance(soup)
            data_fields = self.__get_data_fields(soup)
            if data_fields:
                account_info.country = data_fields['country']
                account_info.email_address = data_fields['email_address']
                account_info.email_status = data_fields['email_status']
                account_info.phone_number_ending = data_fields['phone_number_ending']
                account_info.steam_guard_status = data_fields['steam_guard_status']

            account_info.limit = self.is_limited()
            account_info.bans = self.get_bans()

        except:
            pass

        return account_info

    @login_required
    def unlock(self, unlock_code: str) -> dict:
        """
        Unlock an account with L-code.

        Args:
            unlock_code (str): L-code to unlock the account, e.g.: L8CP37T, 8CP37T, l8cp37t, 8cp37t.

        Returns:
            dict: the response of the query

        """
        resp = {'success': 0}
        try:
            if len(unlock_code) == 6:
                unlock_code = 'L' + unlock_code

            if len(unlock_code) != 7 or unlock_code[0] != 'L':
                raise exceptions.InvalidUnlockCode('You provided invalid unlock code!')

            unlock_code = unlock_code.upper()
            data = {
                'sessionid': self.client.session_id,
                'wizard_ajax': '1',
                'gamepad': '0',
                'unlockcode': unlock_code
            }
            resp = self.req_post(AjaxUrl.DO + 'AccountUnlock', data=data).json()

        except:
            pass

        return resp

    @login_required
    def change_primary_language(
            self, primary_language: str = 'english', secondary_languages: Optional[List[str]] = None,
            additional_languages: Optional[List[str]] = None
    ) -> dict:
        resp = {'success': 0}
        try:
            data = {
                'sessionid': self.client.session_id,
                'primary_language': primary_language,
                'secondary_languages[]': secondary_languages,
                'additional_languages[]': additional_languages
            }
            resp = self.req_post(SteamUrl.STORE_URL + '/account/savelanguagepreferences', data=data).json()

        except:
            pass

        return resp

    @login_required
    def change_email(self, confirmation_code: str = '') -> dict:
        resp = {'success': 0}
        try:
            if confirmation_code:
                params = {
                    'sessionid': self.client.session_id,
                    's': self.s,
                    'issueid': self.issueid,
                    'wizard_ajax': '1',
                    'gamepad': '0',
                    'reset': '2',
                    'lost': '0',
                    'method': '2',
                    'code': confirmation_code
                }
                resp = self.req_get(AjaxUrl.VERIFY + 'AccountRecoveryCode', params=params).json()

            else:
                resp = self.req_get(SteamUrl.WIZARD_URL + '/HelpChangeEmail')
                location = parse_qs(urlparse(resp.history[-1].headers['Location']).query)
                self.s = location['s'][0]
                self.issueid = location['issueid'][0]
                data = {
                    'sessionid': self.client.session_id,
                    's': self.s,
                    'wizard_ajax': '1',
                    'gamepad': '0',
                    'method': '2',
                    'link': ''
                }
                resp = self.req_post(AjaxUrl.SEND + 'AccountRecoveryCode', data=data).json()

        except:
            pass

        return resp

    @login_required
    def verify_email_changing(self, email: str, confirmation_code: str = '') -> dict:
        resp = {'success': 0}
        try:
            data = {
                'sessionid': self.client.session_id,
                'account': str(self.client.steamid.accountid),
                's': self.s,
                'wizard_ajax': '1',
                'gamepad': '0',
                'email': email
            }
            if confirmation_code:
                data['email_change_code'] = confirmation_code
                resp = self.req_post(AjaxUrl.ACCOUNT + 'RecoveryConfirmChangeEmail', data=data).json()

            else:
                resp = self.req_post(AjaxUrl.ACCOUNT + 'RecoveryChangeEmail', data=data).json()

        except:
            pass

        return resp
