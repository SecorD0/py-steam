from __future__ import annotations

import json
import time
from base64 import b64encode
from typing import Optional

import requests
from Crypto.PublicKey.RSA import RsaKey
from fake_useragent import UserAgent

from py_steam import exceptions
from py_steam.account import Account
from py_steam.crypto import pkcs1v15_encrypt, rsa_publickey
from py_steam.models import SteamUrl
from py_steam.profile import Profile
from py_steam.steamid import SteamID
from py_steam.utils import generate_session_id, login_required


class WebClient:
    """
    This class is the entry point for interacting with Steam from Web session.

    Attributes:
        proxy (Optional[str]): a proxy used in the client.
        check_proxy (bool): check if the proxy is working when initializing.
        username (str): a username.
        password (str): a password.
        key (Optional[RsaKey]): an RSA key.
        logged_on (bool): current authorization status.
        session (Optional[requests.Session]): a session instance.
        session_id (Optional[str]): a session ID.
        captcha_gid (int): a captcha ID.
        captcha_code (str): a captcha code from the image.
        email_domain (Optional[str]): an email domain.
        steamid (Optional[SteamID]): a SteamID instance.
        client (WebClient): the client instance for 'login_required' decorator.
        account (Account): an initialized Account class.
        profile (Profile): an initialized Profile class.

    """
    proxy: Optional[str] = None
    check_proxy: bool = True
    username: str = ''
    password: Optional[str] = None
    key: Optional[RsaKey] = None
    logged_on: bool = False
    session: Optional[requests.Session] = None
    session_id: Optional[str] = None
    captcha_gid: int = -1
    captcha_code: str = ''
    email_domain: Optional[str] = None
    steamid: Optional[SteamID] = None

    client: WebClient
    account: Account
    profile: Profile

    def __init__(self, proxy: Optional[str] = None, check_proxy: bool = True) -> None:
        """
        Initialize the class.

        Args:
            proxy (str): a proxy in one of the following formats (None):

            - login:password@proxy:port
            - http://login:password@proxy:port
            - proxy:port
            - http://proxy:port

            check_proxy (bool): check if the proxy is working. (True)

        Raises:
            InvalidProxy: when the specified proxy doesn't work.

        """
        self.proxy = proxy
        self.session = requests.Session()
        self.session.headers.update({
            'Origin': 'https://store.steampowered.com/',
            'Referer': 'https://store.steampowered.com/',
            'User-Agent': UserAgent().chrome
        })
        if self.proxy:
            try:
                if 'http' not in self.proxy:
                    self.proxy = f'http://{self.proxy}'

                proxies = {'http': self.proxy, 'https': self.proxy}
                self.session.proxies.update(proxies)
                if check_proxy:
                    your_ip = requests.get('http://eth0.me/', proxies=proxies).text.rstrip()
                    if your_ip not in proxy:
                        raise exceptions.InvalidProxy(f"Proxy doesn't work! Your IP is {your_ip}.")

            except exceptions.InvalidProxy:
                pass

            except Exception as e:
                raise exceptions.InvalidProxy(str(e))

        self.client = self
        self.account = Account(self)
        self.profile = Profile(self)

    def __load_key(self) -> None:
        """
        Load an RSA key.
        """
        if not self.key:
            resp = self.get_rsa_key(self.username)
            self.key = rsa_publickey(int(resp['publickey_mod'], 16), int(resp['publickey_exp'], 16))
            self.timestamp = resp['timestamp']

    def __send_login(self, captcha: str = '', email_code: str = '', twofactor_code: str = '') -> Optional[dict]:
        """
        Send login request to the Steam.

        Args:
            captcha (str): the captcha answer.
            email_code (str): an email code to confirm authorization.
            twofactor_code (str): a 2FA code to confirm authorization.

        Returns:
            Optional[dict]: the response of the request.

        Raises:
            HTTPError: any problem with HTTP request.

        """
        data = {
            'username': self.username,
            "password": b64encode(pkcs1v15_encrypt(self.key, self.password.encode('ascii'))),
            "emailauth": email_code,
            "emailsteamid": str(self.steamid.steamid64) if email_code else '',
            "twofactorcode": twofactor_code,
            "captchagid": self.captcha_gid,
            "captcha_text": captcha,
            "loginfriendlyname": "webauth",
            "rsatimestamp": self.timestamp,
            "remember_login": 'true',
            "donotcache": int(time.time() * 100000),
        }
        response = None
        try:
            response = self.session.post(SteamUrl.COMMUNITY_URL + '/login/dologin/', data=data, timeout=15)
            if response.status_code == requests.codes.ok:
                return response.json()

            raise exceptions.HTTPError(response=response)

        except requests.exceptions.RequestException:
            raise exceptions.HTTPError(response=response)

    def __finalize_login(self, login_response: dict) -> None:
        """
        Finalize authorization by assigning values to some class attributes.

        Args:
            login_response (dict): the response of the login request.

        """
        self.steamid = SteamID(login_response['transfer_parameters']['steamid'])

    def get_rsa_key(self, username: str) -> Optional[dict]:
        """
        Get an RSA key for a specified username.

        Args:
            username (str): a username.

        Returns:
            Optional[dict]: the response of the request.

        Raises:
            HTTPError: any problem with HTTP request.

        """
        response = None
        try:
            data = {
                'username': username,
                'donotcache': int(time.time() * 1000)
            }
            response = self.session.post(SteamUrl.COMMUNITY_URL + '/login/getrsakey/', timeout=15, data=data)
            if response.status_code == requests.codes.ok:
                return response.json()

            raise exceptions.HTTPError(response=response)

        except requests.exceptions.RequestException:
            raise exceptions.HTTPError(response=response)

    def login(
            self, username: str, password: str, captcha: str = '', email_code: str = '', twofactor_code: str = '',
            language: str = 'english'
    ) -> Optional[requests.session]:
        """
        Authorize in the specified account.

        Args:
            username (str): a username.
            password (str): a password.
            captcha (str): the captcha answer.
            email_code (str): an email code to confirm authorization.
            twofactor_code (str): a 2FA code to confirm authorization.
            language (str): the language for Steam client (english).

        Returns:
            Optional[requests.session]: a session.

        Raises:
            LoginIncorrect: wrong a username or a password.
            TooManyLoginFailures: when you've made too many login failures.
            CaptchaRequired: when captcha is needed.
            CaptchaRequiredLoginIncorrect: when captcha is needed and the login is incorrect.
            EmailCodeRequired: when it's necessary to specify a code from the email.
            TwoFactorCodeRequired: when it's necessary to specify a 2FA code.

        """
        self.username = username
        self.password = password
        if self.logged_on:
            return self.session

        if not captcha and self.captcha_code:
            captcha = self.captcha_code

        self.__load_key()
        resp = self.__send_login(captcha=captcha, email_code=email_code, twofactor_code=twofactor_code)
        if resp['success'] and resp['login_complete']:
            self.logged_on = True
            self.password = ''
            self.captcha_gid = -1
            self.captcha_code = ''

            for cookie in list(self.session.cookies):
                for domain in ['store.steampowered.com', 'help.steampowered.com', 'steamcommunity.com']:
                    self.session.cookies.set(cookie.name, cookie.value, domain=domain, secure=cookie.secure)

            self.session_id = generate_session_id()

            for domain in ['store.steampowered.com', 'help.steampowered.com', 'steamcommunity.com']:
                self.session.cookies.set('Steam_Language', language, domain=domain)
                self.session.cookies.set('birthtime', '-3333', domain=domain)
                self.session.cookies.set('sessionid', self.session_id, domain=domain)

            self.__finalize_login(resp)

            return self.session

        else:
            if resp.get('captcha_needed', False):
                self.captcha_gid = resp['captcha_gid']
                self.captcha_code = ''

                if resp.get('clear_password_field', False):
                    self.password = ''
                    raise exceptions.CaptchaRequiredLoginIncorrect(resp['message'])
                else:
                    raise exceptions.CaptchaRequired(resp['message'])

            elif resp.get('emailauth_needed', False):
                self.email_domain = resp['emaildomain']
                self.steamid = SteamID(resp['emailsteamid'])
                raise exceptions.EmailCodeRequired(resp['message'])

            elif resp.get('requires_twofactor', False):
                raise exceptions.TwoFactorCodeRequired(resp['message'])

            elif 'too many login failures' in resp.get('message', ''):
                raise exceptions.TooManyLoginFailures(resp['message'])

            else:
                self.password = ''
                raise exceptions.LoginIncorrect(resp['message'])

    def cli_login(
            self, username: str = '', password: str = '', captcha: str = '', email_code: str = '',
            twofactor_code: str = '', language: str = 'english'
    ) -> Optional[requests.session]:
        """
        Authorize in the specified account.

        Args:
            username (str): a username.
            password (str): a password.
            captcha (str): the captcha answer.
            email_code (str): an email code to confirm authorization.
            twofactor_code (str): a 2FA code to confirm authorization.
            language (str): the language for Steam client (english).

        Returns:
            Optional[requests.session]: a session.

        Raises:
            LoginIncorrect: wrong a username or a password.
            TooManyLoginFailures: when you've made too many login failures.
            CaptchaRequired: when captcha is needed.
            CaptchaRequiredLoginIncorrect: when captcha is needed and the login is incorrect.
            EmailCodeRequired: when it's necessary to specify a code from the email.
            TwoFactorCodeRequired: when it's necessary to specify a 2FA code.

        """
        if not username:
            username = input('Enter the username: ')

        if not password:
            password = input('Enter the password: ')

        while True:
            try:
                return self.login(username, password, captcha, email_code, twofactor_code, language)

            except exceptions.LoginIncorrect:
                print('You entered wrong a username or a password!')
                username = input('Enter the username: ')
                password = input('Enter the password: ')

            except exceptions.CaptchaRequired:
                print(
                    f'You need to solve the CAPTCHA: https://steamcommunity.com/login/rendercaptcha/?gid={self.captcha_gid}'
                )
                captcha = input('Enter the CAPTCHA code: ')

            except exceptions.EmailCodeRequired:
                email_code = input(f'Enter the code from the {self.email_domain} email for {username}: ')
                twofactor_code = ''

            except exceptions.TwoFactorCodeRequired:
                email_code = ''
                twofactor_code = input(f'Enter the 2FA code for {username}: ')

    @login_required
    def is_session_alive(self) -> bool:
        """
        Check if the session has expired.

        Returns:
            bool: True if the session is still alive.

        """
        steam_login = self.username
        resp = self.session.get(SteamUrl.COMMUNITY_URL)
        return steam_login.lower() in resp.text.lower()

    @login_required
    def logout(self) -> None:
        """
        Logout.

        Raises:
            UnsuccessfulLogout: for some reason failed to logout.

        """
        data = {'sessionid': self.session_id}
        self.session.post(SteamUrl.STORE_URL + '/logout/', data=data)
        if self.is_session_alive():
            raise exceptions.UnsuccessfulLogout('Logout unsuccessful')
        self.logged_on = False


class MobileClient(WebClient):
    """
    This class is the entry point for interacting with Steam from Mobile session.

    Attributes:
        All from the WebClient.
        oauth_token (Optional[str]): an oauth token.

    """
    oauth_token: Optional[str]

    def __send_login(self, captcha: str = '', email_code: str = '', twofactor_code: str = '') -> Optional[dict]:
        """
        Send login request to the Steam.

        Args:
            captcha (str): the captcha answer.
            email_code (str): an email code to confirm authorization.
            twofactor_code (str): a 2FA code to confirm authorization.

        Returns:
            Optional[dict]: the response of the request.

        Returns:
            HTTPError: any problem with HTTP request.

        """
        data = {
            'username': self.username,
            'password': b64encode(pkcs1v15_encrypt(self.key, self.password.encode('ascii'))),
            'emailauth': email_code,
            'emailsteamid': str(self.steamid.steamid64) if email_code else '',
            'twofactorcode': twofactor_code,
            'captchagid': self.captcha_gid,
            'captcha_text': captcha,
            'loginfriendlyname': 'mobileauth',
            'rsatimestamp': self.timestamp,
            'remember_login': 'true',
            'donotcache': int(time.time() * 100000),
            'oauth_client_id': 'DE45CD61',
            'oauth_scope': 'read_profile write_profile read_client write_client',
        }

        self.session.cookies.set('mobileClientVersion', '0 (2.1.3)')
        self.session.cookies.set('mobileClient', 'android')

        response = None
        try:
            response = self.session.post(SteamUrl.COMMUNITY_URL + '/login/dologin/', data=data, timeout=15)
            if response.status_code == requests.codes.ok:
                return response.json()

            raise exceptions.HTTPError(response=response)

        except requests.exceptions.RequestException:
            raise exceptions.HTTPError(response=response)

        finally:
            self.session.cookies.pop('mobileClientVersion', None)
            self.session.cookies.pop('mobileClient', None)

    def __finalize_login(self, login_response: dict) -> None:
        """
        Finalize authorization by assigning values to some class attributes.

        Args:
            login_response (dict): the response of the login request.

        """
        data = json.loads(login_response['oauth'])
        self.steamid = SteamID(data['steamid'])
        self.oauth_token = data['oauth_token']
