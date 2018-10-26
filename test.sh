#!/usr/bin/env bash
./manage.py collectstatic
./manage.py test -v 2 --settings=config.settings.test_local $1