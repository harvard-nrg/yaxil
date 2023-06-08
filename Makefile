init:
	pip install pipenv --upgrade
	pipenv install --dev --skip-lock
test:
	pipenv run py.test tests/test.py
dist:
	python setup.py sdist bdist_wheel --universal
publish:
	pip install 'twine>=1.5.0' wheel
	python setup.py sdist bdist_wheel --universal
	twine upload dist/*.whl
	rm -fr build dist .egg yaxil.egg-info
