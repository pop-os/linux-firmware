#!/bin/sh
# SPDX-License-Identifier: GPL-2.0
#
# Copy firmware files based on WHENCE list
#

verbose=:
prune=no
# shellcheck disable=SC2209
compress=cat
compext=

while test $# -gt 0; do
    case $1 in
        -v | --verbose)
            # shellcheck disable=SC2209
            verbose=echo
            shift
            ;;

        -P | --prune)
            prune=yes
            shift
            ;;

        --xz)
            if test "$compext" = ".zst"; then
                echo "ERROR: cannot mix XZ and ZSTD compression"
                exit 1
            fi
            compress="xz --compress --quiet --stdout --check=crc32"
            compext=".xz"
            shift
            ;;

        --zstd)
            if test "$compext" = ".xz"; then
                echo "ERROR: cannot mix XZ and ZSTD compression"
                exit 1
            fi
            # shellcheck disable=SC2209
            compress="zstd --compress --quiet --stdout"
            compext=".zst"
            shift
            ;;

        -*)
            if test "$compress" = "cat"; then
                echo "ERROR: unknown command-line option: $1"
                exit 1
            fi
            compress="$compress $1"
            shift
            ;;
        *)
            if test "x$destdir" != "x"; then
                echo "ERROR: unknown command-line options: $*"
                exit 1
            fi

            destdir="$1"
            shift
            ;;
    esac
done

if [ -z "$destdir" ]; then
	echo "ERROR: destination directory was not specified"
	exit 1
fi

# shellcheck disable=SC2162 # file/folder name can include escaped symbols
grep -E '^(RawFile|File):' WHENCE | sed -E -e 's/^(RawFile|File): */\1 /;s/"//g' | while read k f; do
    test -f "$f" || continue
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
grep -E '^Link:' WHENCE | sed -e 's/^Link: *//g;s/-> //g' | while read f d; do
    if test -L "$f$compext"; then
        test -f "$destdir/$f$compext" && continue
        $verbose "copying link $f$compext"
        install -d "$destdir/$(dirname "$f")"
        cp -d "$f$compext" "$destdir/$f$compext"

        if test "x$d" != "x"; then
            target="$(readlink "$f")"

            if test "x$target" != "x$d"; then
                $verbose "WARNING: inconsistent symlink target: $target != $d"
            else
                if test "x$prune" != "xyes"; then
                    $verbose "WARNING: unneeded symlink detected: $f"
                else
                    $verbose "WARNING: pruning unneeded symlink $f"
                    rm -f "$f$compext"
                fi
            fi
        else
            $verbose "WARNING: missing target for symlink $f"
        fi
    else
        directory="$destdir/$(dirname "$f")"
        install -d "$directory"
        target="$(cd "$directory" && realpath -m -s "$d")"
        if test -e "$target"; then
            $verbose "creating link $f -> $d"
            ln -s "$d" "$destdir/$f"
        else
            $verbose "creating link $f$compext -> $d$compext"
            ln -s "$d$compext" "$destdir/$f$compext"
        fi
    fi
done

# Verify no broken symlinks
if test "$(find "$destdir" -xtype l | wc -l)" -ne 0 ; then
        echo "ERROR: Broken symlinks found:"
        find "$destdir" -xtype l
        exit 1
fi

exit 0

# vim: et sw=4 sts=4 ts=4
