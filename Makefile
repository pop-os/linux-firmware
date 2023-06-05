# This file implements the GNOME Build API:
# http://people.gnome.org/~walters/docs/build-api.txt

FIRMWAREDIR = /lib/firmware

all:

check:
	@./check_whence.py

install:
	install -d $(DESTDIR)$(FIRMWAREDIR)
	./copy-firmware.sh $(DESTDIR)$(FIRMWAREDIR)

install-xz:
	install -d $(DESTDIR)$(FIRMWAREDIR)
	./copy-firmware.sh --xz $(DESTDIR)$(FIRMWAREDIR)

install-zst:
	install -d $(DESTDIR)$(FIRMWAREDIR)
	./copy-firmware.sh --zstd $(DESTDIR)$(FIRMWAREDIR)
