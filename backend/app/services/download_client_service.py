import logging
import httpx

logger = logging.getLogger(__name__)

class DownloadClientError(Exception):
    pass

class QBittorrentClient:
    def __init__(self, url: str, username: str = '', password: str = '', category: str = 'codex'):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.category = category
        self._sid: str | None = None

    async def _login(self, client: httpx.AsyncClient) -> None:
        if not self.username:
            return
        resp = await client.post(f'{self.url}/api/v2/auth/login', data={'username': self.username, 'password': self.password})
        if resp.status_code != 200 or resp.text != 'Ok.':
            raise DownloadClientError(f'qBittorrent login failed: {resp.text}')
        self._sid = resp.cookies.get('SID')

    async def test_connection(self) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            await self._login(client)
            resp = await client.get(f'{self.url}/api/v2/app/version', cookies={'SID': self._sid} if self._sid else {})
            resp.raise_for_status()
            return {'status': 'ok', 'version': resp.text.strip()}

    async def add_torrent(self, torrent_url: str, save_path: str | None = None) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            await self._login(client)
            data = {'urls': torrent_url, 'category': self.category}
            if save_path:
                data['savepath'] = save_path
            resp = await client.post(f'{self.url}/api/v2/torrents/add', data=data, cookies={'SID': self._sid} if self._sid else {})
            if resp.status_code != 200 or resp.text != 'Ok.':
                raise DownloadClientError(f'Failed to add torrent: {resp.text}')
            return 'ok'

class SABnzbdClient:
    def __init__(self, url: str, api_key: str, category: str = 'codex'):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.category = category

    async def test_connection(self) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f'{self.url}/api', params={'mode': 'version', 'apikey': self.api_key, 'output': 'json'})
            resp.raise_for_status()
            data = resp.json()
            return {'status': 'ok', 'version': data.get('version', 'unknown')}

    async def add_nzb(self, nzb_url: str, name: str = '') -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            params = {'mode': 'addurl', 'name': nzb_url, 'cat': self.category, 'apikey': self.api_key, 'output': 'json'}
            if name:
                params['nzbname'] = name
            resp = await client.get(f'{self.url}/api', params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data.get('status'):
                raise DownloadClientError(f'SABnzbd failed: {data}')
            return data.get('nzo_ids', ['unknown'])[0]

async def get_client_from_settings(db):
    from app.services.settings_service import get_setting
    # Check qBittorrent
    qbit_enabled = await get_setting(db, 'downloadclient.qbittorrent.enabled')
    if qbit_enabled == 'true':
        url = await get_setting(db, 'downloadclient.qbittorrent.url') or ''
        username = await get_setting(db, 'downloadclient.qbittorrent.username') or ''
        password = await get_setting(db, 'downloadclient.qbittorrent.password') or ''
        category = await get_setting(db, 'downloadclient.qbittorrent.category') or 'codex'
        return QBittorrentClient(url=url, username=username, password=password, category=category)
    # Check SABnzbd
    sab_enabled = await get_setting(db, 'downloadclient.sabnzbd.enabled')
    if sab_enabled == 'true':
        url = await get_setting(db, 'downloadclient.sabnzbd.url') or ''
        api_key = await get_setting(db, 'downloadclient.sabnzbd.api_key') or ''
        category = await get_setting(db, 'downloadclient.sabnzbd.category') or 'codex'
        return SABnzbdClient(url=url, api_key=api_key, category=category)
    return None
