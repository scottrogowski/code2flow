build:
	rm -rf dist
	python3 setup.py sdist

test:
	pytest --cov-report=html --cov=code2flow -x

clean:
	rm -rf build
	rm -rf dist
	rm -f out.*
	rm -rf *.egg-info
	rm -rf htmlcov


