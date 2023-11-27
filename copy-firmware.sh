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
skip_dedup=0

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

        --ignore-duplicates)
            skip_dedup=1
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

if ! command -v rdfind >/dev/null; then
	if [ "$skip_dedup" != 1 ]; then
    		echo "ERROR: rdfind is not installed.  Pass --ignore-duplicates to skip deduplication"
		exit 1
	fi
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

if [ "$skip_dedup" != 1 ] ; then
	$verbose "Finding duplicate files"
	rdfind -makesymlinks true -makeresultsfile false "$destdir" >/dev/null
	find "$destdir" -type l | while read -r l; do
		target="$(realpath "$l")"
		$verbose "Correcting path for $l"
		ln -fs "$(realpath --relative-to="$(dirname "$(realpath -s "$l")")" "$target")" "$l"
	done
fi

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
        if test -d "$target"; then
            $verbose "creating link $f -> $d"
            ln -s "$d" "$destdir/$f"
        else
            $verbose "creating link $f$compext -> $d$compext"
            ln -s "$d$compext" "$destdir/$f$compext"
        fi
    fi
done

exit 0

# vim: et sw=4 sts=4 ts=4
