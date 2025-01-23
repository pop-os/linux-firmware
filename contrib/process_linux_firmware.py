#!/usr/bin/python3
import os
import time
import urllib.request
import sqlite3
import feedparser
import argparse
import logging
import email
import email.utils
import smtplib
import subprocess
import sys
import magic  # https://pypi.python.org/pypi/python-magic
from datetime import date
from enum import Enum

URL = "https://lore.kernel.org/linux-firmware/new.atom"


class ContentType(Enum):
    REPLY = 1
    PATCH = 2
    PULL_REQUEST = 3
    SPAM = 4


content_types = {
    "are available in the Git repository at": ContentType.PULL_REQUEST,
    "diff --git": ContentType.PATCH,
    "Signed-off-by:": ContentType.PATCH,
}


def classify_content(content):
    # load content into the email library
    msg = email.message_from_string(content)
    decoded = None
    body = None

    # check the subject
    subject = msg["Subject"]
    if "Re:" in subject:
        return ContentType.REPLY
    if "PATCH" in subject:
        return ContentType.PATCH

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True)
    else:
        body = msg.get_payload(decode=True)

    if body:
        m = magic.Magic(mime_encoding=True)
        try:
            decoded = body.decode(m.from_buffer(body))
        except UnicodeDecodeError:
            pass

    if decoded:
        for key in content_types.keys():
            if key in decoded:
                return content_types[key]
    else:
        logging.warning("Failed to decode email: %s, treating as SPAM", body)

    return ContentType.SPAM


def fetch_url(url):
    blob = None
    with urllib.request.urlopen(url) as response:
        blob = response.read()
    m = magic.Magic(mime_encoding=True)
    return blob.decode(m.from_buffer(blob))


def quiet_cmd(cmd):
    logging.debug("Running {}".format(cmd))
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    logging.debug(output)


def reply_email(content, branch):
    user = None
    password = None
    server = None
    port = None

    if "SMTP_USER" in os.environ:
        user = os.environ["SMTP_USER"]
    if "SMTP_PASS" in os.environ:
        password = os.environ["SMTP_PASS"]
    if "SMTP_SERVER" in os.environ:
        server = os.environ["SMTP_SERVER"]
    if "SMTP_PORT" in os.environ:
        port = os.environ["SMTP_PORT"]
    if not user or not password or not server or not port:
        logging.debug("Missing SMTP configuration, not sending email")
        return

    reply = email.message.EmailMessage()

    orig = email.message_from_string(content)
    try:
        reply["To"] = ", ".join(
            email.utils.formataddr(t)
            for t in email.utils.getaddresses(
                orig.get_all("from", [])
                + orig.get_all("to", [])
                + orig.get_all("cc", [])
            )
        )
    except ValueError:
        logging.warning("Failed to parse email addresses, not sending email")
        return

    reply["From"] = "linux-firmware@kernel.org"
    try:
        reply["Subject"] = "Re: {}".format(orig["Subject"])
    except ValueError:
        logging.warning("Failed to parse subject, not sending email")
        return

    reply["In-Reply-To"] = orig["Message-Id"]
    reply["References"] = orig["Message-Id"]
    reply["Thread-Topic"] = orig["Thread-Topic"]
    reply["Thread-Index"] = orig["Thread-Index"]

    content = (
        "Your request has been forwarded by the Linux Firmware Kernel robot.\n"
        "Please follow up at https://gitlab.com/kernel-firmware/linux-firmware/-/merge_requests to ensure it gets merged\n"
        "Your request is '{}'".format(branch)
    )
    reply.set_content(content)

    mailserver = smtplib.SMTP(server, port)
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login(user, password)
    mailserver.sendmail(reply["From"], reply["To"], reply.as_string())
    mailserver.quit()


def create_pr(remote, branch):
    cmd = [
        "git",
        "push",
        "-u",
        remote,
        branch,
        "-o",
        "merge_request.create",
        "-o",
        "merge_request.remove_source_branch",
        "-o",
        "merge_request.target=main",
        "-o",
        "merge_request.title={}".format(branch),
    ]
    quiet_cmd(cmd)


def refresh_branch():
    quiet_cmd(["git", "checkout", "main"])
    quiet_cmd(["git", "pull"])


def delete_branch(branch):
    quiet_cmd(["git", "checkout", "main"])
    quiet_cmd(["git", "branch", "-D", branch])


def process_pr(mbox, num, remote):
    branch = "robot/pr-{}-{}".format(num, int(time.time()))

    # manual fixup for PRs from drm firmware repo
    if "git@gitlab.freedesktop.org:drm/firmware.git" in mbox:
        mbox = mbox.replace(
            "git@gitlab.freedesktop.org:drm/firmware.git",
            "https://gitlab.freedesktop.org/drm/firmware.git",
        )

    cmd = ["b4", "--debug", "pr", "-b", branch, "-"]
    logging.debug("Running {}".format(cmd))
    p = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = p.communicate(mbox.encode("utf-8"))
    for line in stdout.splitlines():
        logging.debug(line.decode("utf-8"))
    for line in stderr.splitlines():
        logging.debug(line.decode("utf-8"))

    # determine if it worked (we can't tell unfortunately by return code)
    cmd = ["git", "branch", "--list", branch]
    logging.debug("Running {}".format(cmd))
    result = subprocess.check_output(cmd)

    if result:
        for line in result.splitlines():
            logging.debug(line.decode("utf-8"))
        logging.info("Forwarding PR for {}".format(branch))
        if remote:
            create_pr(remote, branch)
        delete_branch(branch)
        return branch
    return None


def process_patch(mbox, num, remote):
    # create a new branch for the patch
    branch = "robot/patch-{}-{}".format(num, int(time.time()))
    cmd = ["git", "checkout", "-b", branch]
    quiet_cmd(cmd)

    # apply the patch
    cmd = ["git", "am"]
    logging.debug("Running {}".format(cmd))
    p = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = p.communicate(mbox.encode("utf-8"))
    for line in stdout.splitlines():
        logging.debug(line.decode("utf-8"))
    for line in stderr.splitlines():
        logging.debug(line.decode("utf-8"))
    if p.returncode != 0:
        quiet_cmd(["git", "am", "--abort"])
    else:
        logging.info("Opening PR for {}".format(branch))
        if remote:
            create_pr(remote, branch)

    delete_branch(branch)
    if p.returncode == 0:
        return branch
    return None


def update_database(conn, url):
    c = conn.cursor()

    c.execute(
        """CREATE TABLE IF NOT EXISTS firmware (url text, processed integer default 0, spam integer default 0)"""
    )

    # local file
    if os.path.exists(url):
        with open(url, "r") as f:
            atom = f.read()
    # remote file
    else:
        logging.info("Fetching {}".format(url))
        atom = fetch_url(url)

    # Parse the atom and extract the URLs
    feed = feedparser.parse(atom)

    # Insert the URLs into the database (oldest first)
    feed["entries"].reverse()
    for entry in feed["entries"]:
        c.execute("SELECT url FROM firmware WHERE url = ?", (entry.link,))
        if c.fetchone():
            continue
        c.execute("INSERT INTO firmware VALUES (?, ?, ?)", (entry.link, 0, 0))

    # Commit the changes and close the connection
    conn.commit()


def process_database(conn, remote):
    c = conn.cursor()

    # get all unprocessed urls that aren't spam
    c.execute("SELECT url FROM firmware WHERE processed = 0 AND spam = 0")
    num = 0
    msg = ""

    rows = c.fetchall()

    if not rows:
        logging.info("No new entries")
        return

    refresh_branch()

    # loop over all unprocessed urls
    for row in rows:
        branch = None
        msg = "Processing ({}%)".format(round(num / len(rows) * 100))
        print(msg, end="\r", flush=True)

        url = "{}raw".format(row[0])
        logging.debug("Processing {}".format(url))
        mbox = fetch_url(url)
        classification = classify_content(mbox)

        if classification == ContentType.PATCH:
            logging.debug("Processing patch ({})".format(row[0]))
            branch = process_patch(mbox, num, remote)

        if classification == ContentType.PULL_REQUEST:
            logging.debug("Processing PR ({})".format(row[0]))
            branch = process_pr(mbox, num, remote)

        if classification == ContentType.SPAM:
            logging.debug("Marking spam ({})".format(row[0]))
            c.execute("UPDATE firmware SET spam = 1 WHERE url = ?", (row[0],))

        if classification == ContentType.REPLY:
            logging.debug("Ignoring reply ({})".format(row[0]))

        c.execute("UPDATE firmware SET processed = 1 WHERE url = ?", (row[0],))
        num += 1
        print(" " * len(msg), end="\r", flush=True)

        # commit changes
        conn.commit()

        # send any emails
        if branch:
            reply_email(mbox, branch)

    logging.info("Finished processing {} new entries".format(len(rows)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process linux-firmware mailing list")
    parser.add_argument("--url", default=URL, help="URL to get ATOM feed from")
    parser.add_argument(
        "--database",
        default=os.path.join("contrib", "linux_firmware.db"),
        help="sqlite database to store entries in",
    )
    parser.add_argument("--dry", action="store_true", help="Don't open pull requests")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging to console"
    )
    parser.add_argument("--remote", default="origin", help="Remote to push to")
    parser.add_argument(
        "--refresh-cycle", default=0, help="How frequently to run (in minutes)"
    )
    args = parser.parse_args()

    if not os.path.exists("WHENCE"):
        logging.critical(
            "Please run this script from the root of the linux-firmware repository"
        )
        sys.exit(1)

    log = os.path.join(
        "contrib",
        "{prefix}-{date}.{suffix}".format(
            prefix="linux_firmware", suffix="txt", date=date.today()
        ),
    )
    logging.basicConfig(
        format="%(asctime)s %(levelname)s:\t%(message)s",
        filename=log,
        filemode="w",
        level=logging.DEBUG,
    )

    # set a format which is simpler for console use
    console = logging.StreamHandler()
    if args.debug:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s : %(levelname)s : %(message)s")
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)

    while True:
        if args.dry:
            remote = ""
        else:
            remote = args.remote

        try:
            conn = sqlite3.connect(args.database)

            # update the database
            update_database(conn, args.url)
            # process the database
            process_database(conn, remote)

        except urllib.error.HTTPError as e:
            logging.error("Failed to fetch URL: {}".format(e))
        finally:
            conn.close()

        if args.refresh_cycle:
            logging.info("Sleeping for {} minutes".format(args.refresh_cycle))
            time.sleep(int(args.refresh_cycle) * 60)
        else:
            break
