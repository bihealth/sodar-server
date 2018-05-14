#!/usr/bin/env bash
if [ $# -gt 0 ] && [ $1 = "sync" ]; then
    ./manage.py synctaskflow
fi
./manage.py runserver --settings=config.settings.local
