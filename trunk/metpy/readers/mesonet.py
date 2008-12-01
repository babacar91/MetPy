#!/usr/bin/env python
import numpy as np
from numpy.ma import MaskedArray
from metpy.cbook import loadtxt, lru_cache #Can go back to numpy once it's updated

#This is a direct copy and paste of the mesonet station data avaiable at
#http://www.mesonet.org/sites/geomeso.csv
#As of November 20th, 2008
mesonet_station_table = '''
  100   2008 08 12  GEOMESO.TBL
'''

mesonet_vars = ['STID', 'STNM', 'TIME', 'RELH', 'TAIR', 'WSPD', 'WVEC', 'WDIR',
    'WDSD', 'WSSD', 'WMAX', 'RAIN', 'PRES', 'SRAD', 'TA9M', 'WS2M', 'TS10',
    'TB10', 'TS05', 'TB05', 'TS30', 'TR05', 'TR25', 'TR60', 'TR75']

#Map of standard variable names to those use by the mesonet
mesonet_var_map = {'temperature':'TAIR', 'relative humidity':'RELH',
    'wind speed':'WSPD', 'wind direction':'WDIR', 'rainfall':'RAIN',
    'pressure':'PRES'}

mesonet_inv_var_map = dict(zip(mesonet_var_map.values(),
    mesonet_var_map.keys()))

@lru_cache(maxsize=20)
def _fetch_mesonet_data(date_time=None, site=None):
    '''
    Helper function for fetching mesonet data from a remote location.
    Uses an LRU cache.
    '''
    import urllib2
    print 'fetching file'
    if date_time is None:
        import datetime
        date_time = datetime.datetime.utcnow()

    if site is None:
        data_type = 'mdf'
        #Put time back to last even 5 minutes
        date_time = date_time.replace(minute=(dt.minute - dt.minute%5),
            second=0, microsecond=0)
        fname = '%s.mdf' % date_time.strftime('%Y%m%d%H%M')
    else:
        data_type = 'mts'
        fname = '%s%s.mts' % (date_time.strftime('%Y%m%d'), site.lower())

    #Create the various parts of the URL and assemble them together
    path = '/%s/%04d/%02d/%02d/' % (data_type, date_time.year, date_time.month,
        date_time.day)
    baseurl='http://www.mesonet.org/public/data/getfile.php?dir=%s&filename=%s'

    #Open the remote location
    datafile = urllib2.urlopen(baseurl % (path+fname, fname))

    return datafile.read()

def remote_mesonet_data(date_time=None, fields=None, site=None,
    rename_fields=False):
    '''
    Reads in Oklahoma Mesonet Datafile (MDF) directly from their servers.

    date_time : datetime object
        A python :class:`datetime` object specify that date and time
        for which that data should be downloaded.  For a times series
        data, this only needs to be a date.  For snapshot files, this is
        the time to the nearest five minutes.

    fields : sequence
        A list of the variables which should be returned.  See
        :func:`read_mesonet_ts` for a list of valid fields.

    site : string
        Optional station id for the data to be fetched.  This is
        case-insensitive.  If specified, a time series file will be
        downloaded.  If left blank, a snapshot data file for the whole
        network is downloaded.

    rename_fields : boolean
        Flag indicating whether the field names given by the mesonet
        should be renamed to standard names. Defaults to False.

    Returns : array
        A nfield by ntime masked array.  nfield is the number of fields
        requested and ntime is the number of times in the file.  Each
        variable is a row in the array.  The variables are returned in
        the order given in *fields*.
    '''
    from cStringIO import StringIO
    data = StringIO(_fetch_mesonet_data(date_time, site))
    return read_mesonet_data(data, fields, rename_fields)

def read_mesonet_data(filename, fields=None, rename_fields=False):
    '''
    Reads Oklahoma Mesonet data from *filename*.

    filename : string or file-like object
        Location of data. Can be anything compatible with
        :func:`numpy.loadtxt`, including a filename or a file-like
        object.

    fields : sequence
        List of fields to read from file.  (Case insensitive)
        Valid fields are:
            STID, STNM, TIME, RELH, TAIR, WSPD, WVEC, WDIR, WDSD,
            WSSD, WMAX, RAIN, PRES, SRAD, TA9M, WS2M, TS10, TB10,
            TS05, TB05, TS30, TR05, TR25, TR60, TR75
        The default is to return all fields.

    rename_fields : boolean
        Flag indicating whether the field names given by the mesonet
        should be renamed to standard names. Defaults to False.

    Returns : array
        A nfield by ntime masked array.  nfield is the number of fields
        requested and ntime is the number of times in the file.  Each
        variable is a row in the array.  The variables are returned in
        the order given in *fields*.
    '''
    if fields:
        fields = map(str.upper, fields)
    data = loadtxt(filename, dtype=None, skiprows=2, names=True,
        usecols=fields)

    #Mask out data that are missing or have not yet been collected
#    BAD_DATA_LIMIT = -990
#    return MaskedArray(data, mask=data < BAD_DATA_LIMIT)
    
    if rename_fields:
        names = data.dtype.names
        data.dtype.names = [mesonet_inv_var_map.get(n.upper(), n)
            for n in names]

    return data

def mesonet_stid_info(info):
    'Get mesonet station information'
    names = ['stid', 'lat', 'lon']
    dtypes = ['S4','f8','f8']
    sta_table = loadtxt(StringIO(mesonet_station_table), skiprows=123,
        usecols=(1,7,8), dtype=zip(names,dtypes), delimiter=',')
    return sta_table

#    station_indices = sta_table['stid'].searchsorted(data['stid'])
#    lat = sta_table[station_indices]['lat']
#    lon = sta_table[station_indices]['lon']

if __name__ == '__main__':
    import datetime
    from optparse import OptionParser

    import matplotlib.pyplot as plt
    from metpy.vis import meteogram

    #Create a command line option parser so we can pass in site and/or date
    parser = OptionParser()
    parser.add_option('-s', '--site', dest='site', help='get data for SITE',
        metavar='SITE', default='nrmn')
    parser.add_option('-d', '--date', dest='date', help='get data for YYYYMMDD',
        metavar='YYYYMMDD', default=None)
    
    #Parse the command line options and convert them to useful values
    opts,args = parser.parse_args()
    if opts.date is not None:
        dt = datetime.datetime.strptime(opts.date, '%Y%m%d')
    else:
        dt = None
    
#    time, relh, temp, wspd, press = remote_mesonet_data(dt,
#        ['time', 'relh', 'tair', 'wspd', 'pres'], opts.site)
    data = remote_mesonet_data(dt,
        ('stid', 'time', 'relh', 'tair', 'wspd', 'pres'), opts.site, True)
    
#    meteogram(opts.site, dt, time=time, relh=relh, temp=temp, wspd=wspd,
#        press=press)
#    meteogram(opts.site, dt, time=time, relh=relh, temp=temp, wspd=wspd,
#        press=press)

    print data
    print data.dtype
#    plt.show()