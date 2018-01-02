#!/usr/bin/env bash
coverage run --source="." manage.py test -v 2 --settings=config.settings.test_local
coverage report
coverage html
