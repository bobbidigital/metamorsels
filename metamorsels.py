import re
import urllib2
import xml.etree.ElementTree as ET
import zipfile
import sqlite3
import datetime
import os
import urllib
import codecs

APIKEY="643B2E25491987A8"
TVDB='http://thetvdb.com/api/%s/' % APIKEY
LANGUAGE='en'
NOW = datetime.datetime.now()

def get_db_cursor():
    conn = sqlite3.connect('meta.db',isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn.cursor()

def parse_series_info(series):
    results = ("","")
    SERIES_PATTERNS = ( ".+(\d+)x(\d+).+", ".+[Ss](\d+)[eE](\d+).+",
                        "^[Ss](\d+)[eE](\d+).+")
    for pattern in SERIES_PATTERNS:
        match = re.search(pattern,series)
        if match:
            results = (match.group(1), match.group(2))
            break
    return results

def write_series(show):
    cursor = get_db_cursor()
    cursor.execute("INSERT INTO series (id,name,overview,last_update) VALUES (?,?,?,?)" \
            ,(show['id'],show['name'],show['overview'],NOW.strftime("%Y-%m-%d \
                %H:%M:%S")))

def write_episodes(episodes,series_id):
    cursor = get_db_cursor()
    records = []
    for episode in episodes:
        record = ()
        record = (episode['id'],series_id,episode['name'],episode['number'] \
                ,episode['aired'],episode['overview'],episode['season'] )
        records.append(record)
    cursor.executemany("INSERT INTO episodes VALUES (?,?,?,?,?,?,?)" , records)

def parse_series_xml(root):
    series = []
    for elem in  root:
        data = {}
        data['name'] = elem[2].text
        data['id'] = elem[0].text
        for field in (('overview',4),('banner',3)):
            try:
                data[field[0]] = elem[field[1]].text
            except IndexError:
                data[field[0]] = "Not Provided"
        series.append(data)
    return series

def create_episodes(root):
    series_id = root[0][0].text
    episodes = []
    FIELDS = (
                ('id',0),
                ('name',9),
                ('number',10),
                ('aired',11),
                ('overview',15),
                ('season',2)
             )
    for elem in root:
        if elem.tag == 'Episode':
            episode = {}
            for field in FIELDS:
                try:
                    episode[field[0]] = elem[field[1]].text
                except InexError:
                    episode[field[0]] = 'Not Provided'

                if episode[field[0]] == '':
                    episode[field[0]] == 'Not Provided'
            episodes.append(episode)
    write_episodes(episodes,series_id)

def is_match(a,b):
    return a.upper() == b.upper()

def get_show_from_user(series):
    print "Couldn't get a series match"
    return ""

def get_series_by_name(name):
    cursor = get_db_cursor()
    series = query_series(name)
    if series:
        return series
    else:
        parameters = urllib.urlencode({ 'seriesname' : name })
        URL="http://thetvdb.com/api/GetSeries.php?%s'" % parameters
        show = {}
        try:
            results = urllib2.urlopen(URL)
            data = results.read()
            root = ET.fromstring(data)
            series = parse_series_xml(root)
        except HTTPError:
            series = None

        if series:
            if is_match(series[0]['name'],name):
                show = series[0]
            else:
                show = get_show_from_user(series)
            write_series(show)
        return show

def unzip_file(filename):
    with zipfile.ZipFile(filename) as zf:
        for member in zf.infolist():
                zf.extract(member,"tmp/")

def get_episode(series_id,season,episode,recursive_call=False):
    cursor = get_db_cursor()
    parameters = (series_id,season,episode)
    cursor.execute("select * from episodes where series_id=? and season=? \
            and number=?", parameters)
    result = cursor.fetchone()
    if not result:
        update_series(series_id)
        if not recursive_call:
            result = get_episode(series_id,season,episode,True)
    return result

def update_series(series_id):
    episodes = get_series_episodes(series_id)
    cursor = get_db_cursor()
    parameters = (series_id,)
    cursor.execute("delete from episodes where series_id=?", parameters)
    create_episodes(episodes)

def get_series_episodes(show_id):
   URL = '%sseries/%s/all/%s.zip' % (TVDB,show_id,LANGUAGE)
   try:
       data = urllib2.urlopen(URL)
       tmp_file = "tmp/%s_all.zip" % show_id
       with open(tmp_file, "wb") as local_file:
            local_file.write(data.read())
       unzip_file(tmp_file)
       unzipped_file = open("tmp/en.xml")
       root = ET.fromstring(unzipped_file.read())
       return root
   except:
       pass

def query_series(name):
    cursor = get_db_cursor()
    parameters = (name.upper(),)
    cursor.execute("select * from series where upper(name)=?", parameters)
    result = cursor.fetchone()
    return result

def query_episode(name,season,episode):
    cursor = get_db_cursor()
    parameters = (name,)
    cursor.execute("select id from series where name=?" , parameters)
    series_id = cursor.fetchone()
    parameters = (series_id[0],episode,season)
    if series_id:
        cursor.execute("select * from episodes where series_id=? \
                and number=? and season=?",  parameters)
        episode = cursor.fetchone()
        return episode
    else:
        return ""


def create_database():
    cursor = get_db_cursor()
    cursor.execute("CREATE TABLE episodes(id INTEGER NOT NULL, series_id INTEGER \
        NOT NULL, name CHAR(100) NOT NULL, number INTEGER NOT NULL, first_aired \
        DATETIME, overview CHAR(1500), season integer not null")

    cursor.execute("CREATE TABLE series (id INTEGER NOT NULL, name CHAR(50) \
    NOT NULL collate nocase, overview CHAR(500), \
    last_update DATETIME NOT NULL, \ banner CHAR(50))")


def isHidden(directory):
    return directory[0] == '.'

def process_dir(directory,names):
   series = os.path.split(directory)
   if isHidden(series[1]):
       return
   series = get_series_by_name(series[1])
   if series:
       #get_series_episodes(series['id'])
       for name in names:
           episode_details = parse_series_info(name)
           episode =  get_episode(series['id'],episode_details[0],\
                   episode_details[1])
           #episode = query_episode(series['name'],episode_details[0],episode_details[1])
           if not episode:
               episode = { 'season' : episode_details[0],
                           'number' : episode_details[1],
                           'name' : 'Not Provided',
                           'overview' : 'Not Provided',
                           'first_aired' : '01/01/01' }
           create_metadata(series,episode,name,directory)
   else:
       print "Failed to retrieve series info for %s \n" % series[1]


def create_metadata(series,episode,name,directory):
    path = os.path.join(directory, ".meta")
    if not os.path.exists(path):
        os.makedirs(path)
    filename = "%s.txt" % name
    path = os.path.join(path,filename)
    if not os.path.exists(path):
       fd = codecs.open(path,"w","utf-8")
       fd.write("title : %s\n" % series['name'])
       fd.write("seriesTitle : %s\n" % series['name'])
       fd.write("episodeTitle : %s\n" % episode['name'])
       if episode['number'] < 10:
           episode_number = "0%s" % episode['number']
       else:
           episode_number = "%s" % episode['number']
       fd.write("episodeNumber : %s%s\n" % (episode['season'],episode_number))
       fd.write("isEpisode : true\n")
       fd.write("description : %s\n" % episode['overview'])
       fd.write("seriesId : SH%s\n" % series['id'])
       if episode['first_aired']:
           fd.write("originalAirDate : %sT00:00:00Z\n" % episode['first_aired'])
           fd.write("time : %sT00:00:00Z\n" % episode['first_aired'])
       fd.close()


def main():
    DIR = "/Users/jeffery.smith/Movies"
    #DIR="/Users/jeff/Movies/Tivo/tv"
    for root, subdir, files in os.walk(DIR):
        if root == DIR:
            continue
        if not isHidden(root):
            process_dir(root,files)

if  __name__ == '__main__':
    main()




