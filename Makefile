THIS_FILE := $(lastword $(MAKEFILE_LIST))
.PHONY: help build run stop restart  destroy log shell

help:
	make -pRrq  -f $(THIS_FILE) : 2>/dev/null |	awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

build:
	docker compose -f docker-compose.prod.yaml build $(c)

run:
	docker compose -f docker-compose.prod.yaml up -d $(c)

stop:
	docker compose -f docker-compose.prod.yaml stop $(c)

restart:
	docker compose -f docker-compose.prod.yaml stop $(c)
	docker compose -f docker-compose.prod.yaml up -d $(c)
destroy:
	docker compose -f docker-compose.prod.yaml down -v $(c)
log:
	docker compose -f docker-compose.prod.yaml logs --tail=150 -f poll-backend

shell:
	docker compose -f docker-compose.prod.yaml exec poll-backend /bin/bash

#manage:
#	docker-compose -f docker-compose.yaml exec poll-app python manage.py $(c)
#makemigrations:
#	docker-compose -f docker-compose.yaml exec pool-app python manage.py makemigrations
#migrate:
#	docker-compose -f docker-compose.yaml exec pool-app python manage.py migrate
#test:
#	docker-compose -f docker-compose.yaml exec pool-app python manage.py test


