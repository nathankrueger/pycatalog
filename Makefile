PYCAT_CMD=./pycatalog.py
CURRENT_TEXT_DEFS=text_defs_2016
OBFUSCATED_MARKER_FILE=.obfuscated

# Git stuff
co:
	git add $(FILES)

ci:
	git commit

rm:
	git rm $(FILES)

push:
	git push origin master

pull:
	git pull origin master

revert:
	git reset

# PC stuff
keys:
	$(PYCAT_CMD) --dump_keywords

load:
	$(PYCAT_CMD) --input=$(CURRENT_TEXT_DEFS)

reload: clean load

clean:
	touch catalog.db default.m3u $(OBFUSCATED_MARKER_FILE)
	rm catalog.db default.m3u $(OBFUSCATED_MARKER_FILE)
