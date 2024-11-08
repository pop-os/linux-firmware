#!/bin/sh
# SPDX-License-Identifier: GPL-2.0
#
# Copy firmware files based on WHENCE list
#

verbose=:
# shellcheck disable=SC2209
compress=cat
compext=
destdir=

err() {
    printf "ERROR: %s\n" "$*"
    exit 1
}

warn() {
    printf "WARNING: %s\n" "$*"
}

while test $# -gt 0; do
    case $1 in
        -v | --verbose)
            # shellcheck disable=SC2209
            verbose=echo
            shift
            ;;

        --xz)
            if test "$compext" = ".zst"; then
                err "cannot mix XZ and ZSTD compression"
            fi
            compress="xz --compress --quiet --stdout --check=crc32"
            compext=".xz"
            shift
            ;;

        --zstd)
            if test "$compext" = ".xz"; then
                err "cannot mix XZ and ZSTD compression"
            fi
            # shellcheck disable=SC2209
            compress="zstd --compress --quiet --stdout"
            compext=".zst"
            shift
            ;;

        *)
            if test -n "$destdir"; then
                err "unknown command-line options: $*"
            fi

            destdir="$1"
            shift
            ;;
    esac
done

if test -z "$destdir"; then
    err "destination directory was not specified"
fi

if test -d "$destdir"; then
    find "$destdir" -type d -empty >/dev/null || warn "destination folder is not empty."
fi

$verbose "Checking that WHENCE file is formatted properly"
./check_whence.py || err "check_whence.py has detected errors."

# shellcheck disable=SC2162 # file/folder name can include escaped symbols
grep -E '^(RawFile|File):' WHENCE | sed -E -e 's/^(RawFile|File): */\1 /;s/"//g' | while read k f; do
    install -d "$destdir/$(dirname "$f")"
    $verbose "copying/compressing file $f$compext"
    if test "$compress" != "cat" && test "$k" = "RawFile"; then
        $verbose "compression will be skipped for file $f"
        cat "$f" > "$destdir/$f"
    else
        $compress "$f" > "$destdir/$f$compext"
    fi
done

# shellcheck disable=SC2162 # file/folder name can include escaped symbols
grep -E '^Link:' WHENCE | sed -e 's/^Link: *//g;s/-> //g' | while read l t; do
    directory="$destdir/$(dirname "$l")"
    install -d "$directory"
    target="$(cd "$directory" && realpath -m -s "$t")"
    if test -e "$target"; then
        $verbose "creating link $l -> $t"
        ln -s "$t" "$destdir/$l"
    else
        $verbose "creating link $l$compext -> $t$compext"
        ln -s "$t$compext" "$destdir/$l$compext"
    fi
done

# Verify no broken symlinks
if test "$(find "$destdir" -xtype l | wc -l)" -ne 0 ; then
    err "Broken symlinks found:\\n$(find "$destdir" -xtype l)"
fi

exit 0

# vim: et sw=4 sts=4 ts=4
