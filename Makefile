test:
	coverage run --concurrency=multiprocessing -m pytest tests -vx || exit 1
	coverage combine
	coverage report --include=code2flow/*.py
	coverage html --include=code2flow/*.py
