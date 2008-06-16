The acx loads the firmware marked "default", unless you pass it another
version using the firmware_ver=XXXX module parameter. If your card requires
other than the default, please file a bug report to Ubuntu with the output
of "lspci -vv", "lspci -vvn" and "lsusb".

acx100 USB		1.0.7
acx100 USB		1.0.9		(default)

acx100 PCI		1.7.0
acx100 PCI		1.9.8.b		(default)

acx111 PCI		0.1.0.11
acx111 PCI		0.4.11.4
acx111 PCI		0.4.11.9
acx111 PCI		1.2.0.30
acx111 PCI		2.3.1.31	(default)
