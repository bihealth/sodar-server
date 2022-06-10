SHELL = /bin/bash
MANAGE = python manage.py
define USAGE=
@echo -e
@echo -e "Usage:"
@echo -e "\tmake black [arg=--<arg>]                    -- format python with black"
@echo -e "\tmake serve [arg=sync]                       -- start server"
@echo -e "\tmake celery                                 -- start celery & celerybeat"
@echo -e "\tmake demo                                   -- start demo server"
@echo -e "\tmake samplesheets_vue                       -- start samplesheet vue.js app"
@echo -e "\tmake collectstatic                          -- run collectstatic"
@echo -e "\tmake test [arg=<test_object>]               -- run all django tests or specify module/class/function"
@echo -e "\tmake test_coverage                          -- run all django tests and provide coverage html report"
@echo -e "\tmake test_samplesheets_vue [arg=<target>]   -- run all samplesheets vue app tests or specify target"
@echo -e "\tmake sync_taskflow                          -- sync taskflow"
@echo -e
endef

# Argument passed from commandline, optional for some rules, mandatory for others.
arg =


.PHONY: black
black:
	black . -l 80 --skip-string-normalization \
	--exclude ".git|.venv|.tox|env|src|docs|migrations|versioneer.py|_version.py" $(arg)


.PHONY: sync_taskflow
sync_taskflow:
	$(MANAGE) synctaskflow


.PHONY: serve
ifeq ($(arg),sync)
serve: sync_taskflow
else
serve:
endif
	$(MANAGE) runserver 0.0.0.0:8000 --settings=config.settings.local


.PHONY: celery
celery:
	celery -A config worker -l info --beat


.PHONY: demo
demo:
	DJANGO_DEBUG=0 $(MANAGE) runserver --settings=config.settings.local --insecure


.PHONY: samplesheets_vue
samplesheets_vue:
	npm run --prefix samplesheets/vueapp serve


.PHONY: collectstatic
collectstatic:
	$(MANAGE) collectstatic --no-input


.PHONY: test
test: collectstatic
	$(MANAGE) test -v 2 --settings=config.settings.test $(arg)


.PHONY: test_coverage
test_coverage: collectstatic
	coverage run --source="." manage.py test -v 2 --settings=config.settings.test
	coverage report
	coverage html


.PHONY: test_samplesheets_vue
test_samplesheets_vue:
	npm run --prefix samplesheets/vueapp test:unit $(arg)


.PHONY: usage
usage:
	$(USAGE)

