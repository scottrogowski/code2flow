test:
	coverage run --concurrency=multiprocessing -m pytest tests -vx || exit 1
	coverage combine
	coverage report --include=lib/*.py
	coverage html --include=lib/*.py

clean:
	rm -rf build
	rm -rf dist
	rm -f out.*
	rm -rf *.egg-info
	rm -rf htmlcov


