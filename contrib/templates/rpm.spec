Name:           {{ package }}
Version:        {{ version }}
Release:        1%{?dist}
Summary:        Linux Firmware (upstream)
License:        Redistributable, no modification permitted
URL:            http://gitlab.com/kernel-firmware/linux-firmware
Source:         /dev/null
BuildArch:      noarch

%description
Monolithic snapshot of upstream linux-firmware package, intended to
to validate upstream firmware without conflicts to the distribution
package.

%prep
%setup -q

%build

%install
%define __strip /bin/true
rm -rf %{buildroot}
mkdir -p %{buildroot}/lib/firmware
cp -aR {{ cwd }}/updates %{buildroot}/lib/firmware

%files
%defattr(-,root,root,-)
/lib/firmware/updates/*

%post
dracut -fp --regenerate-all
