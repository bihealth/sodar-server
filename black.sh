#!/usr/bin/env bash
black . -l 80 --skip-string-normalization --exclude ".git|.venv|env|src|docs_dev|docs_manual|migrations|versioneer.py" $1
