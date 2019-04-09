import pickle
import re

import requests
from django.utils import timezone

from Harvest.throttling import DatabaseSyncedThrottler
from Harvest.utils import get_filename_from_content_disposition, control_transaction, get_logger
from plugins.redacted.exceptions import RedactedTorrentNotFoundException, RedactedRateLimitExceededException, \
    RedactedException, RedactedLoginException, RedactedUploadException
from plugins.redacted.models import RedactedThrottledRequest, RedactedClientConfig
from plugins.redacted.utils import extract_upload_errors

logger = get_logger(__name__)

HEADERS = {
    'Content-type': 'application/x-www-form-urlencoded',
    'Accept-Charset': 'utf-8',
    'User-Agent': 'Harvest'
}

DOMAIN = 'redacted.ch'


class RedactedClient:
    UPLOAD_TIMEOUT = 60

    def __init__(self, timeout=30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers = HEADERS
        self.throttler = DatabaseSyncedThrottler(RedactedClientConfig, RedactedThrottledRequest, 5, 10)
        self.config = None

    @property
    def login_url(self):
        return 'https://{}/login.php'.format(DOMAIN)

    @property
    def ajax_url(self):
        return 'https://{}/ajax.php'.format(DOMAIN)

    @property
    def torrent_file_url(self):
        return 'https://{}/torrents.php'.format(DOMAIN)

    @property
    def log_url(self):
        return 'https://{}/log.php'.format(DOMAIN)

    @property
    def upload_url(self):
        return 'https://{}/upload.php'.format(DOMAIN)

    def _login(self):
        logger.debug('Attempting login with username {}.', self.config.username)

        if self.config.last_login_failed:
            logger.debug('Refusing to retry failed login attempt.')
            raise RedactedException('Refusing to retry failed login attempt. Check connection settings manually.')

        # Mark login as failed in order to prevent future tries if the code crashes
        self.config.last_login_failed = True
        self.config.save()

        data = {
            'username': self.config.username,
            'password': self.config.password,
            'keeplogged': 1,
            'login': 'Login',
        }
        # Login is not subject to the normal API rate limiting
        r = self.session.post(self.login_url, data=data, allow_redirects=False, timeout=self.timeout)
        if r.status_code != 302:
            logger.debug('Login failed, returned status {}.', r.status_code)

            if '<form class="auth_form" name="2fa" id="2fa"' in r.text:
                logger.debug('Login failed: 2FA unsupported.')
                raise RedactedLoginException('2FA is enabled on your account, unable to login.')
            elif 'Your username or password was incorrect.' in r.text:
                logger.debug('Login failed: incorrect username/password.')
                raise RedactedLoginException('Incorrect Redact username/password.')
            else:
                logger.debug('Login failed: unknown reason.')
                raise RedactedLoginException('Unknown error logging in.')

        # Working outside of the normal __request cycling since this is a special case
        self.throttler.throttle_request(url='{}?action=index')
        index_response = self.session.get(
            self.ajax_url,
            params={'action': 'index'},
            allow_redirects=False,
            timeout=self.timeout,
        )
        if index_response.status_code == 200:
            self.authkey = index_response.json()['response']['authkey']
            self.passkey = index_response.json()['response']['passkey']
        else:
            raise RedactedLoginException('Index request after fresh login returned {}: {}'.format(
                index_response.status_code, index_response.text))

        self.config.last_login_failed = False
        self.config.login_datetime = timezone.now()
        self.config.cookies = pickle.dumps([c for c in self.session.cookies])
        self.config.authkey = self.authkey
        self.config.passkey = self.passkey
        self.config.save()

        logger.info('Login succeeded with username {}, credentials stored.', self.config.username)

    def __request(self, method, url, **kwargs):
        logger.info('Requesting {} {}.', method, url)
        kwargs.setdefault('timeout', self.timeout)

        def get_request_kwargs():
            result = {
                'method': method,
                'url': url,
                **kwargs,
            }

            if 'params' in result:
                params = dict(kwargs['params'])
                result['params'] = params
                if 'auth' in params and params['auth'] is None:
                    params['auth'] = self.config.authkey
                if 'authkey' in params and params['authkey'] is None:
                    params['authkey'] = self.config.authkey
                if 'torrent_pass' in params and params['torrent_pass'] is None:
                    params['torrent_pass'] = self.config.passkey

            return result

        if self.config.cookies:
            logger.debug('Found cached login credentials.')

            self.session.cookies.clear()
            for cookie in pickle.loads(self.config.cookies):
                self.session.cookies.set_cookie(cookie)

            self.throttler.throttle_request(url='{} {}'.format(method, url))
            resp = self.session.request(**get_request_kwargs())

            # If not logged in, try to log in
            if resp.status_code == 302:
                logger.debug('Login credentials did not work, attempting login.')

                # Clear login credentials that didn't work
                self.config.clear_login_data()
                self.config.save()

                self._login()

                self.throttler.throttle_request(url='{} {}'.format(method, url))
                resp = self.session.request(**get_request_kwargs())
                resp.raise_for_status()
        else:
            logger.debug('No login credentials found, attempting fresh login.')
            self._login()

            self.throttler.throttle_request(url='{} {}'.format(method, url))
            resp = self.session.request(**get_request_kwargs())
            if resp.status_code == 302:
                raise RedactedException('API returned redirect after fresh login')
            resp.raise_for_status()

        return resp

    @control_transaction()
    def _request(self, method, url, **kwargs):
        try:
            self.config = RedactedClientConfig.objects.using('control').select_for_update().get()
        except RedactedClientConfig.DoesNotExist:
            raise RedactedException('Client config is missing. Please configure your account through settings.')

        try:
            return self.__request(method, url, **kwargs)
        except RedactedException:
            raise
        except Exception as ex:
            raise RedactedException('Unable to perform Redacted request: {}'.format(ex))
        finally:
            self.config = None

    def request_ajax(self, action, **kwargs):
        params = {
            'action': action,
            'auth': None,
        }
        params.update(kwargs)

        resp = self._request('GET', self.ajax_url, params=params, allow_redirects=False)

        try:
            data = resp.json()
            if data['status'] != 'success':
                if data['error'] == 'bad id parameter':
                    raise RedactedTorrentNotFoundException()
                elif data['error'] == 'rate limit exceeded':
                    raise RedactedRateLimitExceededException(data)
                raise RedactedException('Unknown Redacted API error: {}'.format(data))
            return data['response']
        except ValueError:
            if action == 'torrentlog' and resp.content == 'no payload data (empty result set)':
                return {'status': 'success', 'response': []}
            raise RedactedException('Error decoding JSON. Response text: {}'.format(
                resp.text[:30] + '...' if len(resp.text) > 27 else resp.text))

    def get_index(self):
        return self.request_ajax('index')

    def get_torrent(self, torrent_id):
        return self.request_ajax('torrent', id=torrent_id)

    def get_torrent_by_info_hash(self, info_hash):
        return self.request_ajax('torrent', hash=info_hash.upper())

    def get_torrent_group(self, group_id):
        return self.request_ajax('torrentgroup', id=group_id)

    def get_torrent_file(self, torrent_id):
        """Downloads the torrent at torrent_id using the authkey and passkey"""

        params = {
            'action': 'download',
            'id': torrent_id,
            'authkey': None,
            'torrent_pass': None,
        }

        r = self._request('GET', self.torrent_file_url, params=params, allow_redirects=False)
        if r.status_code == 200 and 'application/x-bittorrent' in r.headers['content-type'].lower():
            filename = get_filename_from_content_disposition(r.headers['content-disposition'])
            return filename, r.content
        else:
            raise RedactedException('Unable to fetch torrent - received {} {}'.format(
                r.status_code, r.headers['content-type']))

    def get_site_log(self, page):
        r = self._request('GET', self.log_url, params={'page': page}, allow_redirects=False)
        if r.status_code != 200:
            raise RedactedException('Log.php returned status code {}.'.format(200))
        return r.text

    def get_announce(self):
        r = self._request('GET', self.upload_url, allow_redirects=False)
        if r.status_code != 200:
            raise RedactedException('Upload.php returned status code {}'.format(200))
        match = re.search(r'value\=\"([^"]*/announce)\"', r.text)
        if not match:
            raise RedactedException('Unable to match announce url in HTML')
        return match.group(1)

    def perform_upload(self, payload, torrent_file):
        index = self.get_index()
        payload['auth'] = index['authkey']

        r = self._request(
            'POST',
            self.upload_url,
            data=payload,
            files={
                'file_input': ('torrent.torrent', torrent_file),
            },
            headers={
                'Content-Type': None,
            },
            timeout=self.UPLOAD_TIMEOUT,
        )
        if r.url == self.upload_url:
            try:
                errors = extract_upload_errors(r.text)
            except Exception:
                errors = 'Unable to automatically detect error. Check HTML file.'
            raise RedactedUploadException(r.text, errors)
