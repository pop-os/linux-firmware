#!/usr/bin/env python3

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
from jinja2 import Environment, FileSystemLoader


def version_str() -> str:
    try:
        return subprocess.check_output(["git", "describe"]).strip().decode("utf-8")
    except subprocess.CalledProcessError:
        return "0"


def prep_tree(package) -> tuple:
    tmpdir = tempfile.mkdtemp()
    builddir = os.path.join(tmpdir, package)
    fwdir = os.path.join(builddir, "updates")
    targetdir = "dist"

    os.makedirs(targetdir, exist_ok=True)
    os.makedirs(builddir, exist_ok=False)
    os.makedirs(fwdir, exist_ok=False)

    subprocess.check_output(["./copy-firmware.sh", fwdir])
    shutil.copy("WHENCE", os.path.join(builddir, "WHENCE"))

    return (tmpdir, builddir, fwdir, targetdir)


def build_deb_package(package, builddir) -> None:
    env = Environment(loader=FileSystemLoader(os.path.join("contrib", "templates")))

    d = {
        "package": package,
        "date": datetime.datetime.now()
        .astimezone()
        .strftime("%a, %d %b %Y %H:%M:%S %z"),
        "version": version_str(),
    }

    templates = {
        "debian.control": "control",
        "debian.changelog": "changelog",
        "debian.copyright": "copyright",
    }

    os.makedirs(os.path.join(builddir, "debian"))
    for f in templates:
        template = env.get_template(f)
        with open(os.path.join(builddir, "debian", templates[f]), "w") as w:
            w.write(template.render(d))

    with open(os.path.join(builddir, "debian", "install"), "w") as w:
        w.write("updates lib/firmware\n")

    with open(os.path.join(builddir, "debian", "docs"), "w") as w:
        w.write("WHENCE\n")

    with open(os.path.join(builddir, "debian", "rules"), "w") as w:
        w.write("#!/usr/bin/make -f\n")
        w.write("%:\n")
        w.write("\tdh $@\n")
    os.chmod(os.path.join(builddir, "debian", "rules"), 0o755)

    os.mkdir(os.path.join(builddir, "debian", "source"))
    with open(os.path.join(builddir, "debian", "source", "format"), "w") as w:
        w.write("3.0 (native)\n")

    # build the package
    os.environ["DEB_BUILD_OPTIONS"] = "nostrip"
    subprocess.check_output(["dpkg-buildpackage", "-us", "-uc", "-b"], cwd=builddir)

    # result is in tmpdir (not builddir!)
    return os.path.join(
        "..",
        "{package}_{version}_all.deb".format(package=package, version=version_str()),
    )


def build_rpm_package(package, builddir) -> None:

    v = version_str().replace("-", "_")
    env = Environment(loader=FileSystemLoader(os.path.join("contrib", "templates")))

    d = {
        "package": package,
        "version": v,
        "cwd": builddir,
    }

    template = env.get_template("rpm.spec")
    with open(os.path.join(builddir, "package.spec"), "wt") as w:
        w.write(template.render(d))
    cmd = ["rpmbuild", "-bb", "--build-in-place", "package.spec"]
    subprocess.check_call(cmd, cwd=builddir, stderr=subprocess.STDOUT)

    # result is in ~/rpmbuild/RPMS/noarch/
    for root, dirs, files in os.walk(
        os.path.join(os.getenv("HOME"), "rpmbuild", "RPMS", "noarch")
    ):
        for f in files:
            if f.startswith(package) and f.endswith(".rpm") and v in f:
                return os.path.join(root, f)
    raise FileNotFoundError("RPM package not found")


def parse_args():
    parser = argparse.ArgumentParser("Build upstream packages using Jinja2 templates")
    parser.add_argument("--deb", help="Build DEB package", action="store_true")
    parser.add_argument("--rpm", help="Build RPM package", action="store_true")
    parser.add_argument("--debug", help="Enable debug output", action="store_true")
    args = parser.parse_args()

    if not (args.rpm or args.deb) or (args.rpm and args.deb):
        parser.print_help()
        sys.exit(1)

    return args


if __name__ == "__main__":
    args = parse_args()

    package = "linux-firmware-upstream"
    tmpdir, builddir, fwdir, targetdir = prep_tree(package)

    try:
        if args.deb:
            result = build_deb_package(package, builddir)
        elif args.rpm:
            result = build_rpm_package(package, builddir)
        shutil.copy(os.path.join(builddir, result), targetdir)
        print(
            "Built package: {}".format(
                os.path.join(targetdir, os.path.basename(result))
            )
        )
    finally:
        if not args.debug:
            shutil.rmtree(tmpdir)
