import urllib
import urllib2
import json
import sys
import os
import sqlite3
import numpy as np
from astropy.io import fits
from astropy import wcs

__author__ = "Natasha Hurley-Walker"

# Append the service name to this base URL, eg 'con', 'obs', etc.
BASEURL = 'http://mwa-metadata01.pawsey.org.au/metadata/'
#dbfile = 'GLEAM-X.sqlite'

def truncate(f, n):
    '''Truncates/pads a float f to n decimal places without rounding'''
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    return '.'.join([i, (d+'0'*n)[:n]])

# Function to call a JSON web service and return a dictionary: This function by Andrew Williams
def getmeta(service='obs', params=None):
    """
    Given a JSON web service ('obs', find, or 'con') and a set of parameters as
    a Python dictionary, return a Python dictionary containing the result.
    """
    if params:
        data = urllib.urlencode(params)  # Turn the dictionary into a string with encoded 'name=value' pairs
    else:
        data = ''
    # Validate the service name
    if service.strip().lower() in ['obs', 'find', 'con']:
        service = service.strip().lower()
    else:
        print "invalid service name: %s" % service
        return
    # Get the data
    try:
        print BASEURL + service + '?' + data
        result = json.load(urllib2.urlopen(BASEURL + service + '?' + data))
    except urllib2.HTTPError as error:
        print "HTTP error from server: code=%d, response:\n %s" % (error.code, error.read())
        return
    except urllib2.URLError as error:
        print "URL or network error: %s" % error.reason
        return
    # Return the result dictionary
    return result

def fake_image(metafits, imsize=5000, overwrite=False):
    hdu = fits.open(metafits)
    ra = hdu[0].header["RA"]
    dec = hdu[0].header["DEC"]
    chan = hdu[0].header["CENTCHAN"]
    dt = hdu[0].header["DATE-OBS"]
    delays = hdu[0].header["DELAYS"]
    gp = hdu[0].header["GRIDNUM"]
    pixsize=float(truncate(0.6/chan, 8))
    output="template_{0}_{1}.fits".format(gp, chan)
    if not os.path.exists(output) or overwrite is True:
        w = wcs.WCS(naxis=2)
        w.wcs.crpix = [imsize/2, imsize/2]
        w.wcs.cdelt = np.array([-pixsize, pixsize])
        w.wcs.crval = [ra, dec]
        w.wcs.ctype = ["RA---SIN", "DEC--SIN"]
        header = w.to_header()
        header["DELAYS"] = delays
        data = np.zeros([imsize, imsize], dtype=np.float32)
        new = fits.PrimaryHDU(data,header=header) #create new hdu
        newlist = fits.HDUList([new]) #create new hdulist
        newlist.writeto(output, overwrite=True)
    return output

if __name__ == "__main__":

# Download observation information from every combination of observing parameters
    chans = [69, 93, 121, 145, 169]
    decs = [18.6, 2., -13., -26.7, -40., -55., -72.]
    has = [ -1, 0, 1]
    obs_list=[]
    for dec in decs:
        for chan in chans:
            obsdata = getmeta(service='find', params={'projectid':'G0008', 'mintime':'1200000000', 'maxtime': '1400000000', 'pagesize':1000, 'cenchan':chan, 'obsname':'FDS_DEC%', 'mindec':dec-2, 'maxdec':dec+2, 'extended':1}) #'limit':10
            print len(obsdata)
# Can't search on HA so check each observation until I find one that matches
            for ha in has:
                for obs in obsdata:
# ha = Local sidereal time - ra_pointing (I hope that's accurate enough!)
                    ha_obs = (obs[11] - obs[5])/15
                    if int(round(ha_obs,0)) == ha:
# Save the obsid, the grid point number, the ra and dec, and the channel -- we'll need them later
                        obs_list.append({"obsid":obs[0], "gridpoint":obs[12], "ra":obs[5], "dec":obs[6], "chan":chan})
                        break
    
    base = os.getcwd()
    if not os.path.exists("pbeams"):
        os.mkdir("pbeams")
    for obs in obs_list:
        grid_dir = base+"/pbeams/"+str(obs["gridpoint"])
        if not os.path.exists(grid_dir):
            os.mkdir(grid_dir)
        os.chdir(grid_dir)
        if not os.path.exists(str(obs["chan"])):
            os.mkdir(str(obs["chan"]))
        os.chdir(str(obs["chan"]))
# Get the metafits files
        os.system("wget http://mwa-metadata01.pawsey.org.au/metadata/fits?obs_id={0}".format(obs["obsid"]))
        metafits = "{0}.metafits".format(obs["obsid"])
        os.rename("fits?obs_id={0}".format(obs["obsid"]),metafits)
# Make a template file
        fake_image(metafits)
