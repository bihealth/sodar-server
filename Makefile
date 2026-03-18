SHELL = /bin/bash
MANAGE = python manage.py
define USAGE=
@echo -e
@echo -e "Usage:"
@echo -e "\tmake black [arg=--<arg>]                    -- format python with black"
@echo -e "\tmake flake                                  -- run flake8"
@echo -e "\tmake js-beautify arg=<path>                 -- run js-beautify on JQuery file(s)"
@echo -e "\tmake samplesheets_vue                       -- start samplesheets Vue2 app for development"
@echo -e "\tmake samplesheets_vue3                      -- start samplesheets Vue3 app for development"
@echo -e "\tmake serve [arg=sync]                       -- start Django server for development"
@echo -e "\tmake spectacular                            -- generate OpenAPI schemas with drf-spectacular"
@echo -e "\tmake sync_taskflow                          -- sync taskflow"
@echo -e "\tmake test [arg=<test_object>]               -- run django tests"
@echo -e "\tmake test_coverage                          -- run django tests and provide coverage html report"
@echo -e "\tmake test_samplesheets_vue [arg=<target>]   -- run samplesheets Vue2 app tests"
@echo -e "\tmake test_samplesheets_vue3 [arg=<target>]  -- run samplesheets Vue3 app tests"
@echo -e
endef

default: usage

# Argument passed from commandline, optional for some rules, mandatory for others.
arg =


.PHONY: black
black:
	black . $(arg)


.PHONY: celery
celery:
	celery -A config worker -l info --beat


.PHONY: collectstatic
collectstatic:
	$(MANAGE) collectstatic --no-input


.PHONY: flake
flake:
	flake8 .


.PHONY: js-beautify
js-beautify:
	js-beautify -anr -s 2 -w 80 $(arg)


.PHONY: samplesheets_vue
samplesheets_vue:
	npm run --prefix samplesheets/vueapp serve


.PHONY: samplesheets_vue3
samplesheets_vue3:
	npm run --prefix samplesheets/vue3app dev


.PHONY: serve
ifeq ($(arg),sync)
serve: sync_taskflow
else
serve:
endif
	$(MANAGE) runserver 0.0.0.0:8000 --settings=config.settings.local


.PHONY: spectacular
spectacular:
	$(MANAGE) spectacular --color $(arg)


.PHONY: sync_taskflow
sync_taskflow:
	$(MANAGE) synctaskflow


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


.PHONY: test_samplesheets_vue3
test_samplesheets_vue3:
	npm run --prefix samplesheets/vue3app test:unit $(arg)


.PHONY: usage
usage:
	$(USAGE)
