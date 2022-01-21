# Makefile for openedx-census

.PHONY: help dev install clean

help: 				## display this help message
	@echo "Please use \`make <target>' where <target> is one of:"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

dev: install			## prepare for development
	pip install -r requirements/test.txt

install:			## install this project to run it
	pip install -e .
	mkdir -p refs state html

clean:				## remove all transient files
	rm refs/*.* state/*.* html/*.* course-ids.txt update.json
	rm -rf save

## Data management

# Where Ned kept it
#OPENEDX_STATS_DIR = /src/edx/src/openedxstats
OPENEDX_STATS_DIR = /home/e0d/Documents/git/openedx/openedx-census/openedxstats

.PHONY: save_referer_history fetch_referrer_logs get_referers get_known

ALL_REFS = refs/referers.txt

save_referer_history:		## save current referers in the history directory
	mv -n $(ALL_REFS) "refs/history/referers_$$(date -r $(ALL_REFS) +"%Y%m%d").txt"

fetch_referer_logs:		## use openedxstats to get the latest referer logs
	cd $(OPENEDX_STATS_DIR) && heroku run --app openedxstats python manage.py fetch_referrer_logs

get_referers:			## get the latest referrers and aliases
	./get-domains.sh

get_known:			## pull down the csv of known sites
	census getcsv

## Scraping

.PHONY: new_sites all_sites known_sites post

NEW_REFS = refs/new-refs.txt
NEW_PICKLE = state/new-refs.pickle

$(NEW_REFS): $(ALL_REFS)
	@# Sorry for the shell craziness!
	@# date -d '2 months ago'    gives us the date of two months ago, so we can see the new referrers.
	comm -13 refs/history/$$(ls -1 refs/history | awk '{if ($$0 < "referers_'$$(date -d '2 months ago' '+%Y%m%d')'.txt") print}' | tail -1) $(ALL_REFS) > $(NEW_REFS)

new_refs: $(NEW_REFS) new_scrape new_html	## scrape new referrers in the last 2 months

new_scrape:
	census scrape --in $(NEW_REFS) --out $(NEW_PICKLE)

new_html:
	census html --in $(NEW_PICKLE) --out html/new-refs.html --skip-none --only-new
	census html --in $(NEW_PICKLE) --out html/new-refs-full.html --skip-none --only-new --full

ALL_PICKLE = state/all-refs.pickle

all_refs: all_scrape all_html	## scrape all referrers ever

all_scrape:
	census scrape --in $(ALL_REFS) --out $(ALL_PICKLE)

all_html:
	census html --in $(ALL_PICKLE) --out html/all-refs.html --skip-none --only-new
	census html --in $(ALL_PICKLE) --out html/all-refs-full.html --only-new --full
	census html --in $(ALL_PICKLE) --out html/aall-refs.html --skip-none
	census html --in $(ALL_PICKLE) --out html/aall-refs-full.html --full

known_sites:			## scrape the known sites
	census scrape --gone
	census summary
	census html --out html/sites.html
	census html --out html/sites-full.html --full
	census json

post:				## update the stats site with the latest known_sites scrape
	census post

sheet:
	census sheet --in $(ALL_PICKLE)

## Requirements maintenance

.PHONY: requirements upgrade test

requirements:
	pip install -r requirements/test.txt

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	pip install -q -r requirements/pip_tools.txt
	pip-compile --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/test.txt requirements/test.in
	pip-compile --upgrade -o requirements/tox.txt requirements/tox.in
	pip-compile --upgrade -o requirements/ci.txt requirements/ci.in

test: requirements
	tox
