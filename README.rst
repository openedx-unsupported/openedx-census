###############
Open edX Census
###############

A simple command-line tool for scraping information from Open edX sites to
gauge how many courses they are running.

Requires Python 3.6 (or greater).

Requires a sites.csv file.

Then::

    $ pip install -r requirements.pip
    $ python census.py --min=100
    14 sites
    ..............
    Site(url='http://www.xuetangx.com', latest_courses=860, current_courses=866, error=None)
    Site(url='https://www.france-universite-numerique-mooc.fr', latest_courses=364, current_courses=371, error=None)
    Site(url='http://courses.zsmu.edu.ua', latest_courses=316, current_courses=328, error=None)
    Site(url='https://courses.openedu.tw', latest_courses=251, current_courses=249, error=None)
    Site(url='https://openedu.ru', latest_courses=247, current_courses=251, error=None)
    Site(url='https://puroom.net', latest_courses=205, current_courses=221, error=None)
    Site(url='http://gacco.org', latest_courses=179, current_courses=182, error=None)
    Site(url='http://www.memooc.hu', latest_courses=153, current_courses=153, error=None)
    Site(url='http://oldtsinghua.xuetangx.com', latest_courses=130, current_courses=0, error=None)
    Site(url='http://www.emadras.ir', latest_courses=130, current_courses=0, error=None)
    Site(url='http://docmode.org', latest_courses=121, current_courses=131, error=None)
    Site(url='http://doroob.sa', latest_courses=113, current_courses=0, error=None)
    Site(url='https://lms.mitx.mit.edu', latest_courses=111, current_courses=122, error=None)
    Site(url='https://www.millionlights.org', latest_courses=106, current_courses=0, error=None)
    Found courses went from 2807 to 2874
