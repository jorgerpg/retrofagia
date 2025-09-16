.PHONY: up down logs build test

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build backend

logs:
	docker compose logs -f backend

test:
	./tests_retrofagia.sh
