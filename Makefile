# Makefile for openedx-census

.PHONY: help dev install

help: 				## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

dev: install			## prepare for development
	pip install -r dev-requirements.txt

install:			## install this project to run it
	pip install -e .
