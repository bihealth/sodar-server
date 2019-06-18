#!/usr/bin/env bash
export DJANGO_DEBUG=0
./manage.py runserver --settings=config.settings.local --insecure
