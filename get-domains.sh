# Get the domains of referers.
heroku pg:psql -a openedxstats -c "select distinct(domain) from sites_accesslogaggregate" | sed -e 's/^ //' -e 's/\.$//' | grep -E -v -f junk-referers.regex | sort | uniq > refs/referers.txt

# Get the domains of aliases.
heroku pg:psql -a openedxstats -c "select aliases from sites_site where active_end_date is null and array_length(aliases, 1) > 0;" | sed -E -e '/{/!d' -e 's/[{} ]//g' -e 's/,/\
/g' | sed -E -e 's/https?:\/\///' -e 's/\/$//' | sort | uniq > refs/aliases.txt
