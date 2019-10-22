#!/usr/bin/env bash

set -e

if [ -n "$(git status --porcelain)" ]
then
    echo "ERROR: uncommitted changes"
    exit 1
fi

package="$(dpkg-parsechangelog --file "debian/changelog" --show-field Source)"
version="$(dpkg-parsechangelog --file "debian/changelog" --show-field Version)"

if [[ "${version}" == *"+system76"* ]]
then
    echo "${package} ${version} already updated for system76"
else
    new_version="${version}+system76"
    sed -i "s/${package} (${version})/${package} (${new_version})/" "debian/changelog"
    dch --changelog "debian/changelog" --release 'Release for System76'
fi

fakeroot debian/rules clean

git add .
git commit -s -m "DROP ON REBASE: ${new_version} based on ${version}"
