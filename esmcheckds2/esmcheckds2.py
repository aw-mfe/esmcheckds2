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
from configparser import ConfigParser, NoSectionError, MissingSectionHeaderError
from datetime import datetime, timedelta
from esmcheckds2.version import __version__

requests.packages.urllib3.disable_warnings()

class Config(object):
    """
    Find the config settings which include:
    
     - esm_host
     - esm_user
     - esm_passwd    
    """
    CONFIG = None

    @classmethod
    def find_ini(cls):
        """
        Attempt to locate a mfe_saw.ini file 
        """
        config = ConfigParser()
        module_dir = os.path.dirname(sys.modules[__name__].__file__)

        if 'APPDATA' in os.environ:
            conf_path = os.environ['APPDATA']
        elif 'XDG_CONFIG_HOME' in os.environ:  
            conf_path = os.environ['XDG_CONFIG_HOME']
        elif 'HOME' in os.environ:  
            conf_path = os.path.join(os.environ['HOME'], '.config')
        else:
            conf_path = None

        paths = [os.path.join(module_dir, '.mfe_saw.ini'), '.mfe_saw.ini']
        if conf_path is not None:
            paths.insert(1, os.path.join(conf_path, '.mfe_saw.ini'))
        config.read(paths)
        cls.CONFIG = config

    def __init__(self, **kwargs):
        """
        Initialize a Config instance.
        
        """
        self._kwargs = kwargs
        self.find_ini()
        self._find_envs()
        self._init_config()
    
    def _find_envs(self):
        """
        Builds a dict with env variables set starting with 'ESM'.
        """
        self._envs = {self._kenv: self._venv 
                        for self._kenv, self._venv in os.environ.items()
                          if self._kenv.startswith('ESM')}
                          
    def _init_config(self):
        """ 
        """
        if not self.CONFIG:
            raise FileNotFoundError('mfe_ini file not found.')
            
        try:
            self.types = dict(self.CONFIG.items('types'))
        except NoSectionError:
            self.types = None
            
        try:
            self.recs = dict(self.CONFIG.items('recs'))
        except NoSectionError:
            self.recs = None

        try:
            self._ini = dict(self.CONFIG.items('esm'))
            self.__dict__.update(self._ini)
        except NoSectionError:
            print("Section [esm] not found in mfe_saw.ini")

        # any envs overwrite the ini values
        if self._envs:
            self._envs = {self._key.lower(): self._val
                            for self._key, self._val in self._envs.items()}
            self.__dict__.update(self._envs)

class ESM(object):
    """
    """

    def __init__(self, hostname, username, password):
        """
        """
        self._host = hostname
        self._user = username
        self._passwd = password
        
        self._base_url = 'https://{}/rs/esm/'.format(self._host)
        self._int_url = 'https://{}/ess'.format(self._host)

        self._v9_creds = '{}:{}'.format(self._user, self._passwd)
        self._v9_b64_creds = base64.b64encode(self._v9_creds.encode('utf-8'))

        self._v10_b64_user = base64.b64encode(self._user.encode('utf-8')).decode()
        self._v10_b64_passwd = base64.b64encode(self._passwd.encode('utf-8')).decode()
        self._v10_params = {"username": self._v10_b64_user, 
                            "password": self._v10_b64_passwd, 
                            "locale": "en_US", 
                            "os" : "Win32"}
        self._headers = {'Content-Type': 'application/json'}
        
    def login(self):
        """
        Log into the ESM
        """
        self._headers = {'Authorization':'Basic '
                         + self._v9_b64_creds.decode('utf-8'),
                         'Content-Type': 'application/json'}
        self._method = 'login'
        self._data = self._v10_params
        self._resp = self.post(self._method, data=self._data, 
                                headers=self._headers, raw=True)
        
        if self._resp.status_code == 401:
            print('Invalid username or password for the ESM')
            sys.exit(1)
            
        self._data = ''
        self._headers = {'Content-Type': 'application/json'}
        self._headers['Cookie'] = self._resp.headers.get('Set-Cookie')
        self._headers['X-Xsrf-Token'] = self._resp.headers.get('Xsrf-Token')
        self._headers['SID'] = self._resp.headers.get('Location')
        
    def _build_devtree(self):
        """
        Coordinates assembly of the devtree 
        """
        self._devtree = self._get_devtree()
        self._devtree = self._insert_rec_info()
        self._client_containers = self._get_client_containers()

        """
        This next bit of code gets and formats the clients for each
        container and inserts them back into the devtree.
        
        The tricky part is keeping the devtree in order and keeping 
        index labels consistent for all of the devices while 
        inserting new devices into the middle with their own index
        labels. Kind of like changing a tire on a moving car...
        
        pidx - parent idx is the original index value of the parent
                this does not increment
                
        cidx - client idx is incremented starting after the pidx
        
        didx - stores the delta between different containers to 
               keep it all in sync.
        """
        self._cidx = 0
        self._didx = 0
        for self._container in self._client_containers:
            self._raw_clients = self._get_raw_clients(self._container['ds_id'])
            self._clients_lod = self._clients_to_lod(self._raw_clients)
            self._container['idx'] = self._container['idx'] + self._didx
            self._pidx = self._container['idx']
            self._cidx = self._pidx + 1 
            for self._client in self._clients_lod:
                self._client['parent_id'] = self._container['ds_id']
                self._client['idx'] = self._cidx 
                self._cidx += 1 
                self._didx += 1
            self._devtree[self._pidx:self._pidx] = self._clients_lod 
        self._devtree = self._insert_rec_info()
        self._last_times = self._get_last_times()
        self._last_times = self._format_times(self._last_times)
        self._devtree = self._insert_ds_last_times(self._last_times)
        return self._devtree

    def _get_devtree(self):
        """
        Returns:
            ESM device tree; raw, but ordered, string.
            Does not include client datasources.
        """
        self._method = 'GRP%5FGETVIRTUALGROUPIPSLISTDATA'
        self._data = {'ITEMS': '#{DC1 + DC2}', 
                      'DID': '1', 
                      'HD': 'F',
                      'NS': '0'}

        if self._headers.get('SID') is not None:
            self._data['SID'] = self._headers['SID']
        self._resp = self.post(self._method, data=self._data, headers=self._headers,
                                callback=self._devtree_to_lod)
        return self._resp
                
    def _devtree_to_lod(self, devtree):
        """
        Parse key fields from raw device strings into datasource dicts
        
        Returns: 
            List of datasource dicts
        """
        self._devtree = devtree
        self._devtree = self._devtree['ITEMS']
        self._devtree_io = StringIO(self._devtree)
        self._devtree_csv = csv.reader(self._devtree_io, delimiter=',')
        self._devtree_lod = []

        for self._idx, self._row in enumerate(self._devtree_csv, start=1):
            if len(self._row) == 0:
                continue
            
            if self._row[0] == '16':  # Get rid of duplicate 'asset' devices
                continue
            
            if self._row[2] == "3":  # Client group datasource group containers
                self._row.pop(0)     # are fake datasources that seemingly have
                self._row.pop(0)     # two uneeded fields at the beginning.

            if self._row[16] == 'TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT':
                self._row[16] = '0'  # Get rid of weird type-id for N/A devices
                
            self._ds_fields = {'idx': self._idx,
                                'desc_id': self._row[0],
                                'name': self._row[1],
                                'ds_id': self._row[2],
                                'enabled': self._row[15],
                                'ds_ip': self._row[27],
                                'hostname' : self._row[28],
                                'type_id': self._row[16],
                                'vendor': '',
                                'model': '',
                                'tz_id': '',
                                'date_order': '',
                                'port': '',
                                'syslog_tls': '',
                                'client_groups': self._row[29],
                                'zone_name': '',
                                'zone_id': '',
                                'client': False
                              }
            self._devtree_lod.append(self._ds_fields)
        return self._devtree_lod
                
    def _get_client_containers(self):
        """
        Filters DevTree for datasources that have client datasources.
        
        Returns:
            List of datasource dicts that have clients
        """
        return [self._ds for self._ds in self._devtree
                                if self._ds['desc_id'] == "3" 
                                if int(self._ds['client_groups']) > 0]
        
    def _get_raw_clients(self, ds_id):
        """
        Get list of raw client strings.
        
        Args:
            ds_id (str): Parent ds_id(s) are collected on init
            ftoken (str): Set and used after requesting clients for ds_id
            
        Returns:
            List of strings representing unparsed client datasources
        """
        self._ds_id = ds_id
        self._method = 'DS_GETDSCLIENTLIST'
        self._data = {'DSID': self._ds_id,
                      'SEARCH': ''}
        if self._headers.get('SID') is not None:
            self._data['SID'] = self._headers['SID']

        self._resp = self.post(self._method, data=self._data, headers=self._headers)
        self._ftoken = self._resp['FTOKEN']
        return self._get_rfile(self._ftoken)

    def _get_rfile(self, ftoken):
        """
        Exchanges token for file
        
        Args:
            ftoken (str): instance name set by 
        
        """
        self._ftoken = ftoken
        self._method = 'MISC_READFILE'
        self._data = {'FNAME': self._ftoken,
                       'SPOS': '0',
                       'NBYTES': '0'}

        if self._headers.get('SID') is not None:
            self._data['SID'] = self._headers['SID']

        self._resp = self.post(self._method, data=self._data, headers=self._headers)
        return dehexify(self._resp['DATA'])

    def _clients_to_lod(self, clients):
        """
        Parse key fields from _get_clients() output.
        
        Returns:
            list of dicts
        """
        self._clients = clients
        self._clients_io = StringIO(self._clients)
        self._clients_csv = csv.reader(self._clients_io, delimiter=',')

        self._clients_lod = []
        for self._row in self._clients_csv:
            if len(self._row) < 2:
                continue

            self._ds_fields = {'desc_id': "256",
                              'name': self._row[1],
                              'ds_id': self._row[0],
                              'enabled': self._row[2],
                              'ds_ip': self._row[3],
                              'hostname' : self._row[4],
                              'type_id': self._row[5],
                              'vendor': self._row[6],
                              'model': self._row[7],
                              'tz_id': self._row[8],
                              'date_order': self._row[9],
                              'port': self._row[11],
                              'syslog_tls': self._row[12],
                              'client_groups': "0",
                              'zone_name': '',
                              'zone_id': '',
                              'client': True
                              }
            self._clients_lod.append(self._ds_fields)
        return self._clients_lod

    def _insert_rec_info(self):
        """
        Adds parent_ids to datasources in the tree based upon the 
        ordered list provided by the ESM. All the datasources below
        a Receiver row have it's id set as their parent ID.
        
        Returns:
            List of datasource dicts
        """
        self._pid = '0'
        for self._ds in self._devtree:
            if self._ds['desc_id'] in ['14']:
                self._esm_name = self._ds['name']
                self._esm_id = self._ds['ds_id']
                self._ds['parent_id'] = '0'
                self._ds['parent_name'] = 'n/a'
                
            if self._ds['desc_id'] in ['2', '4', '10', '12', '13', '15']:
                self._ds['parent_name'] = self._esm_name
                self._ds['parent_id'] = self._esm_id
                self._parent_name = self._ds['name']
                self._pid = self._ds['ds_id']
                continue
                
            if self._ds['desc_id'] in ['3', '5', '7', '17', '19', 
                                        '20', '21', '22', '24', '256']:
                self._ds['parent_id'] = self._pid
                self._ds['parent_name'] = self._parent_name
            else:
                self._ds['parent_name'] = 'n/a'
                self._ds['parent_id'] = 'n/a'
                
        return self._devtree

    def _get_last_times(self):
        """
        """
        self._method = 'QRY%5FGETDEVICELASTALERTTIME'
        if self._headers.get('SID') is not None:
            self._session= {'SID' : self._headers['SID']}
            self._data = self._session
        else:
            self._data ={}

        self._resp = self.post(self._method, data=self._data, headers=self._headers)
        return self._resp
        
    def _format_times(self, last_times):
        """
        Formats the output of _get_last_times

        Args:
            last_times (str): string output from _get_last_times()

        Returns:
            list of dicts - [{'name', 'model', 'last_time'}]
        """
        self._last_times = last_times
        self._last_times = self._last_times['ITEMS']
        self._last_times_io = StringIO(self._last_times)
        self._last_times_csv = csv.reader(self._last_times_io, delimiter=',')
        self._last_times = []
        for self._row in self._last_times_csv:
            if len(self._row) == 5:
                self._time_d = {}
                self._time_d['name'] = self._row[0]
                self._time_d['model'] = self._row[2]
                if self._row[3]:
                    self._time_d['last_time'] = self._row[3]
                else:
                    self._time_d['last_time'] = 'never'
                self._last_times.append(self._time_d)
        return self._last_times
        
    def _insert_ds_last_times(self, last_times):
        """
        Parse event times str and insert it into the _devtree
        
        Returns: 
            List of datasource dicts - the devtree
        """
        self._last_times = last_times
        count = 0
        for self._ds in self._devtree:
            for self._time in self._last_times:
                if self._ds['name'] == self._time['name']:
                    self._ds['model'] = self._time['model']
                    self._ds['last_time'] = self._time['last_time']
        return self._devtree        
        
    def post(self, method, data=None, callback=None, raw=None, 
                headers=None, verify=False):
        """
        """
        self._method = method
        self._data = data
        self._callback = callback
        self._headers = headers
        self._raw = raw
        self._verify = verify

        if not self._method:
            raise ValueError("Method must not be None")
        
        self._url = self._base_url + self._method
        if self._method == self._method.upper():
            self._url = self._int_url
            self._data = self._format_params(self._method, **self._data)
        else:
            self._url = self._base_url + self._method
            if self._data:
                try:
                    self._data = json.dumps(self._data)
                except json.JSONDecodeError:
                    raise TypeError('Invalid parameter format')

        
        self._resp = self._post(self._url, data=self._data,
                               headers=self._headers, verify=self._verify)

        if self._raw:
            return self._resp

        if 200 <= self._resp.status_code <= 300:
            try:
                self._resp = self._resp.json()
                self._resp = self._resp.get('return')
            except json.decoder.JSONDecodeError:
                self._resp = self._resp.text
            if self._method == self._method.upper():
                self._resp = self._format_resp(self._resp)
            if self._callback:
                self._resp = self._callback(self._resp)
            return self._resp
        if 400 <= self._resp.status_code <= 600:
            print('ESM Error:', self._resp.text)
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
        return requests.post(url, data=data, headers=headers,
                             verify=verify)
                             
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

    return data

def _print_help_and_exit():

    print("""ESM-Check_DS: List inactive datasources on a McAfee ESM
  Usage: esm-check_ds (days|hours|minutes)=x  
  Provides a list of datasources with no events since the given time unit. 
    
    Examples:
        esm-check_ds days=2
        esm-check_ds hours=6
        esm-check_ds minutes=60
    
Output is csv:
    name,ip,model,rec_name,last_time
    
Redirect output to file and import as a spreadsheet.
    
    """)
    sys.exit(0)

    
# def main():
    # config = Config()
    # host = config.esm_host
    # user = config.esm_user
    # passwd = config.esm_passwd

    # if len(sys.argv) > 1:
        # args = dict(arg.split('=') for arg in sys.argv[1].split(', '))
        # args = {tunit: int(time) for tunit, time in args.items()}
        # td = timedelta(**args)
        # time_filter = datetime.now() - td
        # format = '%m/%d/%Y %H:%M:%S'
    # else:
        # _print_help_and_exit()
   
    
    # esm = ESM(host, user, passwd)
    # esm.login()
    # _devtree = esm._build_devtree()
    
    
    # print('Datasources with no events since: {:%m/%d/%Y %H:%M:%S}'
            # .format(time_filter))

    # never = True
    # for ds in _devtree:
        # fields = [ds['name'], ds['ds_ip'], ds['model'], ds['parent_name'],
                    # ds.get('last_time')]
        # if never:
            # if ds['desc_id'] == '3' and ds['last_time'] == 'never':
                # print(','.join(fields))
                # continue
        # else:
            # if ds['desc_id'] == '3' and ds['last_time'] == 'never':
                # continue
                
        # if ds['desc_id'] == '3' and ds.get('last_time'):
            # if datetime.strptime(ds['last_time'], format) < time_filter:
                # print(','.join(fields))
                # continue
            # else:
                # #print('Datasource time inside provided time:', 
                # #    ds['name'], ds['last_time'])
                # continue
        
# if __name__ == "__main__":
    # try:
        # main()
    # except KeyboardInterrupt:
        # logging.warning("Control-C Pressed, stopping...")
        # sys.exit()
