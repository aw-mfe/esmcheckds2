==========================================
McAfee SIEM Check Datasources: esmdscheck2
==========================================

This script queries a McAfee ESM for inactive data sources.

**Updates from esm-check-ds v1:**

-  New Name!

-  Order of magnitude faster!

-  Completely rewritten to perform a set of limited queries regardless of the number of datasources.

-  McAfee ESM 9.x and 10.x versions are now supported in a single script.

-  Additional information provided for each datasource (IP, parent device name).

-  Native Windows support with the script compiled into a single portable exe.

-  Output formats include CSV, MS Word, text and bordered.

-  Settings stored in ini file in secure directory.

If you do not want to run the Windows EXE then you will need to make sure Python 3 is installed.

Directions on how to install and create an environment to run the script on both Linux and Windows are available at:
https://community.mcafee.com/people/andy777/blog/2016/11/29/installing-python-3

The script requires a .mfe\_saw.ini file for the credentials. 

See installation notes to determine which directory it should be placed for your operating system.

----------
QuickStart
----------

**Windows**

1. Download the `latest release <https://github.com/andywalden/esmcheckds2/releases/latest>`__

2. Unzip it into a directory.

3. Create your .mfe_saw.ini configuration_ file.

4. Run esmcheckds2.exe -a

**Linux**

1. pip3 install esmcheckds2

2. Create your .mfe_saw.ini configuration_ file.

3. Run esmcheckds2.exe -a

-----
Usage
-----

::

        usage: esmcheckds2 <-d|-h|-m|-a|--future> <timeframe> [OPTIONS]

**Timeframe Options:**

      -d, --days <num>     Days since datasource active
      -h, --hours <num>    Hours since datasource active
      -m, --minutes <num>  Minutes since datasource active
      -a, --all            Show all devices
      --future             Only devices with time in future
      
**Additional Options:**

      -z, --zone [zone]    Limit devices to zone
      --disabled           Exclude disabled devices
      --mfe                Exclude top level McAfee devices (EPO, NSM...)
      --siem               Exclude SIEM devices (ESM, ERC...)
      -f, --format         Results format: csv, text, word (default: csv)
      -w, --write [file]   Output to file (default: ds_results.txt)
      -v, --version        Print version
      --debug              Enable debug output
      --help               Show this help message and exit      
      
---------
Examples:
---------

*Note: All time frames are automatically converted to GMT which is how the ESM stores time.*

Show all non-disabled datasources that have not sent an event in the past hour:
::

        $ esmcheckds2 -h 1
        +-----------------------------------+-----------------+----------------------------------------------+----------------------------------------+---------------------+
        |   name                            |        IP       |                   Type                       |             Parent Device              |      Last Time      |
        +-----------------------------------+-----------------+----------------------------------------------+----------------------------------------+---------------------+
        |   Historical Correlation Engine   |  172.12.109.41  |              Correlation Engine              | Adv Correlation Engine Historical _41_ | 2017/04/13 20:21:32 |
        |   Test 1                          |  172.12.109.92  |                Load Balancer                 |   Event Receiver - 4600 - EBC _133_    |        never        |
        |   Test2                           |  172.12.109.92  |                Load Balancer                 |   Event Receiver - 4600 - EBC _133_    |        never        |
        |   Cisco ACS VPN                   |  172.12.109.39  |                  Secure ACS                  |      Event Receiver - 4600 _134_       | 2017/08/16 08:13:03 |
        |   Endpoint Manager                |  172.12.109.29  |            Advanced Syslog Parser            |      Event Receiver - 4600 _134_       | 2017/08/16 08:13:03 |
        |   NextGen Firewall                |  172.12.109.19  |             Firewall Enterprise              |      Event Receiver - 4600 _134_       | 2017/08/16 08:13:03 |
        |   Snare                           |  172.12.109.79  |              Snare for Windows               |      Event Receiver - 4600 _134_       | 2017/08/16 08:13:03 |
        |   Web Gateway                     |  172.12.109.99  |                 Web Gateway                  |      Event Receiver - 4600 _134_       | 2017/08/16 08:13:03 |
        |   Windows DC Central              |  172.12.109.89  |              Snare for Windows               |      Event Receiver - 4600 _134_       | 2017/08/16 08:13:03 |
        |   Windows DC East                 |  172.12.109.47  |              Snare for Windows               |      Event Receiver - 4600 _134_       | 2017/08/16 08:13:03 |
        |   Windows DC West                 |  172.12.109.44  |              Snare for Windows               |      Event Receiver - 4600 _134_       | 2017/08/16 08:13:03 |
        |   MalTrail                        |  172.12.110.238 |            Advanced Syslog Parser            |      Event Receiver - Demo _139_       | 2017/07/17 17:25:10 |
        +-----------------------------------+-----------------+----------------------------------------------+----------------------------------------+---------------------+
        Host: 10.0.0.10 | Current UTC: 2017-10-16 20:03:17 | Time Offset: False | Zone: False | Device Count: 12


Show all non-disabled datasources regardless of the last event time:
::

        $ esmcheckds2 -a --disabled
        +------+-------------+-------+---------------+---------------------+
        | name |      IP     |  Type | Parent Device |      Last Time      |
        +------+-------------+-------+---------------+---------------------+
        | app  |  10.1226.3 | Linux |     ERC-1     | 08/16/2017 15:10:45 |
        |  gw  |  10.1226.1 | Linux |     ERC-1     | 08/16/2017 15:12:45 |
        | Mail |  10.1226.4 | Linux |     ERC-1     | 08/16/2017 15:12:45 |
        | NS0  | 10.1226.10 | Linux |     ERC-1     | 08/16/2017 15:12:45 |
        | NS1  | 10.1226.12 | Linux |     ERC-1     | 08/16/2017 14:18:45 |
        | Tool |  10.1226.6 | Linux |     ERC-1     | 08/16/2017 14:26:45 |
        +------+-------------+-------+---------------+---------------------+
        Host: 10.0.0.10 | Current UTC: 2017-10-16 20:03:17 | Time Offset: False | Zone: False | Device Count: 6

Show all datasources for a particular zone idle for over a day:
::

        +-----------------------------+---------------+--------------------------+-----------------------------+-----------+
        |             name            |       IP      |           Type           |        Parent Device        | Last Time |
        +-----------------------------+---------------+--------------------------+-----------------------------+-----------+
        | Intrusion Prevention System | 172.16.19.149 | Network Security Manager | Event Receiver - 4600 _134_ |   never   |
        +-----------------------------+---------------+--------------------------+-----------------------------+-----------+
        Host: 10.0.0.10 | ESM Time UTC: 2017-10-16 20:21:11 | Time Offset: 2017-10-15 20:21:11 | Zone: demo | Device Count: 1        

Show all datasources in CSV format:
::
    
    $ esmcheckds2 -a -f csv

    Datasources with no events since: 07/28/2017 13:25:04
    001w7tie,172.22.117.20,Windows Event Log - WMI,Receiver (events),never
    ATD_test,10.75.113.5,Advanced Threat Defense,Receiver (events),12/01/2015 17:43:19
    esx000,172.22.119.34,VMware,Receiver (events),10/02/2015 15:19:05
    esx001,172.22.119.35,VMware,Receiver (events),10/02/2015 15:19:05
    esx002,172.22.119.36,VMware,Receiver (events),never
    esx003,172.22.119.37,VMware,Receiver (events),12/08/2015 19:22:28
    esx004,172.22.119.38,VMware,Receiver (events),12/08/2015 19:22:28

-------------
Prerequisites
-------------

-  Windows device for the EXE
-  Python 3 if running as script
-  McAfee ESM running version 9.x or 10.x
-  Port 443 access to the ESM
-  ESM Credentials and proper permissions
- .mfe_ini file (covered below)

------------
Installation
------------

^^^^^^^
Windows:
^^^^^^^
Download, unzip and  at a CMD prompt.

`Windows EXE Package <https://github.com/andywalden/esmcheckds2/releases/latest>`__


^^^^^^
Linux:
^^^^^^

Install via PIP:

::

    $ pip3 install esmcheckds2


^^^^^^^^^^^^^^
Manual install 
^^^^^^^^^^^^^^
    
    
`Python project and source code <https://github.com/andywalden/esmcheckds2/releases/latest>`__

::

    $ unzip master.zip
    $ cd esmcheckds2
    $ python3 setup.py install
    
.. _configuration:
-------------
Configuration
-------------

This script requires a '.mfe\_saw.ini' file the local directory or in your 
home directory. This file contains sensitive clear text credentials for 
the McAfee ESM so it is important it be protected. 

It looks like this:

::

    [esm]
    esmhost=10.0.0.1
    esmuser=NGCP
    esmpass=SuppaSecret

An example mfe-saw.ini is available in the download or at:
https://github.com/andywalden/esmcheckds2/blob/master/mfe\_saw.ini

^^^^^^^
Windows
^^^^^^^

Go to Start \| Run and type %APPDATA% into the box and press
enter. This will open your Windows home directory. Edit the Copy the
customized .mfe\_saw.ini (period in front) to the directory.

^^^^^^^^^^
Linux\*nix
^^^^^^^^^^

The '.mfe\_saw.ini' file will either live in: $HOME or:
$XDG\_CONFIG\_HOME. You can determine which by typing:

::

    echo $XDG_CONFIG_HOME
    echo $HOME

One or both should list your home directory. If both options are
available, $XDG\_CONFIG\_HOME is the more modern and recommended choice.

-------
Thanks!
-------

Thanks to rh, tad and brooksy for testing and feedback!


----------
Disclaimer
----------

*Note: This is an **UNOFFICIAL** project and is **NOT** sponsored or
supported by **McAfee, Inc**. If you accidentally delete all of your
datasources, don't call support (or me). Product access will always be
limited to 'safe' methods and with respect to McAfee's intellectual
property. This project is released under the `ISC
license <https://en.wikipedia.org/wiki/ISC_license>`__, which is a
permissive free software license published by the Internet Systems
Consortium (ISC) and without any warranty.*
