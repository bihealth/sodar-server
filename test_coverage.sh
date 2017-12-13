#!/usr/bin/env bash
coverage run --source="." manage.py test -v 2 --settings=config.settings.test_local --liveserver 0.0.0.0:8081-9000
coverage report
