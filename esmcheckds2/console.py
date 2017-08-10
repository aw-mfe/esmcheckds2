# -*- coding: utf-8 -*-

import sys
from configparser import ConfigParser, NoSectionError, MissingSectionHeaderError
from datetime import datetime, timedelta
from esmcheckds2.esmcheckds2 import Config, ESM, dehexify, _print_help_and_exit

def main():
    config = Config()
    try:
        host = config.esmhost
    except AttributeError:
        print("Cannot find 'esmhost' key in .mfe_saw.ini")
        sys.exit(0)
    try:        
        user = config.esmuser
    except AttributeError:
        print("Cannot find 'esmuser' key in .mfe_saw.ini")
        sys.exit(0)
    try:        
        passwd = config.esmpass
    except AttributeError:
        print("Cannot find 'esmpass' key in .mfe_saw.ini")
        sys.exit(0)

    if len(sys.argv) > 1:
        args = dict(arg.split('=') for arg in sys.argv[1].split(', '))
        try:
            args = {tunit: int(time) for tunit, time in args.items()}
        except ValueError:
            _print_help_and_exit()
        td = timedelta(**args)
        time_filter = datetime.now() - td
        format1 = '%m/%d/%Y %H:%M:%S'
        format2 = '%Y/%m/%d %H:%M:%S'
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
            # In some versions the time format is YYYY/MM/DD instead of
            # DD/MM/YYYY. This detects and normalizes to the latter.
            try: 
                last_time = datetime.strptime(ds['last_time'], format1)
            except ValueError:
                try:
                    last_time = datetime.strptime(ds['last_time'], format2)
                    ds['last_time'] = last_time.strftime(format1)
                except ValueError:
                    print("Datasource does not appear to have valid time: {}"
                            .format(last_time))
                       
            if last_time < time_filter:
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
