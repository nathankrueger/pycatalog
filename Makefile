PYCAT_CMD=./pycatalog.py
CURRENT_TEXT_DEFS=text_defs_2017
OBFUSCATED_MARKER_FILE=.obfuscated
GIT_REPO=https://github.com/nathankrueger/pycatalog
RECENT_FILE_NUM=100
SYNC_DIR=./
TEXT_EDITOR_CMD=open -a TextWrangler

ec:
	gpg -c $(FILE)

dc:
	gpg $(FILE)

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

repo:
	open $(GIT_REPO)

# PC stuff
keys:
	$(PYCAT_CMD) --dump_keywords

sync_recent:
	$(PYCAT_CMD) --all --timesort --list --no_play --limit=$(RECENT_FILE_NUM) | xargs -I % cp % $(SYNC_DIR)

update:
	$(PYCAT_CMD) --update=$(CURRENT_TEXT_DEFS)

load:
	$(PYCAT_CMD) --input=$(CURRENT_TEXT_DEFS)

audit:
	$(PYCAT_CMD) --audit_text=$(CURRENT_TEXT_DEFS)
	$(TEXT_EDITOR_CMD) $(CURRENT_TEXT_DEFS)

reload: clean load

clean:
	touch catalog.db default.m3u $(OBFUSCATED_MARKER_FILE)
	rm catalog.db default.m3u $(OBFUSCATED_MARKER_FILE)
