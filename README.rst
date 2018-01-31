###############
Open edX Census
###############

A simple command-line tool for scraping information from Open edX sites to
gauge how many courses they are running.

Requires Python 3.6 (or greater).

Requires a sites.csv file.

Then::

    $ pip install -r requirements.pip
    python census.py --min=200
    6 sites
    ......
    http://www.xuetangx.com: 860 --> 867
    https://www.france-universite-numerique-mooc.fr: 364 --> 372
    http://courses.zsmu.edu.ua: 316 --> 328
    https://courses.openedu.tw: 251 --> 249
    https://openedu.ru: 247 --> 251
    https://puroom.net: 205 --> 221
    Found courses went from 2243 to 2288
