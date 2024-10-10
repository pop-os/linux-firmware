#!/bin/sh
# SPDX-License-Identifier: GPL-2.0
#
# Deduplicate files in a given destdir
#

err() {
    echo "ERROR: $*"
    exit 1
}

verbose=:
destdir=
while test $# -gt 0; do
    case $1 in
        -v | --verbose)
            # shellcheck disable=SC2209
            verbose=echo
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
    err "destination directory was not specified."
fi

if ! test -d "$destdir"; then
    err "provided directory does not exit."
fi

if ! command -v rdfind >/dev/null; then
    err "rdfind is not installed."
fi

$verbose "Finding duplicate files"
rdfind -makesymlinks true -makeresultsfile true "$destdir" >/dev/null

grep DUPTYPE_WITHIN_SAME_TREE results.txt | grep -o "$destdir.*" | while read -r l; do
    target="$(realpath "$l")"
    $verbose "Correcting path for $l"
    ln --force --symbolic --relative "$target" "$l"
done

rm results.txt
