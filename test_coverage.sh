#!/usr/bin/env bash
./manage.py collectstatic --no-input
coverage run --source="." manage.py test -v 2 --settings=config.settings.test_local
coverage report
coverage html
