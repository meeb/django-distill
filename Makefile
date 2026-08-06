python=/usr/bin/env python


test:
		uv run manage.py testsuite


lint:
		uvx ruff check


format:
		uvx ruff format


runserver:
		uv run manage.py runserver
