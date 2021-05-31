test:
	pytest --cov-report=html --cov=lib -x

clean:
	rm -rf build
	rm -rf dist
	rm -f out.*
	rm -rf *.egg-info
	rm -rf htmlcov


