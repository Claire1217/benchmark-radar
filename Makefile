.PHONY: test check build generate serve

test:
	python3 -m unittest discover -s pipeline/tests -v

check:
	python3 pipeline/validate_data.py
	node --check web/app.js
	node --check web/details.js

build: check
	python3 pipeline/build_github_pages.py
	python3 pipeline/validate_static_site.py

generate:
	python3 pipeline/apply_overrides.py
	python3 pipeline/build_library_records.py
	python3 pipeline/generate_public_index.py
	python3 pipeline/generate_library_index.py
	python3 pipeline/generate_domain_trends.py
	python3 pipeline/generate_awesome.py

serve: build
	python3 -m http.server 8000 --directory _site
