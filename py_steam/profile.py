import copy
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import (List, Optional, Dict, Any)

import requests
from bs4 import BeautifulSoup as BS
from pretty_utils.type_functions.classes import AutoRepr
from pretty_utils.type_functions.strings import text_between

from py_steam import exceptions
from py_steam.models import SteamUrl
from py_steam.utils import extract_int, extract_float


@dataclass
class Location:
    """
    A location instance.

    Attributes:
        flag_icon - a URL to flag icon
        location - a location specified in a profile
    """
    flag_icon: Optional[str]
    location: Optional[str]


@dataclass
class Status:
    """
    A status instance.

    Attributes:
        status - the current status
        game - if the status is 'on-game', the game that is running
        last - a timestamp of the last login to Steam
    """
    status: str
    game: Optional[str]
    last: Optional[str]


@dataclass
class Counters:
    """Counters instance."""
    badges: int = 0
    games: int = 0
    screenshots: int = 0
    videos: int = 0
    workshopitems: int = 0
    reviews: int = 0
    guides: int = 0
    artworks: int = 0
    groups: int = 0
    friends: int = 0


class Badge:
    """
    A badge instance.

    Attributes:
        soup - the badge BeautifulSoup element
        url -
        title - a title of the badge
        game - a name of a game to which the badge belongs
        exp - the amount of experience gained through the badge
        level - the level of the badge
        earned - a timestamp of when the badge was received
    """

    def __repr__(self) -> str:
        """Create human-readable class output."""
        attributes = vars(self)
        try:
            del attributes['soup']
        except:
            pass
        values = ('{}={!r}'.format(key, value) for key, value in attributes.items())
        return '{}({})'.format(self.__class__.__name__, ', '.join(values))

    def __init__(self, soup: BS) -> None:
        """
        Initialize a class.

        :param BeautifulSoup soup: the badge BeautifulSoup element
        """
        self.soup: BS = soup
        self.url: str = self.get_url()
        self.title: str = self.get_title()
        self.game: str = self.get_game()
        self.exp: int = self.get_exp()
        self.level: Optional[int] = self.get_level()
        self.earned: int = self.get_earn_time()

    def get_url(self) -> str:
        """Get a URL to the badge."""
        try:
            return self.soup.find('a', class_='badge_row_overlay').attrs['href']

        except:
            pass

    def get_title(self) -> str:
        """Get a title of the badge."""
        try:
            return self.soup.find('div', class_='badge_info_title').text

        except:
            pass

    def get_game(self) -> str:
        """Get a name of a game to which the badge belongs."""
        try:
            return self.soup.find('div', class_='badge_title').text.split('\xa0')[0].strip()

        except:
            pass

    def get_exp(self) -> int:
        """Get the amount of experience gained through the badge."""
        try:
            lvl_xp: List[str] = self.soup.find('div', class_='badge_info_description').find('div',
                                                                                            class_='').get_text(
                strip=True).split(',')
            if len(lvl_xp) == 2:
                return extract_int(lvl_xp[1])
            return extract_int(lvl_xp[0])

        except:
            pass

    def get_level(self) -> Optional[int]:
        """Get the level of the badge."""
        try:
            lvl_xp: List[str] = self.soup.find('div', class_='badge_info_description').find('div',
                                                                                            class_='').get_text(
                strip=True).split(',')
            if len(lvl_xp) == 2:
                return extract_int(lvl_xp[0])
            return None

        except:
            pass

    def get_earn_time(self) -> int:
        """Get a timestamp of when the badge was received."""
        try:
            tmp: List[str] = self.soup.find('div', class_='badge_info_unlocked').get_text(strip=True).replace(
                'Unlocked ', '').split(' ')
            if len(tmp) == 5:
                return int(datetime.strptime(f'{tmp[2]} {tmp[0]:0>2} {tmp[1][:-1]} {tmp[4].upper():0>7}',
                                             '%Y %d %b %I:%M%p').timestamp())
            return int(datetime.strptime(f'{datetime.now().year} {tmp[0]:0>2} {tmp[1]} {tmp[3].upper():0>7}',
                                         '%Y %d %b %I:%M%p').timestamp())

        except:
            pass


class Game(AutoRepr):
    """
    A game instance.

    Attributes:
        appid - an appid of the game
        name - a name of the game
        icon - a URL to game icon
        hours - how many hours have been played in the game
        recent - how many hours have been played in the last 2 weeks
        last - a timestamp of the last game launch
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        """
        Create a game instance from the dictionary.

        :param Dict[str, Any] data: a dictionary containing information about a game, e.g.:

        {
            'appid': 730,
            'name': 'Counter-Strike: Global Offensive',
            'friendly_name': 'CSGO',
            'app_type': 1,
            'logo': 'https://cdn.cloudflare.steamstatic.com/steam/apps/730/capsule_184x69.jpg',
            'friendlyURL': 'CSGO',
            'availStatLinks': {'achievements': True, 'global_achievements': True, 'stats': False, 'gcpd': True,
                               'leaderboards': False, 'global_leaderboards': False},
            'hours_forever': '59',
            'last_played': 1625130841
        }
        """
        self.appid: int = int(data['appid'])
        self.name: str = data['name']
        self.icon: str = data['logo']
        self.hours: float = extract_float(data['hours_forever']) if 'hours_forever' in data else 0.0
        self.recent: float = extract_float(data['hours']) if 'hours' in data else 0.0
        self.last: int = int(data['last_played']) if 'last_played' in data else 0


class Context(AutoRepr):
    """
    A context instance.

    Attributes:
        id - a context ID
        name - a name of the context
        asset_count - the number of items in a given context
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        """
        Create a context instance from the dictionary.

        :param Dict[str, Any] data: a dictionary containing information about a context, e.g.:

        {
            'asset_count': 105,
            'id': '2',
            'name': 'Backpack'
        }
        """
        self.id: int = data['id']
        self.name: str = data['name']
        self.asset_count: int = data['asset_count']


@dataclass
class Tag:
    """
    A tag instance.

    Attributes:
        name - a name of the tag
        value - a value of the tag
    """
    name: str
    value: str


class Item(AutoRepr):
    """
    An item instance.

    Attributes:
        id - an item ID
        classid - an item ClassID
        instanceid - an item InstanceID
        name - a name of the item
        tradable - is it tradable?
        marketable - is it marketable?
        commodity - is it commodity?
        amount - the number of stacked items
        type - a type of the item
        description - the item description
        tags - tags of the item
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        """
        Create an item instance from the dictionary.

        :param Dict[str, Any] data: a dictionary containing information about an item, e.g.:

        {
            'appid': 730,
            'classid': '5061545468',
            'instanceid': '0',
            'currency': 0,
            'background_color': '',
            'icon_url': '-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXU5A1PIYQNqhpOSV-fRPasw8rsRVx4MwFo5PT8elUwgKKZJmtEvo_kxITZk6StNe-Fz2pTu8Aj3eqVpIqgjVfjrRI9fSmtc1Nw-Kh3',
            'descriptions': [{'type': 'html', 'value': ' '},
                             {'type': 'html', 'value': 'Container Series #4', 'color': '99ccff'},
                             {'type': 'html', 'value': ' '}, {'type': 'html', 'value': 'Contains one of the following:'},
                             {'type': 'html', 'value': 'Tec-9 | Blue Titanium', 'color': '4b69ff'},
                             {'type': 'html', 'value': 'M4A1-S | Blood Tiger', 'color': '4b69ff'},
                             {'type': 'html', 'value': 'FAMAS | Hexane', 'color': '4b69ff'},
                             {'type': 'html', 'value': 'P250 | Hive', 'color': '4b69ff'},
                             {'type': 'html', 'value': 'SCAR-20 | Crimson Web', 'color': '4b69ff'},
                             {'type': 'html', 'value': 'Five-SeveN | Case Hardened', 'color': '8847ff'},
                             {'type': 'html', 'value': 'MP9 | Hypnotic', 'color': '8847ff'},
                             {'type': 'html', 'value': 'Nova | Graphite', 'color': '8847ff'},
                             {'type': 'html', 'value': 'Dual Berettas | Hemoglobin', 'color': '8847ff'},
                             {'type': 'html', 'value': 'P90 | Cold Blooded', 'color': 'd32ce6'},
                             {'type': 'html', 'value': 'USP-S | Serum', 'color': 'd32ce6'},
                             {'type': 'html', 'value': 'SSG 08 | Blood in the Water', 'color': 'eb4b4b'},
                             {'type': 'html', 'value': 'or an Exceedingly Rare Special Item!', 'color': 'ffd700'},
                             {'type': 'html', 'value': ' '}, {'type': 'html', 'value': '', 'color': '00a000'}],
            'tradable': 0,
            'name': 'CS:GO Weapon Case 2',
            'name_color': 'D2D2D2',
            'type': 'Base Grade Container',
            'market_name': 'CS:GO Weapon Case 2',
            'market_hash_name': 'CS:GO Weapon Case 2',
            'commodity': 1,
            'market_tradable_restriction': 7,
            'marketable': 1,
            'tags': [{'category': 'Type',
                      'internal_name': 'CSGO_Type_WeaponCase',
                      'localized_category_name': 'Type',
                      'localized_tag_name': 'Container'},
                     {'category': 'ItemSet',
                      'internal_name': 'set_weapons_ii',
                      'localized_category_name': 'Collection',
                      'localized_tag_name': 'The Arms Deal 2 Collection'},
                     {'category': 'Quality',
                      'internal_name': 'normal',
                      'localized_category_name': 'Category',
                      'localized_tag_name': 'Normal'},
                     {'category': 'Rarity',
                      'internal_name': 'Rarity_Common',
                      'localized_category_name': 'Quality',
                      'localized_tag_name': 'Base Grade',
                      'color': 'b0c3d9'}],
            'market_buy_country_restriction': 'FR',
            'contextid': '2',
            'id': '27620580881',
            'amount': '1'
        }
        """
        self.id: str = data['id']
        self.classid: str = data['classid']
        self.instanceid: str = data['instanceid']
        self.name: str = data['market_hash_name']
        self.tradable: bool = True if data['tradable'] else False
        self.marketable: bool = True if data['marketable'] else False
        self.commodity: bool = True if data['commodity'] else False
        self.amount: int = int(data['amount'])
        self.type: str = data['type']
        self.description: str = ''
        for value in data['descriptions']:
            self.description += f'{value["value"]}\n'
        self.tags: List[Tag] = [Tag(value['localized_category_name'], value['localized_tag_name']) for value in
                                data['tags']]


class Inventory:
    """
    An inventory instance.

    Attributes:
        session - a session instance
        steamid64 - a SteamID64
        appid - an appid of the game
        name - a name of the game
        url - a URL to game
        icon - a URL to game icon
        asset_count - the number of items in the inventory
        contexts - a list of contexts
        response - the response of parsing items from the inventory
        items - a list of parsed items
    """

    def __repr__(self) -> str:
        """Create human-readable class output."""
        attributes = vars(self)
        del attributes['session']
        values = ('{}={!r}'.format(key, value) for key, value in attributes.items())
        return '{}({})'.format(self.__class__.__name__, ', '.join(values))

    def __init__(self, data: Dict[str, Any]) -> None:
        """
        Create an inventory instance from the dictionary.

        :param Dict[str, Any] data: a dictionary containing information about an inventory, e.g.:

        {
            'appid': 753,
            'name': 'Steam',
            'icon': 'https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/apps/753/135dc1ac1cd9763dfc8ad52f4e880d2ac058a36c.jpg',
            'link': 'https://steamcommunity.com/app/753',
            'asset_count': 2308,
            'inventory_logo': 'https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/apps/753/db8ca9e130b7b37685ab2229bf5a288aefc3f0fa.png',
            'trade_permissions': 'FULL',
            'load_failed': 0,
            'store_vetted': '1',
            'owner_only': False,
            'rgContexts': {
                '1': {'asset_count': 5, 'id': '1', 'name': 'Gifts'},
                '6': {'asset_count': 2304, 'id': '6', 'name': 'Community'}
            },
            'session': requests.session(),
            'steamid64': '76561198324466325'
        }
        """
        self.session: requests.session = data['session']
        self.steamid64: int = int(data['steamid64'])
        self.appid: int = int(data['appid'])
        self.name: str = data['name']
        self.url: str = data['link']
        self.icon: str = data['icon']
        self.asset_count: int = data['asset_count']
        self.contexts: List[Context] = [Context(value) for key, value in data['rgContexts'].items()]
        self.response: dict
        self.items: Dict[int, Item] = {}

    def __get_description_key(self, item: dict) -> str:
        """
        Join classid and instanceid.

        :param Dict[str, Any] item: a dictionary containing information about an item
        :return str: {classid}_{instanceid}
        """
        return item['classid'] + '_' + item['instanceid']

    def get_items(self) -> None:
        """Try to parse items from the inventory."""
        items = {}
        for context in self.contexts:
            url = f'{SteamUrl.COMMUNITY_URL}/inventory/{self.steamid64}/{self.appid}/{context.id}/'
            params = {'l': 'english',
                      'count': 5000}
            response_dict = self.session.get(url, params=params).json()
            if response_dict:
                if response_dict['success'] != 1:
                    self.response = {'success': False, 'error': 'Request was unsuccessful'}

                inventory = response_dict.get('assets', [])
                if not inventory:
                    continue

                descriptions = {self.__get_description_key(description): description for description in
                                response_dict['descriptions']}
                merged_items = {}
                for item in inventory:
                    description_key = self.__get_description_key(item)
                    description = copy.copy(descriptions[description_key])
                    item_id = item.get('id') or item['assetid']
                    description['contextid'] = item.get('contextid') or context.id
                    description['id'] = item_id
                    description['amount'] = item['amount']
                    merged_items[int(item_id)] = description

                for key, value in merged_items.items():
                    items[key] = Item(value)

                self.response = {'success': True, 'error': ''}

            else:
                url = f'{SteamUrl.COMMUNITY_URL}/profiles/{self.steamid64}/inventory/#{self.appid}'
                soup = BS(self.session.get(url).text, 'html.parser')
                error = check_error(soup)
                self.response = {'success': False, 'error': error}

        self.items = items


@dataclass
class Group:
    """
    A group instance.

    Attributes:
        name - a name of the group
        url - a URL to the group
        avatar - a URL to the group avatar
        members - the number of members in the group
        in_game - the number of members playing the game
        online - the number of online members
    """
    name: Optional[str]
    url: Optional[str]
    avatar: Optional[str]
    members: int = 0
    in_game: int = 0
    online: int = 0


@dataclass
class Friend:
    """
    A friend instance.

    Attributes:
        url - a URL to the friend profile
        steamid64 - a SteamID64 of the friend
        avatar - a URL to the friend avatar
        nickname - a nickname of the friend
        status - the current status
    """
    url: Optional[str]
    steamid64: Optional[int]
    avatar: Optional[str]
    nickname: Optional[str]
    status: Optional[Status]


class User(AutoRepr):
    """
    A user instance.

    Attributes:
        url - a URL to the profile
        steamid64 - a SteamID64
        private - is the profile private?
        vac_banned - does the user have VAC bans?
        trade_banned - does the user have trade ban?
        community_banned - does the user have community ban?
        created - a timestamp of account creation
        avatar - a URL to the avatar
        nickname - a nickname
        nickname_history - a history of used nicknames
        real_name - a real name
        location - a location
        level - a level
        favorite_badge - an instance of the favorite badge
        recent_activity - a list of instances of recent played games
        status - the current status
        counters - counters (badges, games, screenshots, videos, workshop items, reviews, guides, artworks, groups, friends)
        badges - a list of instances of received badges
        games - a dictionary with instances of available games
        inventories - a dictionary with instances of inventories
        groups - a list of instances of groups in which the user is a member
        friends - a list of instances of friends
    """

    def __init__(self, url: Optional[str] = None, steamid64: int = None, private: bool = False,
                 vac_banned: bool = False, trade_banned: bool = False, community_banned: bool = False, created: int = 0,
                 avatar: Optional[str] = None, nickname: Optional[str] = None, nickname_history: List[str] = None,
                 real_name: Optional[str] = None, location: Optional[Location] = None, level: int = 0,
                 favorite_badge: Optional[Badge] = None, recent_activity: Optional[List[Game]] = None,
                 status: Optional[Status] = None, counters: Counters = None, badges: Optional[List[Badge]] = None,
                 games: Optional[Dict[int, Game]] = None, inventories: Optional[Dict[int, Inventory]] = None,
                 groups: Optional[List[Group]] = None, friends: Optional[List[Friend]] = None) -> None:
        """
        Initialize a class.

        :param Optional[str] url: a URL to the profile
        :param int steamid64: a SteamID64
        :param bool private: is the profile private?
        :param bool vac_banned: does the user have VAC bans?
        :param bool trade_banned: does the user have trade ban?
        :param bool community_banned: does the user have community ban?
        :param int created: a timestamp of account creation
        :param Optional[str] avatar: a URL to the avatar
        :param Optional[str] nickname: a nickname
        :param List[str] nickname_history: a history of used nicknames
        :param Optional[str] real_name: a real name
        :param Optional[Location] location: a location
        :param int level: a level
        :param Optional[Badge] favorite_badge: an instance of the favorite badge
        :param Optional[List[Game]] recent_activity: a list of instances of recent played games
        :param Optional[Status] status: the current status
        :param Counters counters: counters (badges, games, screenshots, videos, workshop items, reviews, guides, artworks, groups, friends)
        :param Optional[List[Badge]] badges: a list of instances of received badges
        :param Optional[Dict[int, Game]] games: a dictionary with instances of available games
        :param Optional[Dict[int, Inventory]] inventories: a dictionary with instances of inventories
        :param Optional[List[Group]] groups: a list of instances of groups in which the user is a member
        :param Optional[List[Friend]] friends: a list of instances of friends
        """
        self.url: Optional[str] = url
        self.steamid64: Optional[int] = steamid64
        self.private: bool = private
        self.vac_banned = vac_banned
        self.trade_banned = trade_banned
        self.community_banned = community_banned
        self.created: int = created
        self.avatar: Optional[str] = avatar
        self.nickname: Optional[str] = nickname
        if not nickname_history:
            self.nickname_history = []
        else:
            self.nickname_history = nickname_history

        self.real_name: Optional[str] = real_name
        self.location: Optional[Location] = location
        self.level: int = level
        self.favorite_badge: Optional[Badge] = favorite_badge
        self.recent_activity: Optional[List[Game]] = recent_activity
        self.status: Optional[Status] = status
        self.counters: Optional[Counters] = counters
        self.badges: Optional[List[Badge]] = badges
        self.games: Optional[Dict[int, Game]] = games
        self.inventories: Optional[Dict[int, Inventory]] = inventories
        self.groups: Optional[List[Group]] = groups
        self.friends: Optional[List[Friend]] = friends


class Profile:
    """
    This class allows you to interact with the profiles.

    Attributes:
        client - the client instance
        req_get - an alias of 'request.session.get'
        url - a URL to the profile
    """

    def __init__(self, client) -> None:
        """
        Initialize a class.

        :param client: the client instance
        """
        self.client = client
        self.req_get = self.client.session.get
        self.url = None

    def __get_private(self, soup: BS) -> bool:
        """
        Check if a profile is private.

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :return bool: True if the profile is private
        """
        try:
            return bool(soup.find('div', class_='profile_private_info') is not None)

        except:
            pass

    def __get_creation_time(self, soup: BS, private: Optional[bool] = None) -> Optional[int]:
        """
        Get a timestamp of account creation.

        :param BeautifulSoup soup: the BeautifulSoup element of the 'Years of Service' badge
        :param Optional[bool] private: is the profile private?
        :return Optional[int]: a timestamp of account creation
        """
        try:
            if private:
                return None

            year = int(soup.find('div', class_='badge_description').get_text(strip=True)[-5: -1])
            tmp: List[str] = soup.find('div', class_='badge_info_unlocked').get_text(strip=True).replace('Unlocked ',
                                                                                                         '').split(' ')
            return int(datetime.strptime(f'{year} {tmp[0]:0>2} {tmp[1]} {tmp[-1].upper():0>7}',
                                         '%Y %d %b %I:%M%p').timestamp())

        except:
            pass

    def __get_avatar(self, soup: BS) -> str:
        """
        Get a URL to avatar.

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :return str: a URL to avatar
        """
        try:
            return str(soup.find('div', class_='playerAvatarAutoSizeInner').find('img')['src'])

        except:
            pass

    def __get_nickname(self, soup: BS) -> str:
        """
        Get a nickname.

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :return str: a nickname
        """
        try:
            return str(soup.find('span', class_='actual_persona_name').text)

        except:
            pass

    def __get_nickname_history(self, private: Optional[bool] = None) -> Optional[List[str]]:
        """
        Get a history of used nicknames.

        :param Optional[bool] private: is the profile private?
        :return Optional[List[str]]: a history of used nicknames
        """
        try:
            if private:
                return None

            nickname_history: List[str] = []
            data: List[Dict[str, str]] = json.loads(requests.get(f'{self.url}ajaxaliases/').text)
            for alias in data:
                nickname_history.append(alias['newname'])
            return nickname_history

        except:
            pass

    def __get_real_name(self, soup: BS, private: Optional[bool] = None) -> Optional[str]:
        """
        Get a real name.

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :param Optional[bool] private: is the profile private?
        :return Optional[str]: a real name
        """
        try:
            if private:
                return None

            element = soup.find('div', class_='header_real_name ellipsis')
            if element is None or element.find('bdi').text == '':
                return None
            return element.find('bdi').text

        except:
            pass

    def __get_location(self, soup: BS, private: Optional[bool] = None) -> Optional[Location]:
        """
        Get a location.

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :param Optional[bool] private: is the profile private?
        :return Optional[Location]: a location
        """
        try:
            if private:
                return None

            element = soup.find('div', class_='header_real_name ellipsis')
            if element is None or element.find('img') is None:
                return None
            return Location(element.find('img')['src'], element.contents[-1].strip())

        except:
            pass

    def __get_level(self, soup: BS, private: Optional[bool] = None) -> int:
        """
        Get a level.

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :param Optional[bool] private: is the profile private?
        :return int: a level
        """
        try:
            if private:
                return False

            element = soup.find('span', class_='friendPlayerLevelNum')
            return extract_int(element.text)

        except:
            pass

    def __get_favorite_badge(self, soup: BS, private: Optional[bool] = None) -> Optional[Badge]:
        """
        Get an instance of the favorite badge.

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :param Optional[bool] private: is the profile private?
        :return Optional[Badge]: an instance of the favorite badge
        """
        try:
            if private:
                return None

            element = soup.find('a', class_='favorite_badge')
            if element is None:
                return None

            badge_url = element.attrs['href']
            bs = BS(self.req_get(badge_url).text, 'html.parser')
            badge = Badge(bs)
            badge.url = badge_url

            return badge

        except:
            pass

    def __get_recent_activity(self, soup: BS, private: Optional[bool] = None) -> Optional[List[Game]]:
        """
        Get a list of instances of recent played games.

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :param Optional[bool] private: is the profile private?
        :return Optional[List[Game]]: a list of instances of recent played games
        """
        try:
            if private:
                return None

            games: List[Game] = []
            recent_games: List[BS] = soup.find_all('div', class_='recent_game_content')
            for game_element in recent_games:
                game_dict = {}
                appid = int(
                    game_element.find('div', class_='game_name').find('a', class_='whiteLink').attrs['href'].split('/')[
                        -1])
                game_dict['appid'] = appid
                game_dict['name'] = game_element.find('div', class_='game_name').find('a', class_='whiteLink').get_text(
                    strip=True)
                game_dict['app_type'] = ''
                game_dict['logo'] = \
                    game_element.find('div', class_='game_info_cap').find('img', class_='game_capsule').attrs['src']
                game_dict['friendlyURL'] = appid
                game_dict['availStatLinks'] = {'achievements': None, 'global_achievements': None, 'stats': None,
                                               'gcpd': None, 'leaderboards': None, 'global_leaderboards': None}
                tmp = game_element.find('div', class_='game_info_details').text.split()
                game_dict['hours_forever'] = tmp[0]
                if len(tmp) == 10:
                    last_played = int(
                        datetime.strptime(f'{tmp[-1]} {tmp[-3]:0>2} {tmp[-2][:-1]}', '%Y %d %b').timestamp())

                elif len(tmp) == 9:
                    last_played = int(
                        datetime.strptime(f'{datetime.now().year} {tmp[-2]:0>2} {tmp[-1]}', '%Y %d %b').timestamp())

                else:
                    last_played = 0

                game_dict['last_played'] = last_played
                games.append(Game(game_dict))

            return games

        except:
            pass

    def __get_status(self, soup: BS, private: Optional[bool] = None) -> Optional[Status]:
        """
        Get the current status.

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :param Optional[bool] private: is the profile private?
        :return Optional[Status]: the current status
        """
        try:
            if private:
                return None

            main_element = soup.find('div', class_='profile_in_game_header')
            desc_element = soup.find('div', class_='profile_in_game_name')
            status: str = main_element.text.replace('Currently ', '').lower()
            last: Optional[str] = None
            game: Optional[str] = None
            if desc_element:
                if status == 'offline':
                    last = desc_element.text.replace('Last Online ', '').lower()
                elif status == 'in-game':
                    game = desc_element.text
            return Status(status, game, last)

        except:
            pass

    def __get_counters(self, soup: BS, private: Optional[bool] = None) -> Optional[Counters]:
        """
        Get counters (badges, games, screenshots, videos, workshop items, reviews, guides, artworks, groups, friends).

        :param BeautifulSoup soup: the BeautifulSoup element of the main page
        :param Optional[bool] private: is the profile private?
        :return Optional[Counters]: a counter instance
        """
        try:
            if private:
                return None

            counters: Dict[str, int] = {'badges': 0, 'games': 0, 'screenshots': 0, 'videos': 0, 'workshopitems': 0,
                                        'reviews': 0, 'guides': 0, 'artworks': 0, 'groups': 0, 'friends': 0}
            label_elements: List[BS] = soup.find_all('span', class_='count_link_label')
            counter_elements: List[BS] = soup.find_all('span', class_='profile_count_link_total')
            for i, counter_element in enumerate(counter_elements):
                key = label_elements[i].get_text(strip=True).lower()
                if key == 'artwork':
                    counters['artworks'] = int(counter_element.get_text(strip=True))
                elif key != 'inventory':
                    counters[key] = int(counter_element.get_text(strip=True))

            return Counters(**counters)

        except:
            logging.exception('_get_counters')
            pass

    def get_profile_url(self, s64_or_id: str or int) -> str:
        """
        Convert a SteamID64, a custom ID or a profile URL to the profile URL.

        :param str or int s64_or_id: a SteamID64, a custom ID or a profile URL
        :return str: the profile URL
        """
        try:
            s64_or_id = str(s64_or_id)
            if 'https://steamcommunity.com/' in s64_or_id:
                if s64_or_id[-1] != '/':
                    s64_or_id += '/'
                return s64_or_id
            elif len(s64_or_id) == 17:
                return SteamUrl.COMMUNITY_URL + f'/profiles/{s64_or_id}/'
            else:
                return SteamUrl.COMMUNITY_URL + f'/id/{s64_or_id}/'

        except:
            pass

    def get_steamid64(self, s64_or_id: str or int = None) -> Optional[int]:
        """
        Parse SteamID64 of the profile.

        :param str or int s64_or_id: a SteamID64, a custom ID or a profile URL
        :return Optional[int]: the profile URL
        """
        try:
            self.url = self.get_profile_url(s64_or_id)
            soup = BS(self.req_get(f'{self.url}?xml=1').content, 'xml')
            if not soup:
                return None

            steamid64 = int(soup.find('steamID64').text)
            if steamid64:
                return steamid64

        except:
            pass

    def get_bans(self, s64_or_id: str or int = None) -> Dict[str, Optional[bool]]:
        """
        Parse the bans present in the user.

        :param str or int s64_or_id: a SteamID64, a custom ID or a profile URL
        :return Dict[str, Optional[bool]]: the dictionary containing information about bans
        """
        bans = {'trade': None, 'vac': None, 'community': None}
        try:
            self.url = self.get_profile_url(s64_or_id)
            soup = BS(self.req_get(f'{self.url}?xml=1').content, 'xml')
            if soup:
                bans['vac'] = True if int(soup.find('vacBanned').text) else False
                bans['trade'] = False if soup.find('tradeBanState').text == 'None' else True
                bans['community'] = True if int(soup.find('isLimitedAccount').text) else False

        except:
            pass

        finally:
            return bans

    def get_badges(self, s64_or_id: Optional[str or int] = None, soup: Optional[BS] = None,
                   private: Optional[bool] = None) -> Optional[List[Badge]]:
        """
        Get a list of instances of received badges.

        :param Optional[str or int] s64_or_id: a SteamID64, a custom ID or a profile URL
        :param Optional[BeautifulSoup] soup: the BeautifulSoup element of the badges page
        :param Optional[bool] private: is the profile private?
        :return Optional[List[Badge]]: a list of instances of received badges
        """
        try:
            if not soup:
                self.url = self.get_profile_url(s64_or_id)
                private = self.__get_private(BS(self.req_get(self.url).text, 'html.parser'))
                soup = BS(self.req_get(f'{self.url}badges/').text, 'html.parser')

            if private:
                return None

            badges: List[Badge] = []
            elements: List[Any] = soup.find_all('div', class_='badge_row is_link')
            for element in elements:
                badges.append(Badge(element))
            return badges

        except:
            pass

    def get_games(self, s64_or_id: Optional[str or int] = None, soup: Optional[BS] = None,
                  private: Optional[bool] = None) -> Optional[Dict[int, Game]]:
        """
        Get a dictionary with instances of available games.

        :param Optional[str or int] s64_or_id: a SteamID64, a custom ID or a profile URL
        :param Optional[BeautifulSoup] soup: the BeautifulSoup element of the games page
        :param Optional[bool] private: is the profile private?
        :return Optional[Dict[int, Game]]: a dictionary with instances of available games
        """
        try:
            if not soup:
                self.url = self.get_profile_url(s64_or_id)
                private = self.__get_private(BS(self.req_get(self.url).text, 'html.parser'))
                soup = BS(self.req_get(f'{self.url}games/?tab=all').text, 'html.parser')

            if private:
                return None

            games: Dict[int, Game] = {}
            try:
                text_dict = text_between(soup.find_all('script')[-1].get_text(strip=True), 'var rgGames = ', ';')
            except:
                return None

            json_data = json.loads(text_dict)
            for game in json_data:
                games[game['appid']] = Game(game)

            return games

        except:
            pass

    def get_inventories(self, s64_or_id: Optional[str or int] = None, soup: Optional[BS] = None,
                        private: Optional[bool] = None,
                        appids: Optional[List[int]] = None) -> Optional[Dict[int, Inventory]]:
        """
        Get a dictionary with instances of inventories.

        :param Optional[str or int] s64_or_id: a SteamID64, a custom ID or a profile URL
        :param Optional[BeautifulSoup] soup: the BeautifulSoup element of the inventory page
        :param Optional[bool] private: is the profile private?
        :param Optional[List[int]] appids: a list of appid of games in which you need to parse items (items aren't parsed)
        :return Optional[Dict[int, Inventory]]: a dictionary with instances of inventories
        """
        try:
            if not soup:
                self.url = self.get_profile_url(s64_or_id)
                private = self.__get_private(BS(self.req_get(self.url).text, 'html.parser'))
                soup = BS(self.req_get(f'{self.url}inventory/').text, 'html.parser')

            if private:
                return None

            error = check_error(soup)
            if error:
                raise exceptions.ProfileUnavailable(error)

            inventories: Dict[int, Inventory] = {}
            javascript = soup.find_all('script')[-1].get_text(strip=True)
            try:
                text_dict = text_between(javascript, 'g_rgAppContextData = ', ';')
                steamid64 = text_between(javascript, "UserYou.SetSteamId( '", "' );")
            except:
                return None

            json_data = json.loads(text_dict)
            for key, value in json_data.items():
                value['session'] = self.client.session
                value['steamid64'] = steamid64
                inventories[int(key)] = Inventory(value)

            if appids:
                for appid in appids:
                    if appid in inventories:
                        inventories[appid].get_items()

            return inventories

        except:
            logging.exception('error')
            pass

    def get_groups(self, s64_or_id: Optional[str or int] = None, soup: Optional[BS] = None,
                   private: Optional[bool] = None) -> Optional[List[Group]]:
        """
        Get a list of instances of groups in which the user is a member.

        :param Optional[str or int] s64_or_id: a SteamID64, a custom ID or a profile URL
        :param Optional[BeautifulSoup] soup: the BeautifulSoup element of the groups page
        :param Optional[bool] private: is the profile private?
        :return Optional[List[Group]]: a list of instances of groups in which the user is a member
        """
        try:
            if not soup:
                self.url = self.get_profile_url(s64_or_id)
                private = self.__get_private(BS(self.req_get(self.url).text, 'html.parser'))
                soup = BS(self.req_get(f'{self.url}groups/').text, 'html.parser')

            if private:
                return None

            groups: List[Group] = []
            group_elements: List[BS] = soup.find_all('div', class_='group_block invite_row')
            for group_element in group_elements:
                title = group_element.find('a', class_='linkTitle')
                name = title.get_text(strip=True)
                url = title.attrs['href']
                avatar = group_element.find('div', class_='avatarMedium').find('img').attrs['src']
                members = extract_int(
                    group_element.find('a', class_='groupMemberStat linkStandard').get_text(strip=True))
                in_game = extract_int(
                    group_element.find('span', class_='groupMemberStat membersInGame').get_text(strip=True))
                online = extract_int(
                    group_element.find('span', class_='groupMemberStat membersOnline').get_text(strip=True))

                groups.append(Group(name=name, url=url, avatar=avatar, members=members, in_game=in_game, online=online))

            return groups

        except:
            pass

    def get_friends(self, s64_or_id: Optional[str or int] = None, soup: Optional[BS] = None,
                    private: Optional[bool] = None) -> Optional[List[Friend]]:
        """
        Get a list of instances of friends.

        :param Optional[str or int] s64_or_id: a SteamID64, a custom ID or a profile URL
        :param Optional[BeautifulSoup] soup: the BeautifulSoup element of the friends page
        :param Optional[bool] private: is the profile private?
        :return Optional[List[Friend]]: a list of instances of friends
        """
        try:
            if not soup:
                self.url = self.get_profile_url(s64_or_id)
                private = self.__get_private(BS(self.req_get(self.url).text, 'html.parser'))
                soup = BS(self.req_get(f'{self.url}friends/').text, 'html.parser')

            if private:
                return None

            friends: List[Friend] = []
            friend_elements = soup.select('div[class^="selectable friend_block_v2 persona"]')
            for friend_element in friend_elements:
                url = friend_element.find('a', class_='selectable_overlay').attrs['href']
                steamid64 = int(friend_element.attrs['data-steamid'])
                avatar = friend_element.find('img').attrs['src']
                texts = friend_element.find('div', class_='friend_block_content').text.split('\n\n')
                nickname = texts[0]
                status = friend_element.attrs['class'][-1]
                if status == 'in-game':
                    game = texts[1].strip()

                else:
                    game = None

                status = Status(status, game, None)
                friend = Friend(url=url, steamid64=steamid64, avatar=avatar, nickname=nickname, status=status)
                friends.append(friend)

            return friends

        except:
            pass

    def get_profile(self, s64_or_id: str or int, get_badges: bool = False, get_games: bool = False,
                    get_inventories: bool = False, get_groups: bool = False, get_friends: bool = False) -> Optional[
        User]:
        """
        Get an instance with information about the profile.

        :param str or int s64_or_id: a SteamID64, a custom ID or a profile URL
        :param bool get_badges: is it necessary to get badges?
        :param bool get_games: is it necessary to get games?
        :param bool get_inventories: is it necessary to get inventories?
        :param bool get_groups: is it necessary to get groups?
        :param bool get_friends: is it necessary to get friends?
        :return Optional[User]: an instance with information about the profile
        """
        user = User()
        try:
            self.url = self.get_profile_url(s64_or_id)
            soup_main = BS(self.req_get(self.url).text, 'html.parser')
            error = check_error(soup_main)
            if error:
                raise exceptions.ProfileUnavailable(error)

            soup_date = BS(self.req_get(f'{self.url}badges/1/').text, 'html.parser')

            user.url = self.url
            user.steamid64 = self.get_steamid64(s64_or_id)
            user.private = private = self.__get_private(soup_main)

            bans = self.get_bans(s64_or_id)
            user.vac_banned = bans['vac']
            user.trade_banned = bans['trade']
            user.community_banned = bans['community']

            user.created = self.__get_creation_time(soup_date, private)
            user.avatar = self.__get_avatar(soup_main)
            user.nickname = self.__get_nickname(soup_main)
            user.nickname_history = self.__get_nickname_history(private)
            user.real_name = self.__get_real_name(soup_main, private)
            user.location = self.__get_location(soup_main, private)
            user.level = self.__get_level(soup_main, private)
            user.favorite_badge = self.__get_favorite_badge(soup_main, private)
            user.recent_activity = self.__get_recent_activity(soup_main, private)
            user.status = self.__get_status(soup_main)
            user.counters = self.__get_counters(soup_main, private)
            if get_badges:
                soup_badges = BS(self.req_get(f'{self.url}badges/').text, 'html.parser')
                user.badges = self.get_badges(soup=soup_badges, private=private)

            if get_games:
                soup_games = BS(self.req_get(f'{self.url}games/?tab=all').text, 'html.parser')
                user.games = self.get_games(soup=soup_games, private=private)

            if get_inventories:
                soup_inventory = BS(self.req_get(f'{self.url}inventory/').text, 'html.parser')
                user.inventory = self.get_inventories(soup=soup_inventory, private=private)

            if get_groups:
                soup_friends = BS(self.req_get(f'{self.url}groups/').text, 'html.parser')
                user.groups = self.get_groups(soup=soup_friends, private=private)

            if get_friends:
                soup_groups = BS(self.req_get(f'{self.url}friends/').text, 'html.parser')
                user.friends = self.get_friends(soup=soup_groups, private=private)

        except:
            pass

        finally:
            return user


def check_error(soup: BS) -> Optional[str]:
    """
    Check for an error on the page.

    :param BeautifulSoup soup: the BeautifulSoup element of the page
    :return Optional[str]: an error text
    """
    error = soup.find('div', class_='error_ctn')
    if error:
        return error.find('div', id='message').find('h3').get_text(strip=True)
