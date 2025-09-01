
# Linux firmware

This repository contains all these firmware images which have been
extracted from older drivers, as well various new firmware images which
we were never permitted to include in a GPL'd work, but which we _have_
been permitted to redistribute under separate cover.

The upstream repository is located at <https://gitlab.com/kernel-firmware/linux-firmware.git>.

## Submitting firmware

To submit firmware to this repository, please do one of the following:

* open a MR [upstream](https://gitlab.com/kernel-firmware/linux-firmware)
* send a git binary diff to `linux-firmware@kernel.org`
* send a git pull request to: `linux-firmware@kernel.org`

### Signed-off-by requirement

All commits must include a `Signed-off-by` line to track the provenance of the
firmware. This signature must be from someone with authority over the licensing
of the firmware, typically someone from within the company that owns or
controls the firmware. The `Signed-off-by` line serves as an attestation that
the contributor has the right to submit the firmware under the specified
license terms and that it can be redistributed according to those terms.

At times, a contributor may work at a location that makes it difficult to
submit patches or MRs from their offical company accounts.  In this case,
the `Signed-off-by` line in the commit should still be via the company
address, but the submitter can use a personal address with the company address
on CC for the MR or patch contribution.

## Quality

If your commit adds new firmware, it must update the `WHENCE` file to
clearly state the license under which the firmware is available, and
that it is redistributable. Being redistributable includes ensuring
the firmware license provided includes an implicit or explicit
patent grant to end users to ensure full functionality of device
operation with the firmware. If the license is long and involved, it's
permitted to include it in a separate file and refer to it from the
`WHENCE` file (IE _'See `LICENSE.foo` for details.'_).
And if it were possible, a changelog of the firmware itself.

To maintain consistent quality on the repository, please run the following
before submitting a patch:

```shell
make check
```

If you don't have pre-commit installed, you can install it with:

```shell
pip install pre-commit
```

Your commit **must** contain a `Signed-Off-By:` from someone authoritative on
the licensing of the firmware in question (i.e. from within the company
that owns the code).

## Warnings

1. Don't send any `CONFIDENTIALITY STATEMENT` in your e-mail, patch or
request. Otherwise your firmware _will never be accepted_.
2. Maintainers are really busy, so don't expect a prompt reply.
