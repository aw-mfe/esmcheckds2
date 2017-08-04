McAfee SIEM Check Datasources: esmdscheck2
==========================================

This script queries a McAfee ESM for inactive data sources.

**Updates from esm-check-ds v1:**

-  Hundeds of times faster - completely rewritten to perform mininum
   number of queries instead of querying for every datasource.

-  McAfee ESM 9.x and 10.x versions are now supported in a single
   script.

-  Additional information provided for each datasource (IP, Receiver
   name)

-  Output changed to CSV for easy manipulation.

-  Compiled into an executable for easy use on Windows.

-  Centralized ini file to home directory instead of script directory
   for increased security.

This is written in Python 3; directions on how to create a virtual
environment to run the script on both Linux and Windows are available
at:
https://community.mcafee.com/people/andy777/blog/2016/11/29/installing-python-3

The script requires a mfe\_saw.ini file for the credentials. See
installation notes to determine which directory it should be placed for
your operating system.

Usage
-----

::

        Usage: esmcheckds2 (days|hours|minutes)=x

**Examples:**

::

        esmcheckds2 days=2
        esmcheckds2 hours=6
        esmcheckds2 minutes=60

**Output is csv:**

::

        name,ip,model,rec_name,last_time

Redirect output to file and import as a spreadsheet.

Output Sample:

::

    $ python esmcheckds2 hours=24

    Datasources with no events since: 07/28/2017 13:25:04
    001w7tie,172.22.117.20,Windows Event Log - WMI,Receiver (events),never
    ATD_test,10.75.113.5,Advanced Threat Defense,Receiver (events),12/01/2015 17:43:19
    esx000,172.22.119.34,VMware,Receiver (events),10/02/2015 15:19:05
    esx001,172.22.119.35,VMware,Receiver (events),10/02/2015 15:19:05
    esx002,172.22.119.36,VMware,Receiver (events),never
    esx003,172.22.119.37,VMware,Receiver (events),12/08/2015 19:22:28
    esx004,172.22.119.38,VMware,Receiver (events),12/08/2015 19:22:28

Prerequisites
-------------

-  Python 3 if running as script
-  Windows platform if running as exe
-  McAfee ESM running version 9.x or 10.x
-  Port 443 access to the ESM
-  NGCP credentials

Installation
------------

To install esmcheckds2, you can download the script or exe from this
site or install via PIP.

`Windows EXE
Package <https://github.com/andywalden/esmcheckds2/files/1185928/esmdscheck2.zip>`__

`Python project and source
code <https://github.com/andywalden/esmcheckds2/archive/master.zip>`__

Or install via PIP:

::

    $ pip install esmcheckds2

Configuration
-------------

This script requires a '.mfe\_saw.ini' file in your home directory. This
file contains sensitive clear text credentials for the McAfee ESM so it
is important it be protected. This is same ini file will be referenced
by all future ESM related projects also.

It looks like this:

::

    [esm]
    esmhost=10.0.0.1
    esmuser=NGCP
    esmpass=SuppaSecret

An example mfe-saw.ini is available in the download or at:
https://github.com/andywalden/esmcheckds2/blob/master/mfe\_saw.ini

**Windows** 

Go to Start \| Run and type %APPDATA% into the box and press
enter. This will open your Windows home directory. Edit the Copy the
customized .mfe\_saw.ini (period in front) to the directory.

**Linux \*nix**

The '.mfe\_saw.ini' file will either live in: $HOME or:
$XDG\_CONFIG\_HOME. You can determine which by typing:

::

    echo $XDG_CONFIG_HOME
    echo $HOME

One or both should list your home directory. If both options are
available, $XDG\_CONFIG\_HOME is the more modern and recommended choice.

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
