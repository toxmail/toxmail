.PHONY: docs build test

ifndef VTENV_OPTS
VTENV_OPTS = "--no-site-packages"
endif

build:	
	virtualenv $(VTENV_OPTS) .
	bin/python setup.py develop

test:	bin/nosetests
	bin/nosetests -x toxsmtp

bin/nosetests: bin/python
	bin/pip install nose

