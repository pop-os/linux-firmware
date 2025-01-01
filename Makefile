FIRMWAREDIR = /lib/firmware
NUM_JOBS := $(or $(patsubst -j%,%,$(filter -j%,$(MAKEFLAGS))),\
		 1)

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
	@if [ -n "${COPYOPTS}" ]; then \
		echo "COPYOPTS is not used since linux-firmware-20241017!"; \
		echo "You may want to use install{-xz,-zst} and dedup targets instead"; \
		false; \
	fi
	install -d $(DESTDIR)$(FIRMWAREDIR)
	./copy-firmware.sh -j$(NUM_JOBS) $(DESTDIR)$(FIRMWAREDIR)
	@echo "Now run \"make dedup\" to de-duplicate any firmware files"

install-xz:
	install -d $(DESTDIR)$(FIRMWAREDIR)
	./copy-firmware.sh -j$(NUM_JOBS) --xz $(DESTDIR)$(FIRMWAREDIR)
	@echo "Now run \"make dedup\" to de-duplicate any firmware files"

install-zst:
	install -d $(DESTDIR)$(FIRMWAREDIR)
	./copy-firmware.sh -j$(NUM_JOBS) --zstd $(DESTDIR)$(FIRMWAREDIR)
	@echo "Now run \"make dedup\" to de-duplicate any firmware files"

clean:
	rm -rf release dist
