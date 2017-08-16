# -*- coding: utf-8 -*-

import argparse
import csv
import logging
import os
import socket
import sys
from configparser import ConfigParser, NoSectionError, MissingSectionHeaderError
from datetime import datetime, timedelta
from io import StringIO
from esmcheckds2.esmcheckds2 import Config, ESM, dehexify
from esmcheckds2.version import __version__
from prettytable import PrettyTable, PLAIN_COLUMNS, MSWORD_FRIENDLY

def logging_init():
    logfile = "esmcheckds2.log"
    hostname = socket.gethostname()
    formatter = logging.Formatter('%(asctime)s {} %(module)s: %(message)s'
                                    .format(hostname), datefmt='%b %d %H:%M:%S')
    logger = logging.getLogger()
    logger.setLevel('DEBUG')
    fh = logging.FileHandler(logfile, mode='w')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def _get_time_obj(time_str):
    """
    In some ESM versions the time format is YYYY/MM/DD instead of
    DD/MM/YYYY. This detects and normalizes to the latter.

    Args:
        last_time (str): timestamp in format 'YYYY/MM/DD HH:MM:SS' 
                         or 'DD/MM/YYYY HH:MM:SS'
                         
    Returns:
        str of timestamp in 'DD/MM/YYYY HH:MM:SS' format 
            or None if neither format matches
    """
    time_format1 = '%m/%d/%Y %H:%M:%S'
    time_format2 = '%Y/%m/%d %H:%M:%S'

    try: 
        time_obj = datetime.strptime(time_str, time_format1)
    except ValueError:
        try:
            time_obj = datetime.strptime(time_str, time_format2)
        except ValueError:
            logging.debug('Invalid time format: {}'.format(time_str))
            time_obj = None
    return time_obj

def lol_to_table(lol, format=None, headers=None):
    """
    Args:
        lol (list): list of lists
        format (str): text
        headers (list): list of fields to be used as headers
    
    Return:
        obj - prettytable object
        
    """
    table = PrettyTable(field_names=headers)
    for ds_row in lol:
        table.add_row([f for f in ds_row])
    if format == 'text': 
        table.set_style(PLAIN_COLUMNS) 
    if format == 'word': 
        table.set_style(MSWORD_FRIENDLY)
    table = table.get_string()
    return table
   
def write_table(filename, table):
    """
    Args:
        filename (str)
        table (str) prettytable object will work
    """
    try:
        with open(filename, 'w') as open_f:
            open_f.write(str(table))
    except OSError:
        print('Could not write to file: {}'.format(filename))
    
def write_csv(filename, lol, headers=None):
    """
    Args:
        filename (str)
        result (list) 
    """
    try:
        with open(filename, 'w', newline='') as open_f:
            writer = csv.writer(open_f, delimiter=',')
            if headers:
                writer.writerow(headers)
            writer.writerows(lol)
    except OSError:
        print('Could not write to file: {}'.format(filename))

def print_csv(lol, headers=None):
    """
    Prints list of lists as csv to terminal
    Args:
        result (list) list of lists
        headers (list)
    """
    if headers:
        print(','.join(headers))
    for row in lol:
        print(','.join(row))
            
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
    helpdoc = '''\
    usage: esmcheckds2 <-d|-h|-m> <timeframe> [OPTIONS]

    Show McAfee ESM Datasource Activity
    Specify days, hours, minutes 
    Example: esmcheckds2 -d 7
    Use zero for datasources: -d|-h|-m 0
    
    Timeframe Options:
      -d, --days <num>     Days since datasource active
      -h, --hours <num>    Hours since datasource active
      -m, --minutes <num>  Minutes since datasource active
      
    Additional Options:
      -f, --format         Results format: csv, text, word (default: csv)
      -w, --write [file]   Output to file (default: ds_results.txt)
      -v, --version        Print version
      --disabled           Include disabled datasources
      --epo                Include EPO devices (default: excluded)      
      --debug              Enable debug output
      --help               Show this help message and exit'''
    
    if len(sys.argv) < 2:
        print(helpdoc)
        sys.exit(0)
        
    output_formats = ['text', 'csv', 'word']
    parser = argparse.ArgumentParser(prog='esmcheckds2',
                                     add_help=False,
                                     usage=argparse.SUPPRESS,                                 
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=helpdoc)
    p_group =  parser.add_mutually_exclusive_group(required=True)
    p_group.add_argument('-d', '--days', dest='days', type=int, 
                            help=argparse.SUPPRESS)
    p_group.add_argument('-h', '--hours', dest='hours', type=int, 
                            help=argparse.SUPPRESS)
    p_group.add_argument('-m', '--minutes', dest='minutes', type=int, 
                            help=argparse.SUPPRESS)
    p_group.add_argument('--help', action='help', help=argparse.SUPPRESS)
    parser.add_argument("-w", '--write', nargs='?', const='ds_results.txt', 
                            default=False, help=argparse.SUPPRESS)
    parser.add_argument('-f', '--format', default=None, dest='out_format', 
                            choices=output_formats, help=argparse.SUPPRESS)
    parser.add_argument('--disabled', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--epo', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('-v', '--version', action='version', help=argparse.SUPPRESS,
                            version='%(prog)s {version}'.format(version=__version__))    
    pargs = parser.parse_args()
    
    if pargs.debug:
        logging_init()
    
    if pargs.days is not None:
        td = timedelta(days=pargs.days)
    if pargs.hours is not None:
        td = timedelta(hours=pargs.hours)
    if pargs.minutes is not None:
        td = timedelta(minutes=pargs.minutes)

    time_filter = datetime.utcnow() - td
    out_format = pargs.out_format
    filename = pargs.write
    include_disabled = pargs.disabled
    include_epo = pargs.epo

    esm = ESM(host, user, passwd)
    esm.login()
    _devtree = esm._build_devtree()
    output_lol = []
    ds_types = ['3']    
    if include_epo:
        ds_types.append('20')
    
    for ds in _devtree:
        logging.debug('Enumerating datasource: {}'.format(ds['name']))
        if ds['desc_id'] not in ds_types or not ds.get('last_time'):
            logging.debug('Skipping non datasource: {}'.format(ds['name']))
            continue

        fields = [ds['name'], ds['ds_ip'], ds['model'], 
                  ds['parent_name'], ds['last_time']]

        if ds['enabled'] == 'F':
            if include_disabled:
                output_lol.append(fields)
                logging.debug('Adding disabled datasource: {}'.format(ds['name']))
                continue
            else:
                logging.debug('Skipping disabled datasource: {}'.format(ds['name']))
                continue
                  
        if ds['last_time'] == 'never':
            output_lol.append(fields)
            logging.debug('Adding never seen datasource: {}'.format(ds['name']))
            continue
        
        last_time = _get_time_obj(ds['last_time'])
        if not ds['last_time']:
            print("Invalid time format: {} {}"
                    .format(ds['name'], last_time))
            logging.debug('Skipping invalid datasource time: {}'.format(ds['name']))
            continue
        elif last_time < time_filter:
            output_lol.append(fields)
            logging.debug('Adding datasource in range: {}'.format(ds['name']))
            continue
        else:
            logging.debug('Skipping active datasource: {} - {}'.format(ds['name'], ds['last_time']))
            continue

    headers = ['name', 'IP', 'Type', 'Parent Device', 'Last Time']
    
    if out_format == 'csv':
        if filename:
            write_csv(filename, output_lol, headers)
        else:
            print_csv(output_lol, headers)
    
    else:
        out_table = lol_to_table(output_lol, out_format, headers)
        if filename:
            write_table(filename, out_table)
        else:
            print('\nDatasources without events since: {:%m/%d/%Y %H:%M:%S}'
                    .format(time_filter))
            print(out_table)

        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Control-C Pressed, stopping...")
        sys.exit()
