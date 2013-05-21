import re
import urllib2
import xml.etree.ElementTree as ET
import zipfile
import sqlite3
import datetime

APIKEY="643B2E25491987A8"
TVDB='http://thetvdb.com/api/%s/' % APIKEY
LANGUAGE='en'
NOW = datetime.datetime.now()

def parse_series_info(series):
    results = ("","")
    SERIES_PATTERNS = ( '.+(\d+)x(\d+).+', '.+[Ss](\d+)[eE](\d+).+',)
    for pattern in SERIES_PATTERNS:
        match = re.search(pattern,series)
        if match:
            results = (match.group(0), match.group(1))
            break
    return results

def write_series(show):
    conn = sqlite3.connect('meta.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO series (id,name,overview,last_update) VALUES (?,?,?,?)" \
            ,(show['id'],show['name'],show['overview'],NOW.strftime("%Y-%m-%d \
                %H:%M:%S")))
    conn.commit()

def write_episodes(episodes,series_id):
    conn = sqlite3.connect('meta.db')
    cursor = conn.cursor()
    records = []
    for episode in episodes:
        record = ()
        record = (episode['id'],series_id,episode['name'],episode['number'] \
                ,episode['aired'],episode['overview'],episode['season'] )
        records.append(record)
    cursor.executemany("INSERT INTO episodes VALUES (?,?,?,?,?,?,?)" , records)
    conn.commit()
    
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

def parse_episodes_xml(root):
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
    URL="http://thetvdb.com/api/GetSeries.php?seriesname='%s'" % name
    results = urllib2.urlopen(URL)
    root = ET.fromstring(results.read())
    series = parse_series_xml(root)
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

def get_series_episodes(show_id):
   URL = '%sseries/%s/all/%s.zip' % (TVDB,show_id,LANGUAGE)
   data = urllib2.urlopen(URL)
   tmp_file = "tmp/%s_all.zip" % show_id
   with open(tmp_file, "wb") as local_file:
        local_file.write(data.read())
   unzip_file(tmp_file)
   unzipped_file = open("tmp/en.xml")
   root = ET.fromstring(unzipped_file.read())
   parse_episodes_xml(root)


def query_episode(name,season,episode):
    conn = sqlite3.connect('meta.db')
    cursor = conn.cursor()
    cursor.execute("select id from series where name=':name'  ",
            {"name": name} )
    series_id = result.fetchone()
    if series_id:
        cursor.execute("select * from episodes where series_id=:series \
                and episode=:episode and season=:season", \
                {'series' : series_id, 'episode':episode, 'season' : season})
        episode = cursor.fetchone()
        return episode
    else:
        return ""


def main():
    series_name = "LOST"
    show = get_series_by_name(series_name)
    get_series_episodes(show['id'])


if  __name__ == '__main__':
    main()




