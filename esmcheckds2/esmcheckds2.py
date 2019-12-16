# -*- coding: utf-8 -*-

import base64
import csv
import json
import os
import re
import requests
import sys
import urllib.parse as urlparse
from io import StringIO
from configparser import ConfigParser


requests.packages.urllib3.disable_warnings()


class Config(object):
    """
    Find the config settings which include:

     - esmhost
     - esmuser
     - esmpass
    """

    def __init__(self):
        """
        Initialize a Config instance.
        """
        self.config = ConfigParser()
        self.find_ini()
        self.validate_config()

    def find_ini(self):
        """
        Attempt to locate a .mfe_saw.ini file
        """
        module_dir = os.path.dirname(sys.modules[__name__].__file__)

        if 'APPDATA' in os.environ:
            conf_path = os.environ['APPDATA']
        elif 'XDG_CONFIG_HOME' in os.environ:
            conf_path = os.environ['XDG_CONFIG_HOME']
        elif 'HOME' in os.environ:
            conf_path = os.path.join(os.environ['HOME'])
        else:
            conf_path = None

        paths = [os.path.join(module_dir, '.mfe_saw.ini'), '.mfe_saw.ini']
        if conf_path is not None:
            paths.insert(1, os.path.join(conf_path, '.mfe_saw.ini'))
        self.config.read(paths)

    def validate_config(self):
        if not self.config:
            raise FileNotFoundError('.mfe_saw.ini file not found.')
        self.check_esm_section()

    def check_esm_section(self):
        if not self.config.has_section('esm'):
            print('[esm] section is required in .mfe_saw.ini.')
            sys.exit(1)

        if not self.config.has_option('esm', 'esmhost'):
            print('esmhost required for [esm] section in .mfe_saw.ini.')
            sys.exit(1)

        if not self.config.has_option('esm', 'esmuser'):
            print('esmuser required for [esm] section in .mfe_saw.ini.')
            sys.exit(1)

        if not self.config.has_option('esm', 'esmpass'):
            print('esmpass required for [esm] section in .mfe_saw.ini.')
            sys.exit(1)

        self.__dict__.update(self.config['esm'])

    def _find_envs(self):
        """
        Builds a dict with env variables set starting with 'ESM'.
        """
        _envs = {kenv: venv
                 for kenv, venv in os.environ.items()
                 if kenv.startswith('esm')}
        self.__dict__.update(_envs)

    def __getitem__(self, item):
        return self.__dict__[item]


class ESM(object):
    """
    """

    def __init__(self, cfg, api_ver='v2'):
        """
        """
        try:
            hostname = cfg['esmhost']
            username = cfg['esmuser']
            password = cfg['esmpass']
        except TypeError:
            hostname = cfg.esmhost
            username = cfg.esmuser
            password = cfg.esmpass

        self.api_ver = api_ver

        if self.api_ver == 'v2':
            self._base_url = 'https://{}/rs/esm/v2/'.format(hostname)
        else:
            self._base_url = 'https://{}/rs/esm/'.format(hostname)
        self._int_url = 'https://{}/ess'.format(hostname)

        _b64_user = base64.b64encode(username.encode('utf-8')).decode()
        _b64_passwd = base64.b64encode(password.encode('utf-8')).decode()
        self._params = {"username": _b64_user,
                        "password": _b64_passwd,
                        "locale": "en_US",
                        "os": "Win32"}
        self._headers = {'Content-Type': 'application/json'}

        self._login()

    def _login(self):
        """
        Log into the ESM
        """
        method = 'login'
        data = self._params
        resp = self.post(method, data=data,
                         headers=self._headers, raw=True)

        if resp.status_code in [400, 401]:
            print('Invalid username or password for the ESM')
            sys.exit(1)
        elif 402 <= resp.status_code <= 600:
            print('ESM Login Error:', resp.text)
            sys.exit(1)

        self._headers['Cookie'] = resp.headers.get('Set-Cookie')
        self._headers['X-Xsrf-Token'] = resp.headers.get('Xsrf-Token')

    def logout(self):
        """
        Logout of the ESM.
        """
        method = self._base_url + 'logout'
        self._delete(method)

    def time(self):
        """
        Returns:
            str. ESM time (GMT).

        Example:
            '2017-07-06T12:21:59.0+0000'
        """
        method = 'essmgtGetESSTime'
        return self.post(method)

    def _delete(self, url, headers=None, verify=False):
        if not headers:
            headers = self._headers
        try:
            return requests.delete(url, headers=headers, verify=verify)
        except requests.exceptions.ConnectionError:
            print("Unable to connect to ESM: {}".format(url))
            sys.exit(1)

    def post(self, method, data=None, callback=None, raw=None,
             headers=None, verify=False):

        if method.isupper():
            url = self._int_url
            data = self._format_params(method, **data)
        else:
            url = self._base_url + method
            if data:
                data = json.dumps(data)

        resp = self._post(url, data=data,
                          headers=self._headers, verify=verify)

        if raw:
            return resp

        if 200 <= resp.status_code <= 300:
            try:
                resp = resp.json()
                if isinstance(resp, list):
                    return resp

                if resp.get('value'):
                    resp = resp.get('value')
                elif resp.get('return'):
                    resp = resp.get('return')
                    return resp

            except json.decoder.JSONDecodeError:
                resp = resp.text

            if method.isupper():
                resp = self._format_resp(resp)

            if 'value' in resp:
                resp = resp.get('value')

            if 'return' in resp:
                resp = resp.get('return')

            if callback:
                resp = getattr(self, callback)(resp)
            return resp

        if 400 <= resp.status_code <= 600:
            print('ESM Error:', resp.text)
            sys.exit(1)

    @staticmethod
    def _post(url, data=None, headers=None, verify=False):
        """
        Method that actually kicks off the HTTP client.

        Args:
            url (str): URL to send the post to.
            data (str): Any payload data for the post.
            headers (str): http headers that hold cookie data after
                            authentication.
            verify (bool): SSL cerificate verification

        Returns:
            Requests Response object
        """
        try:
            return requests.post(url, data=data, headers=headers,
                                 verify=verify)

        except requests.exceptions.ConnectionError:
            print("Unable to connect to ESM: {}".format(url))
            sys.exit(1)

    @staticmethod
    def _format_params(cmd, **params):
        """
        Format API call
        """
        params = {key: val
                  for key, val in params.items() if val is not None}

        params = '%14'.join([key + '%13' + val + '%13'
                             for (key, val) in params.items()])
        if params:
            params = 'Request=API%13' + cmd + '%13%14' + params + '%14'
        else:
            params = 'Request=API%13' + cmd + '%13%14'
        return params

    @staticmethod
    def _format_resp(resp):
        """
        Format API response
        """
        resp = re.search('Response=(.*)', resp).group(1)
        resp = resp.replace('%14', ' ')
        pairs = resp.split()
        formatted = {}
        for pair in pairs:
            pair = pair.replace('%13', ' ')
            pair = pair.split()
            key = pair[0]
            if key == 'ITEMS':
                value = dehexify(pair[-1])
            else:
                value = urlparse.unquote(pair[-1])
            formatted[key] = value
        return formatted


class DevTree(object):
    def __init__(self, esm):
        self.esm = esm
        self.build_devtree()
        self._build_summary()
        self._build_name_hash()
        self._build_ip_hash()
        self._build_dsid_hash()

    def _build_summary(self):
        self.summary = set()
        for d in self.devtree:
            self.summary.add(d['name'])
            self.summary.add(d['ds_ip'])
            self.summary.add(d['ds_id'])

    def _build_name_hash(self):
        self.name = {dev['name']: dev for dev in self.devtree}

    def _build_ip_hash(self):
        self.ip = {dev['ds_ip']: dev for dev in self.devtree}

    def _build_dsid_hash(self):
        self.id = {dev['ds_id']: dev for dev in self.devtree}

    def __contains__(self, name):
        if name in self.summary:
            return True

    def __iter__(self):
        return iter(self.devtree)

    def __len__(self):
        return len(self.summary)

    def data_sources(self):
        return [d for d in self.devtree if d['desc_id'] == '3'
                or d['desc_id'] == '256']

    def siem_devices(self):
        nitro_dev_id = ['2', '4', '10', '12', '13', '15']
        return [d for d in self.devtree if d['desc_id'] in nitro_dev_id]

    def build_devtree(self):
        devtree = self._get_devtree()
        devtree = self._format_devtree(devtree)
        containers = self._get_client_containers(devtree)
        devtree = self._merge_clients(containers, devtree)

        zonetree = self._get_zonetree()
        devtree = self._insert_zone_names(zonetree, devtree)
        zone_map = self._get_zone_map()
        devtree = self._insert_zone_ids(zone_map, devtree)
        devtree = self._insert_rec_info(devtree)
        last_times = self._get_last_times()
        last_times = self._format_times(last_times)
        self.devtree = self._insert_ds_last_times(last_times, devtree)
        return self.devtree

    def _get_devtree(self):
        """
        Returns:
            ESM device tree; raw, but ordered, string.
            Does not include client datasources.
        """
        method = 'GRP%5FGETVIRTUALGROUPIPSLISTDATA'
        data = {'ITEMS': '#{DC1 + DC2}',
                'DID': '1',
                'HD': 'F',
                'NS': '0'}
        return self.esm.post(method, data=data)


    def _format_devtree(self, devtree):
        """
        Parse key fields from raw device strings into datasource dicts

        Returns:
            List of datasource dicts
        """
        devtree = StringIO(devtree['ITEMS'])
        devtree = csv.reader(devtree, delimiter=',')
        devtree_lod = []
        _ignore_remote_ds = False

        for idx, row in enumerate(devtree, start=1):
            if len(row) == 0:
                continue

            # Get rid of duplicate 'asset' devices
            if row[0] == '16':
                continue

            # Filter out distributed ESMs
            if row[0] == '9':
                _ignore_remote_ds = True
                continue

            # Filter out distributed ESM data sources
            if _ignore_remote_ds:
                if row[0] != '14':
                    continue
                else:
                    _ignore_remote_ds = False

            if row[2] == "3":  # Client group datasource group containers
                row.pop(0)     # are fake datasources that seemingly have
                row.pop(0)     # two uneeded fields at the beginning.
            if row[16] == 'TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT':
                row[16] = '0'  # Get rid of weird type-id for N/A devices

            if len(row) < 29:
                #print('Unknown datasource: {}.'.format(self._row))
                continue

            ds_fields = {'idx': idx,
                            'desc_id': row[0],
                            'name': row[1],
                            'ds_id': row[2],
                            'enabled': row[15],
                            'ds_ip': row[27],
                            'hostname': row[28],
                            'type_id': row[16],
                            'vendor': '',
                            'model': '',
                            'tz_id': '',
                            'date_order': '',
                            'port': '',
                            'syslog_tls': '',
                            'client_groups': row[29],
                            'zone_name': '',
                            'zone_id': '',
                            'client': False
                            }
            devtree_lod.append(ds_fields)
        return devtree_lod

    def _get_client_containers(self, devtree):
        """
        Filters DevTree for datasources that have client datasources.

        Returns:
            List of datasource dicts that have clients
        """
        return [ds for ds in devtree
                if ds['desc_id'] == "3"
                if int(ds['client_groups']) > 0]


    def _merge_clients(self, containers, devtree):
        _cidx = 0
        _didx = 0
        for cont in containers:
            clients = self._get_clients(cont['ds_id'])
            clients = self._format_clients(clients)
            cont['idx'] = cont['idx'] + _didx
            _pidx = cont['idx']
            _cidx = _pidx + 1
            for client in clients:
                client['parent_id'] = cont['ds_id']
                client['idx'] = _cidx
                _cidx += 1
                _didx += 1
            devtree[_pidx:_pidx] = clients
        return devtree

    def _get_clients(self, ds_id):
        """
        Get list of raw client strings.

        Args:
            ds_id (str): Parent ds_id(s) are collected on init
            ftoken (str): Set and used after requesting clients for ds_id

        Returns:
            List of strings representing unparsed client datasources
        """
        method = 'DS_GETDSCLIENTLIST'
        data = {'DSID': ds_id,
                 'SEARCH': ''}

        file = self.esm.post(method, data=data)['FTOKEN']
        pos = 0
        nbytes = 0
        method = 'MISC_READFILE'
        data = {'FNAME': file,
                'SPOS': '0',
                'NBYTES': '0'}
        resp = self.esm.post(method, data=data)

        if resp['FSIZE'] == resp['BREAD']:
            client_data = resp['DATA']
            method = 'ESSMGT_DELETEFILE'
            data = {'FN': file}
            self.esm.post(method, data=data)
            return dehexify(client_data)

        client_data = []
        client_data.append(resp['DATA'])
        file_size = int(resp['FSIZE'])
        collected = int(resp['BREAD'])

        while file_size > collected:
            pos += int(resp['BREAD'])
            nbytes = file_size - collected
            method = 'MISC_READFILE'
            data = {'FNAME': file,
                    'SPOS': str(pos),
                    'NBYTES': str(nbytes)}
            resp = self.esm.post(method, data=data)
            collected += int(resp['BREAD'])
            client_data.append(resp['DATA'])

        method = 'ESSMGT_DELETEFILE'
        data = {'FN': file}
        self.esm.post(method, data=data)

        return dehexify(''.join(client_data))


    def _get_rfile(self, ftoken):
        """
        Exchanges token for file

        Args:
            ftoken (str): instance name set by

        """
        method = 'MISC_READFILE'
        data = {'FNAME': ftoken,
                'SPOS': '0',
                'NBYTES': '0'}

        resp = self.esm.post(method, data=data)
        return dehexify(resp['DATA'])


    def _format_clients(self, clients):
        """
        Parse key fields from _get_clients() output.

        Returns:
            list of dicts
        """
        clients = StringIO(clients)
        clients = csv.reader(clients, delimiter=',')

        clients_lod = []
        for row in clients:
            if len(row) < 13:
                continue

            ds_fields = {'desc_id': "256",
                          'name': row[1],
                          'ds_id': row[0],
                          'enabled': row[2],
                          'ds_ip': row[3],
                          'hostname': row[4],
                          'type_id': row[5],
                          'vendor': row[6],
                          'model': row[7],
                          'tz_id': row[8],
                          'date_order': row[9],
                          'port': row[11],
                          'syslog_tls': row[12],
                          'client_groups': "0",
                          'zone_name': '',
                          'zone_id': '',
                          'client': True
                        }
            clients_lod.append(ds_fields)
        return clients_lod

    def _get_zonetree(self):
        """
        Retrieves zone data.

        Returns:
            str: device tree string sorted by zones
        """

        method = 'GRP_GETVIRTUALGROUPIPSLISTDATA'
        data = {'ITEMS': '#{DC1 + DC2}',
                  'DID': '3',
                  'HD': 'F',
                  'NS': '0'}

        resp = self.esm.post(method, data=data)
        return dehexify(resp['ITEMS'])

    def _insert_zone_names(self, zonetree, devtree):
        """
        Args:
            zonetree (str): Built by self._get_zonetree

        Returns:
            List of dicts (str: str) devices by zone
        """
        zone_name = None
        zonetree = StringIO(zonetree)
        zonetree = csv.reader(zonetree, delimiter=',')

        for row in zonetree:
            if row[0] == '1':
                zone_name = row[1]
                if zone_name == 'Undefined':
                    zone_name = ''
                continue
            for device in devtree:
                if device['ds_id'] == row[2]:
                    device['zone_name'] = zone_name
        return devtree

    def _get_zone_map(self):
        """
        Builds a table of zone names to zone ids.

        Returns:
            dict (str: str) zone name : zone ids
        """
        zone_map = {}
        method = 'zoneGetZoneTree'
        resp = self.esm.post(method)
        if not resp:
            return zone_map
        for zone in resp:
            zone_map[zone['name']] = zone['id']
            for szone in zone['subZones']:
                zone_map[szone['name']] = szone['id']
        return zone_map


    def _insert_zone_ids(self, zone_map, devtree):
        """
        """
        for device in devtree:
            if device['zone_name'] in zone_map.keys():
                device['zone_id'] = zone_map.get(device['zone_name'])
            else:
                device['zone_id'] = '0'
        return devtree

    def _insert_rec_info(self, devtree):
        """
        Adds parent_ids to datasources in the tree based upon the
        ordered list provided by the ESM. All the datasources below
        a Receiver row have its id set as their parent ID.

        Returns:
            List of datasource dicts
        """
        esm_dev_id = ['14']
        esm_mfe_dev_id = ['19', '21', '22', '24']
        nitro_dev_id = ['2', '4', '10', '12', '13', '15']
        datasource_dev_id = ['3', '5', '7', '17', '20', '23', '256']

        parent_id = parent_name = None
        for device in devtree:
            if device['desc_id'] in esm_dev_id:
                esm_name = device['name']
                esm_id = device['ds_id']
                device['parent_name'] = 'n/a'
                device['parent_id'] = '0'
                continue

            if device['desc_id'] in esm_mfe_dev_id:
                parent_name = device['name']
                parent_id = device['ds_id']
                device['parent_name'] = 'n/a'
                device['parent_id'] = '0'
                continue

            if device['desc_id'] in nitro_dev_id:
                device['parent_name'] = esm_name
                device['parent_id'] = esm_id
                parent_name = device['name']
                parent_id = device['ds_id']
                continue

            if device['desc_id'] in datasource_dev_id:
                device['parent_name'] = parent_name
                device['parent_id'] = parent_id
            else:
                device['parent_name'] = 'n/a'
                device['parent_id'] = 'n/a'

        return devtree

    def _get_last_times(self):
        """
        """
        method = 'QRY%5FGETDEVICELASTALERTTIME'
        data = {}
        return self.esm.post(method, data=data)


    def _format_times(self, last_times):
        """
        Formats the output of _get_last_times

        Args:
            last_times (str): string output from _get_last_times()

        Returns:
            list of dicts - [{'name', 'model', 'last_time'}]
        """
        try:
            last_times = last_times['ITEMS']
        except KeyError:
            print('ESM returned an error while getting event times.')
            print('Does this account have permissions to see the ', end='')
            print('"View Reports" button under System Properties in the ESM?')
            print('The "Administrator Rights" box must be checked for the user.')
            sys.exit(1)

        last_times = StringIO(last_times)
        last_times = csv.reader(last_times, delimiter=',')
        last_times_lod = []
        for row in last_times:
            if len(row) == 5:
                time_d = {}
                time_d['name'] = row[0]
                time_d['model'] = row[2]
                if row[3]:
                    time_d['last_time'] = row[3]
                else:
                    time_d['last_time'] = 'never'
                last_times_lod.append(time_d)
        return last_times_lod

    def _insert_ds_last_times(self, last_times, devtree):
        """
        Parse event times str and insert it into the _devtree

        Returns:
            List of datasource dicts - the devtree
        """
        for device in devtree:
            for d_time in last_times:
                if device['name'] == d_time['name']:
                    device['model'] = d_time['model']
                    device['last_time'] = d_time['last_time']
        return devtree



def dehexify(data):
    """
    Decode hex/url data
    """
    hexen = {
        '\x1c': ',',  # Replacing Device Control 1 with a comma.
        '\x11': ',',  # Replacing Device Control 2 with a new line.
        '\x12': '\n',  # Space
        '\x22': '"',  # Double Quotes
        '\x23': '#',  # Number Symbol
        '\x27': '\'',  # Single Quote
        '\x28': '(',  # Open Parenthesis
        '\x29': ')',  # Close Parenthesis
        '\x2b': '+',  # Plus Symbol
        '\x2d': '-',  # Hyphen Symbol
        '\x2e': '.',  # Period, dot, or full stop.
        '\x2f': '/',  # Forward Slash or divide symbol.
        '\x7c': '|',  # Vertical bar or pipe.
    }

    uri = {
        '%11': ',',  # Replacing Device Control 1 with a comma.
        '%12': '\n',  # Replacing Device Control 2 with a new line.
        '%20': ' ',  # Space
        '%22': '"',  # Double Quotes
        '%23': '#',  # Number Symbol
        '%27': '\'',  # Single Quote
        '%28': '(',  # Open Parenthesis
        '%29': ')',  # Close Parenthesis
        '%2B': '+',  # Plus Symbol
        '%2D': '-',  # Hyphen Symbol
        '%2E': '.',  # Period, dot, or full stop.
        '%2F': '/',  # Forward Slash or divide symbol.
        '%3A': ':',  # Colon
        '%7C': '|',  # Vertical bar or pipe.
    }

    for (enc, dec) in hexen.items():
        data = data.replace(enc, dec)

    for (enc, dec) in uri.items():
        data = data.replace(enc, dec)

    data = urlparse.unquote(data)

    return data
