heroku pg:psql -a openedxstats -c "select distinct(domain) from sites_accesslogaggregate" | sed -e 's/^ //' -e 's/\.$//' | grep -E -v -f junk-referers.regex | sort | uniq > referer2.txt
