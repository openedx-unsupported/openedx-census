###############
Open edX Census
###############

A simple command-line tool for scraping information from Open edX sites to
gauge how many courses they are running.

Requires Python 3.6 (or greater).

- Scraping all referrers::

  $ . get-domains.sh
  $ ./census.py refscrape --out refsites.pickle referers.txt
  $ ./census.py html --in refsites.pickle --out referrer-sites.html --skip-none --only-new

- Scraping all known sites::

  $ ./census.py getcsv && ./census.py scrape --gone && ./census.py summary && ./census.py html

- After scraping known sites, updating the database::

  $ ./census.py json && ./census.py post
