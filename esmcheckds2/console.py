# -*- coding: utf-8 -*-

import sys
#import esmdscheck2
from configparser import ConfigParser, NoSectionError, MissingSectionHeaderError
from datetime import datetime, timedelta

from esmcheckds2.esmcheckds2 import Config, ESM, dehexify, _print_help_and_exit

def main():
    config = Config()
    host = config.esm_host
    user = config.esm_user
    passwd = config.esm_passwd

    if len(sys.argv) > 1:
        args = dict(arg.split('=') for arg in sys.argv[1].split(', '))
        args = {tunit: int(time) for tunit, time in args.items()}
        td = timedelta(**args)
        time_filter = datetime.now() - td
        format = '%m/%d/%Y %H:%M:%S'
    else:
        _print_help_and_exit()
   
    
    esm = ESM(host, user, passwd)
    esm.login()
    _devtree = esm._build_devtree()
    
    
    print('Datasources with no events since: {:%m/%d/%Y %H:%M:%S}'
            .format(time_filter))

    never = True
    for ds in _devtree:
        fields = [ds['name'], ds['ds_ip'], ds['model'], ds['parent_name'],
                    ds.get('last_time')]
        if never:
            if ds['desc_id'] == '3' and ds['last_time'] == 'never':
                print(','.join(fields))
                continue
        else:
            if ds['desc_id'] == '3' and ds['last_time'] == 'never':
                continue
                
        if ds['desc_id'] == '3' and ds.get('last_time'):
            if datetime.strptime(ds['last_time'], format) < time_filter:
                print(','.join(fields))
                continue
            else:
                #print('Datasource time inside provided time:', 
                #    ds['name'], ds['last_time'])
                continue
        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Control-C Pressed, stopping...")
        sys.exit()
