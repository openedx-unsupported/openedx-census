###############
Open edX Census
###############

A command-line tool for scraping information from Open edX sites to
gauge how many courses they are running.

Requires Python 3.6 (or greater).

- Installation (including requirements)::

  $ make install

- Get referrer data::

  $ make fetch_referer_logs save_referer_history get_referers

- Scraping all referrers::

  $ make get_known all_refs
  $ open html/all-refs.html

- Scraping new (last 2 months) referrers::

  $ make get_known new_refs
  $ open html/new-refs.html

- Scraping all known sites::

  $ make get_known known_sites
  $ open html/sites.html

- After scraping known sites, updating the database::

  $ make post
