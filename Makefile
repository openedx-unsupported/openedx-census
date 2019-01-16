# Makefile for openedx-census

.PHONY: help dev install

help: 				## display this help message
	@echo "Please use \`make <target>' where <target> is one of:"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

dev: install			## prepare for development
	pip install -r dev-requirements.txt

install:			## install this project to run it
	pip install -e .

## Data management

# Where Ned kept it
OPENEDX_STATS_DIR = /src/edx/src/openedxstats

.PHONY: save_referer_history fetch_referrer_logs

save_referer_history:		## save current referers in the history directory
	mv -n referers.txt "history/referers_$(date -r referers.txt +"%Y%m%d").txt"

fetch_referer_logs:		## use openedxstats to get the latest referer logs
	cd $(OPENEDX_STATS_DIR) && heroku run python manage.py fetch_referrer_logs

new_sites:			## new referers in the last month to new-referers.txt
	@# Sorry for the shell craziness!
	@# date -v-1m    gives us the date of a month ago, so we can see the new referrers in the last month.
	comm -13 history/$$(ls -1 history | awk '{if ($$0 < "referers_'$$(date -v-1m '+%Y%m%d')'.txt") print}' | tail -1) referers.txt > new-referers.txt
	census refscrape --out new-refsites.pickle new-referers.txt
	census html --in new-refsites.pickle --out new-referrers.html --skip-none --only-new
