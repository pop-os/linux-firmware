# This file implements the GNOME Build API:
# http://people.gnome.org/~walters/docs/build-api.txt

FIRMWAREDIR = /lib/firmware

all:

check:
	@if ! command -v pre-commit >/dev/null; then \
		echo "Install pre-commit to check files"; \
		exit 1; \
	fi
	@pre-commit run --all-files

dist:
	@mkdir -p release dist
	./copy-firmware.sh release
	@TARGET=linux-firmware_`git describe`.tar.gz; \
	cd release && tar -czf ../dist/$${TARGET} *; \
	echo "Created dist/$${TARGET}"
	@rm -rf release

deb:
	./build_packages.py --deb

rpm:
	./build_packages.py --rpm

dedup:
	./dedup-firmware.sh $(DESTDIR)$(FIRMWAREDIR)

install:
	install -d $(DESTDIR)$(FIRMWAREDIR)
	./copy-firmware.sh $(DESTDIR)$(FIRMWAREDIR)
	@echo "Now run \"make dedup\" to de-duplicate any firmware files"

install-xz:
	install -d $(DESTDIR)$(FIRMWAREDIR)
	./copy-firmware.sh --xz $(DESTDIR)$(FIRMWAREDIR)
	@echo "Now run \"make dedup\" to de-duplicate any firmware files"

install-zst:
	install -d $(DESTDIR)$(FIRMWAREDIR)
	./copy-firmware.sh --zstd $(DESTDIR)$(FIRMWAREDIR)
	@echo "Now run \"make dedup\" to de-duplicate any firmware files"

clean:
	rm -rf release dist
