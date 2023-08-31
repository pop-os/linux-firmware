# Leverage FDO CI fairy, but add pre-commit to it
FROM quay.io/freedesktop.org/ci-templates:ci-fairy-sha256-eb20531b68e57da06f4e631402fd494869b1529e2c4ad05cfe24ef3fb8038815
RUN apk add python3-dev
RUN apk add gcc
RUN apk add musl-dev
RUN apk add git
RUN apk add npm
RUN apk add rdfind
RUN apk add shellcheck
RUN pip install pre-commit --ignore-installed distlib
