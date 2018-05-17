###############
Open edX Census
###############

A simple command-line tool for scraping information from Open edX sites to
gauge how many courses they are running.

Requires Python 3.6 (or greater).

- Installation (including requirements)::

  $ pip install -e .

- Scraping all referrers::

  $ . get-domains.sh
  $ census refscrape --out refsites.pickle referers.txt
  $ census html --in refsites.pickle --out referrer-sites.html --skip-none --only-new
  $ open referrer-sites.html    # to see the results

- Scraping all known sites::

  $ census getcsv && census scrape --gone && census summary && census html
  $ open sites.html             # to see the results

- After scraping known sites, updating the database::

  $ census json && census post
