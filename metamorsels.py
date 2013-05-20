import re
import urllib2
import xml.etree.ElementTree as ET


def parse_series_info(series):
    results = ("","")
    SERIES_PATTERNS = ( '.+(\d+)x(\d+).+', '.+[Ss](\d+)[eE](\d+).+',) 
    for pattern in SERIES_PATTERNS:
        match = re.search(pattern,series)
        if match:
            results = (match.group(0), match.group(1) 
            break
    return results

def parse_xml(root):
    data['name'] = root[0][2].text
    data['overview'] = root[0][4].text
    data['banner'] = root[0][3].text
    data['id'] = root[0][0].text
    return data

def get_series_by_name(name):
    URL="http://thetvdb.com/api/GetSeries.php?seriesname='%s'" % name
    results = urllib2.urlopen(URL)
    root = ET.fromstring(results)
    data = parse_xml(root)
    

