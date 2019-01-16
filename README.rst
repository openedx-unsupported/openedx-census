###############
Open edX Census
###############

A command-line tool for scraping information from Open edX sites to
gauge how many courses they are running.

Requires Python 3.6 (or greater).

- Installation (including requirements)::

  $ make install

- Scraping all referrers::

  $ make get_referers get_known all_sites
  $ open html/refsites.html         # to see the results

- Scraping all known sites::

  $ make get_known known_sites
  $ open html/sites.html            # to see the results

- After scraping known sites, updating the database::

  $ make post
