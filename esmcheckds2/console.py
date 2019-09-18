# -*- coding: utf-8 -*-

import argparse
import csv
import logging
import os
import socket
import sys
import dateutil.parser as dateparser
from configparser import ConfigParser, NoSectionError, MissingSectionHeaderError
from datetime import datetime, timedelta
from io import StringIO
from esmcheckds2.esmcheckds2 import Config, ESM, dehexify, DevTree
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
    Converts given timestamp string to datetime object
    
    Args:
        time_str (str): time as a string, e.g. 2019/02/28 22:22:22
                         
    Returns:
        datetime object or None if no format matches 
        
    """
    return dateparser.parse(time_str)

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
    # try:
    #     host = config.esmhost
    # except AttributeError:
    #     print("Cannot find 'esmhost' key in .mfe_saw.ini")
    #     sys.exit(0)
    # try:        
    #     user = config.esmuser
    # except AttributeError:
    #     print("Cannot find 'esmuser' key in .mfe_saw.ini")
    #     sys.exit(0)
    # try:        
    #     passwd = config.esmpass
    # except AttributeError:
    #     print("Cannot find 'esmpass' key in .mfe_saw.ini")
    #     sys.exit(0)
    helpdoc = '''\
    usage: esmcheckds2 <-d|-h|-m|-a|--future> <timeframe> [OPTIONS]

    Show McAfee ESM Datasource Activity
    Specify days, hours, minutes 
    Example: esmcheckds2 -d 1
             esmcheckds2 -a --disabled
             
    Timeframe Options:
      -d, --days <num>     Days since datasource active
      -h, --hours <num>    Hours since datasource active
      -m, --minutes <num>  Minutes since datasource active
      -a, --all            Show all devices
      --future             Only devices with time in future 
      
    Additional Options:
      -z, --zone [zone]    Limit devices to zone
      --disabled           Exclude disabled devices
      --mfe                Exclude top level McAfee devices (EPO, NSM...)
      --siem               Exclude SIEM devices (ESM, ERC...)
      --dsid               Display the Datasource ID field
      -f, --format         Result format: csv, text, MS word 
      -w, --write [file]   Output to file (default: ds_results.txt)
      -v, --version        Print version
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
    p_group.add_argument('-a', '--all', dest='show_all', action='store_true', 
                            help=argparse.SUPPRESS)
    p_group.add_argument('--future', action='store_true', help=argparse.SUPPRESS)
    p_group.add_argument('--help', action='help', help=argparse.SUPPRESS)
    parser.add_argument("-z", '--zone', nargs='?', const=None, 
                            default=False, help=argparse.SUPPRESS)
    parser.add_argument('--disabled', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--mfe', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--siem', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--dsid', action='store_true', help=argparse.SUPPRESS)
    

    parser.add_argument('-f', '--format', default=None, dest='out_format', 
                            choices=output_formats, help=argparse.SUPPRESS)
    parser.add_argument("-w", '--write', nargs='?', const='ds_results.txt', 
                            default=False, help=argparse.SUPPRESS)
    parser.add_argument('-v', '--version', action='version', help=argparse.SUPPRESS,
                            version='%(prog)s {version}'.format(version=__version__))    
    parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    pargs = parser.parse_args()

    if pargs.debug:
        logging_init()
        
    out_format = pargs.out_format
    filename = pargs.write
    zone = pargs.zone
    exclude_disabled = pargs.disabled
    exclude_mfe = pargs.mfe
    exclude_siem = pargs.siem
    dsid = pargs.dsid
    future_only = pargs.future
    show_all = pargs.show_all
    
    esm = ESM(config)
    now_str = esm.time()[:-7]
    _devtree = DevTree(esm)
    esm.logout()

    host = config.esmhost

    now = datetime.strptime(now_str, '%Y-%m-%dT%H:%M:%S')
    if show_all:
        time_filter = False
    elif future_only:
        td = timedelta(minutes=1)
        time_filter = now + td
    else:
        if pargs.days is not None:
            td = timedelta(days=pargs.days)
        if pargs.hours is not None:
            td = timedelta(hours=pargs.hours)
        if pargs.minutes is not None:
            td = timedelta(minutes=pargs.minutes)        
        time_filter = now - td

    
    internal_types = {'1': 'zone',
                       '2': 'ERC',
                       '3': 'datasource',
                       '4': 'Database Event Monitor (DBM)',
                       '5': 'DBM Database',
                       '7': 'Policy Auditor',
                       '10': 'Application Data Monitor (ADM)',
                       '12': 'ELM',
                       '13': 'Local Receiver-ELM',
                       '14': 'Local ESM',
                       '15': 'Advanced Correlation Engine (ACE)',
                       '16': 'Asset datasource',
                       '17': 'Score-based Correlation',
                       '19': 'McAfee ePolicy Orchestrator (ePO)',
                       '20': 'EPO Module',
                       '21': 'McAfee Network Security Manager (NSM)',
                       '22': 'McAfee Network Security Platform (NSP)',
                       '23': 'NSP Port',
                       '24': 'McAfee Vulnerability Manager (MVM)',
                       '25': 'Enterprise Log Search (ELS)',
                       '254': 'client_group',
                       '256': 'client'}
    type_filter = ['1', '16', '254']
    mfe_types = ['7', '19', '20', '21', '22', '23', '24']
    siem_types = ['2', '4', '5', '10', '12', '13', '14', '15', '17', '25']
    
    if exclude_mfe:
        type_filter.extend(mfe_types)

    if exclude_siem:
        type_filter.extend(siem_types)
        
    ds_types = [int_t_id for int_t_id in internal_types.keys() 
                    if int_t_id not in type_filter]

    output_lol = []
    for ds in _devtree:
        if ds['desc_id'] not in ds_types:
            logging.debug('PASS - filtered datasource: {}'.format(ds['name']))
            continue
        
        if not ds.get('last_time'):
            ds['last_time'] = 'n/a'
        
        fields = [ds['name'], ds['ds_ip'], ds['model'], 
                  ds['parent_name'], ds['zone_name'], ds['last_time']]
        headers = ['Name', 'IP', 'Type', 'Parent Device', 'Zone', 'Last Time']
        
        if dsid:
            fields.insert(1, ds['ds_id'])
            headers.insert(1, 'DS ID')
                
        if exclude_disabled:
            if ds['enabled'] == 'F':
                logging.debug('PASS - disabled datasource: {}'.format(ds['name']))
                continue

        if zone:
            if zone.lower() != ds['zone_name'].lower():
                logging.debug('PASS - out of zone: {}'.format(ds['name']))
                continue
            
        if (ds['last_time'] == 'never') or (ds['last_time'] == 'n/a'):
            if future_only:
                logging.debug('PASS - time not future: {}'.format(ds['name']))
                continue
            else:
                logging.debug('ADD - no last time: {}'.format(ds['name']))
                output_lol.append(fields)
                continue
                
        if show_all:
            logging.debug('ADD - all devices times: {}'.format(ds['name']))
            output_lol.append(fields)
            continue

        last_time = _get_time_obj(ds['last_time'])
        if not ds['last_time']:
            logging.debug('PASS - invalid time: {}'.format(ds['name']))
            continue

        if future_only:
            if last_time > time_filter:
                output_lol.append(fields)
                logging.debug('ADD - future-time: {}'.format(ds['name']))
                continue
            else:
                logging.debug('PASS - time not future: {}'.format(ds['name']))
                continue
        elif last_time < time_filter:
            output_lol.append(fields)
            logging.debug('ADD - idle too long: {}'.format(ds['name']))
        else:
            logging.debug('PASS - not idle: {} - {}'.format(ds['name'], ds['last_time']))
            continue
    
    if out_format == 'csv':
        if filename:
            write_csv(filename, output_lol, headers)
        else:
            print_csv(output_lol, headers)
    
    else:
        out_table = lol_to_table(output_lol, out_format, headers)
        count = len(output_lol)
        if filename:
            write_table(filename, out_table)
        else:
            try:
                print(out_table)
                print('ESM: {} | ESM Time UTC: {} | Time Offset: {} | Zone: {} | Device Count: {}'
                       .format(host, now, time_filter, zone, count))
            except UnicodeEncodeError:
                print('Console does not support Unicode characters')


        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Control-C Pressed, stopping...")
        sys.exit()
