import os
import sys
import math
import urllib.request as urllib2
import urllib
import time
import math
import shutil
import subprocess
import optparse
import datetime
import csv
import re
import requests
import json
from lxml import html
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


class Plown():
    TMPFILE = os.path.join(os.path.expanduser("~"), ".plown")
    api_version = "stable"
    producttype = 'LANDSAT_8'
    secrets = '.secrets'
    def __init__(self):
        self.api = 'https://m2m.cr.usgs.gov/api/api/json/stable'
        self.session = self._create_session(api_key=None)
        credentials = open(self.secrets).read()[:-1].split(' ')
        self.url = f'{self.api}/login'
        self.api_url = f'https://earthexplorer.usgs.gov/inventory/json/v/{self.api_version}/'
        self.credentials = {'username': credentials[0], 'password': credentials[1]}
        self.user = credentials[0]
        self.password = credentials[1]

        # Fetching the API key
        data = json.dumps(self.credentials)
        r = self.session.post(self.url, data)
        response = r.json()
        print(response)
        self.api_key = response['data']
        self.session = requests.Session()

        self.url_base = "https://earthexplorer.usgs.gov/inventory/json/v/1.4.1/"
        self.url_post = self.url_base + "{}"
        self.url_get = self.url_post + "?jsonRequest={}"


    def dataset_search(self, lllat, lllon, urlat, urlon, start_date, end_date):
        payload = {
            "datasetName": "EE",
            "spatialFilter": {
                "filterType": "mbr",
                "lowerLeft": {
                        "latitude": lllat,
                        "longitude":lllon
                },
                "upperRight": {
                        "latitude": urlat,
                        "longitude":urlon
                }
            },
            "temporalFilter": {
                "start": start_date,
                "end": end_date
            }
        }

        url = os.path.join(self.api, "dataset-search/")
        data = json.dumps(payload)
        self.session.post(url, data)


    def getSceneID(self, path, row, lowerLeftLat, lowerLeftLon, upperRightLat, upperRightLon, date):
        """Get scene's IDs
        Get entity Id  and display Id required to download the scene's compressed file.
        Get IDs required to download the scene. For that, we first authenticate the user
        and get the API key, then we get the coordinates corresponding the path and row of the scene.
        The coordenates correspond to a WRS2 grid type. With them we look for the IDs corresponding
        to the given date. Finally we logout.
        """
        payload = {
		"username": self.user,
		"password": self.password,
		"authType": "EROS",
		"catalogId": "EE"
		}
        resp = requests.post(url=self.api+'login', data={'jsonRequest':json.dumps(payload)})
        print(resp)
        APIkey = self.api_key

        payload = {
		"gridType": "WRS2",
		"responseShape": "polygon",
		"path": path, #26
		"row": row #47
		}
        resp = requests.get(url=self.api+'grid2ll', params={'jsonRequest':json.dumps(payload)})
        print(resp)

        payload = {
		"datasetName": "LANDSAT_8_C1",
		"spatialFilter": {
			"filterType": "mbr",
			"lowerLeft": {
				"latitude": lowerLeftLat,
				"longitude": lowerLeftLon
				},
			"upperRight": {
				"latitude": upperRightLat,
				"longitude": upperRightLon
				}
			},
		"temporalFilter": {
			"startDate": date, #"2018-01-10"
			"endDate": date #"2018-01-10"
			},
		"maxResults": 30,
		"startingNumber": 1,
		"sortOrder": "ASC",
		"apiKey": APIkey
		}
        resp = requests.get(url=self.api+'search', params={'jsonRequest':json.dumps(payload)})
        print(resp)

        results = resp.json()['data']['results']
        info = [[re['entityId'], re['displayId']] for re in results if 'Path: ' + str(path) + ', Row: ' + str(row) in re['summary'] ]
        print(info)
        self.entityId = info[0][0]
        self.displayId = info[0][1]

        payload = {
		"apiKey": self.api_key
		}
        resp = requests.get(url=self.api+'logout', params={'jsonRequest':json.dumps(payload)})
        print(resp)


    def _create_session(self, api_key):
        api_key = self._get_api_key(api_key)

        headers = {
            'User-Agent': 'Python usgs v{}'.format(self.api_version)
        }
        if api_key:
            headers['X-Auth-Token'] = api_key

        session = requests.Session()
        session.headers.update(headers)
        retries = Retry(total=5, backoff_factor=2)
        session.mount(self.api, HTTPAdapter(max_retries=retries))

        return session


    def _get_api_key(self, api_key):
        if api_key is None and os.path.exists(self.TMPFILE):
            with open(TMPFILE, "r") as f:
                api_key_info = json.load(f)
            api_key = api_key_info['apiKey']

        return api_key


    def search(self, inidate, enddate, LowerLeftLat, LowerLeftLon, UpperRightLat, UpperRightLon):
        # Post the query
        query = {'datasetName': self.producttype,
                 'includeUnknownCloudCover': False,
                 'maxResults': 100,
                 'temporalFilter': {'startDate': inidate,
                                    'endDate': enddate},
                 'spatialFilter': {'filterType': 'mbr',
                                   'lowerLeft': {'latitude': LowerLeftLat,
                                                 'longitude': LowerLeftLon},
                                   'upperRight': {'latitude': UpperRightLat,
                                                  'longitude': UpperRightLon}
                                   },
                 'apiKey': self.api_key
                 }

        response = self.session.post(self.api_url + 'search',
                                     params={'jsonRequest': json.dumps(query)})
        response.raise_for_status()
        json_feed = response.json()
        if json_feed['error']:
            raise Exception('Error while searching: {}'.format(json_feed['error']))
        results = json_feed['data']['results']

        print('Found {} results from Landsat'.format(len(results)))
        return results


    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


    def getmetadatafiles(self, destdir, option='update'):
        print('Verifying catalog metadata files...')
        home = 'https://landsat.usgs.gov/landsat/metadata_service/bulk_metadata_files/'
        links = ['LANDSAT_8.csv', 'LANDSAT_ETM.csv', 'LANDSAT_ETM_SLC_OFF.csv', 'LANDSAT_TM-1980-1989.csv',
                'LANDSAT_TM-1990-1999.csv', 'LANDSAT_TM-2000-2009.csv', 'LANDSAT_TM-2010-2012.csv']
        for l in links:
            destfile = os.path.join(destdir, l)
            url = home+l
            if option == 'noupdate':
                if not os.path.exists(destfile):
                    print('Downloading %s for the first time...' % (l))
                    urllib2.urlretrieve(url, destfile)
            elif option == 'update':
                print(f"Downloading file {l}")
                urllib2.urlretrieve(url, destfile)


    def check_required(self, opt):
        option = self.get_option(opt)
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)


    def sizeof_fmt(self, num):
        for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return "%3.1f %s" % (num, x)
            num /= 1024.0


    def downloadChunks(self, url, rep, nom_fic):
        """ Downloads large files in pieces
        inspired by http://josh.gourneau.com
        """
        try:
            req = urllib2.urlopen(url)
            # if downloaded file is html
            if (req.info().gettype() == 'text/html'):
                print("error : file is in html and not an expected binary file")
                lines = req.read()
                if lines.find('Download Not Found') > 0:
                    raise TypeError
                else:
                    with open("error_output.html", "w") as f:
                        f.write(lines)
                        print("result saved in ./error_output.html")
                        sys.exit(-1)
            # if file too small
            total_size = int(req.info().getheader('Content-Length').strip())
            if (total_size < 50000):
                print("Error: The file is too small to be a Landsat Image")
                print(url)
                sys.exit(-1)
            print(nom_fic, total_size)
            total_size_fmt = sizeof_fmt(total_size)

            # download
            downloaded = 0
            CHUNK = 1024 * 1024 * 8
            with open(rep+'/'+nom_fic, 'wb') as fp:
                start = time.clock()
                print('Downloading {0} ({1}):'.format(nom_fic, total_size_fmt))
                while True:
                    chunk = req.read(CHUNK)
                    downloaded += len(chunk)
                    done = int(50 * downloaded / total_size)
                    sys.stdout.write('\r[{1}{2}]{0:3.0f}% {3}ps'
                                    .format(math.floor((float(downloaded)
                                                        / total_size) * 100),
                                            '=' * done,
                                            ' ' * (50 - done),
                                            sizeof_fmt((downloaded // (time.clock() - start)) / 8)))
                    sys.stdout.flush()
                    if not chunk:
                        break
                    fp.write(chunk)
        except (urllib2.HTTPError, e):
            if e.code == 500:
                pass  # File doesn't exist
            else:
                print("HTTP Error:", e.code, url)
            return False
        except (urllib2.URLError, e):
            print("URL Error:", e.reason, url)
            return False

        return rep, nom_fic


    def cycle_day(self, path):
        """ provides the day in cycle given the path number
        """
        cycle_day_path1 = 5
        cycle_day_increment = 7
        nb_days_after_day1 = cycle_day_path1+cycle_day_increment*(path-1)

        cycle_day_path = math.fmod(nb_days_after_day1, 16)
        if path >= 98:  # change date line
            cycle_day_path += 1
        return(cycle_day_path)


    def next_overpass(self, date1, path, sat):
        """ provides the next overpass for path after date1
        """
        date0_L5 = datetime.datetime(1985, 5, 4)
        date0_L7 = datetime.datetime(1999, 1, 11)
        date0_L8 = datetime.datetime(2013, 5, 1)
        if sat == 'LT5':
            date0 = date0_L5
        elif sat == 'LE7':
            date0 = date0_L7
        elif sat == 'LC8':
            date0 = date0_L8
        next_day = math.fmod((date1-date0).days-cycle_day(path)+1, 16)
        if next_day != 0:
            date_overpass = date1+datetime.timedelta(16-next_day)
        else:
            date_overpass = date1
        return(date_overpass)


    def unzipimage(self, tgzfile, outputdir):
        success = 0
        if (os.path.exists(outputdir+'/'+tgzfile+'.tgz')):
            print("\nunzipping...")
            try:
                if sys.platform.startswith('linux'):
                    subprocess.call('mkdir ' + outputdir+'/'+tgzfile, shell=True)  # Unix
                    subprocess.call('tar zxvf '+outputdir+'/'+tgzfile+'.tgz -C ' +
                                    outputdir+'/'+tgzfile, shell=True)  # Unix
                elif sys.platform.startswith('win'):
                    subprocess.call('tartool '+outputdir+'/'+tgzfile+'.tgz ' +
                                    outputdir+'/'+tgzfile, shell=True)  # W32
                success = 1
            except TypeError:
                print('Failed to unzip %s' % tgzfile)
            os.remove(outputdir+'/'+tgzfile+'.tgz')
        return success


    def read_cloudcover_in_metadata(self, image_path):
        output_list = []
        fields = ['CLOUD_COVER']
        cloud_cover = 0
        imagename = os.path.basename(os.path.normpath(image_path))
        metadatafile = os.path.join(image_path, imagename+'_MTL.txt')
        metadata = open(metadatafile, 'r')
        # metadata.replace('\r','')
        for line in metadata:
            line = line.replace('\r', '')
            for f in fields:
                if line.find(f) >= 0:
                    lineval = line[line.find('= ')+2:]
                    cloud_cover = lineval.replace('\n', '')
        return float(cloud_cover)


    def check_cloud_limit(self, imagepath, limit):
        removed = 0
        cloudcover = read_cloudcover_in_metadata(imagepath)
        if cloudcover > limit:
            shutil.rmtree(imagepath)
            print("Image was removed because the cloud cover value of " + \
                str(cloudcover) + " exceeded the limit defined by the user!")
            removed = 1
        return removed


    def find_in_collection_metadata(self, collection_file, cc_limit, date_start, date_end, wr2path, wr2row):
        print("Searching for images in catalog...")
        cloudcoverlist = []
        cc_values = []
        with open(collection_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                year_acq = int(row['acquisitionDate'][0:4])
                month_acq = int(row['acquisitionDate'][5:7])
                day_acq = int(row['acquisitionDate'][8:10])
                acqdate = datetime.datetime(year_acq, month_acq, day_acq)
                if int(row['path']) == int(wr2path) and\
                        int(row['row']) == int(wr2row) and\
                        row['DATA_TYPE_L1'] != 'PR' and\
                        float(row['cloudCoverFull']) <= cc_limit and date_start < acqdate < date_end:
                    cloudcoverlist.append(row['cloudCoverFull'] + '--' + row['sceneID'])
                    cc_values.append(float(row['cloudCoverFull']))
                else:
                    sceneID = ''
        for i in cloudcoverlist:
            if float(i.split('--')[0]) == min(cc_values):
                sceneID = i.split('--')[1]
        return sceneID



    def log(self, location, info):
        logfile = os.path.join(location, 'log.txt')
        log = open(logfile, 'w')
        log.write('\n'+str(info))
