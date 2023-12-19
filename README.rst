###############
Open edX Census
###############

.. warning::

   This repository is no longer being actively developed or maintained.

A command-line tool for scraping information from Open edX sites to
gauge how many courses they are running.

Before using, create (or check) the file census/keys.py.  It must
define two variables, "username" and "password", to use to access
the stats site.  That file is not committed to git.

Requires Python 3.8 (or greater).

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
