import re
import sys
import urllib.parse

import requests

from keys import username, password


site = sys.argv[1]
with open('update.json') as f:
    data = f.read()

with requests.Session() as s:
    login_url = urllib.parse.urljoin(site, "/login/")
    resp = s.get(login_url)
    m = re.search(r"name='csrfmiddlewaretoken' value='([^']+)'", resp.text)
    if m:
        csrftoken = m.group(1)
    resp = s.post(login_url, data={'username': username, 'password': password, 'csrfmiddlewaretoken': csrftoken})

    bulk_url = urllib.parse.urljoin(site, "/sites/bulk/")
    resp = s.post(bulk_url, data=data)
    print(resp.text)
