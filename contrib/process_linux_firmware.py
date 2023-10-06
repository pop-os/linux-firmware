#!/usr/bin/python3
import os
import time
import urllib.request
import sqlite3
import feedparser
import argparse
import logging
import email
import subprocess
import sys
from datetime import datetime, timedelta, date
from enum import Enum
import b4

URL = "https://lore.kernel.org/linux-firmware/new.atom"


class ContentType(Enum):
    REPLY = 1
    PATCH = 2
    PULL_REQUEST = 3
    SPAM = 4


content_types = {
    "diff --git": ContentType.PATCH,
    "Signed-off-by:": ContentType.PATCH,
    "are available in the Git repository at": ContentType.PULL_REQUEST,
}


def classify_content(content):
    # load content into the email library
    msg = email.message_from_string(content)

    # check the subject
    subject = msg["Subject"]
    if "Re:" in subject:
        return ContentType.REPLY
    if "PATCH" in subject:
        return ContentType.PATCH

    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            body = part.get_payload(decode=True).decode("utf-8")
            for key in content_types.keys():
                if key in body:
                    return content_types[key]
            break
    return ContentType.SPAM


def fetch_url(url):
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def quiet_cmd(cmd):
    logging.debug("Running {}".format(cmd))
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    logging.debug(output)


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


def process_pr(url, num, remote):
    branch = "robot/pr-{}-{}".format(num, int(time.time()))
    cmd = ["b4", "pr", "-b", branch, url]
    try:
        quiet_cmd(cmd)
    except subprocess.CalledProcessError:
        logging.warning("Failed to apply PR")
        return

    # determine if it worked (we can't tell unfortunately by return code)
    cmd = ["git", "branch", "--list", branch]
    logging.debug("Running {}".format(cmd))
    result = subprocess.check_output(cmd)

    if result:
        logging.info("Forwarding PR for {}".format(branch))
        if remote:
            create_pr(remote, branch)
        delete_branch(branch)


def process_patch(mbox, num, remote):
    # create a new branch for the patch
    branch = "robot/patch-{}-{}".format(num, int(time.time()))
    cmd = ["git", "checkout", "-b", branch]
    quiet_cmd(cmd)

    # apply the patch
    cmd = ["b4", "shazam", "-m", "-"]
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

        msg = "Processing ({}%)".format(round(num / len(rows) * 100))
        print(msg, end="\r", flush=True)

        url = "{}raw".format(row[0])
        logging.debug("Processing {}".format(url))
        mbox = fetch_url(url)
        classification = classify_content(mbox)

        if classification == ContentType.PATCH:
            logging.debug("Processing patch ({})".format(row[0]))
            process_patch(mbox, num, remote)

        if classification == ContentType.PULL_REQUEST:
            logging.debug("Processing PR ({})".format(row[0]))
            process_pr(row[0], num, remote)

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
        conn = sqlite3.connect(args.database)
        # update the database
        update_database(conn, args.url)

        if args.dry:
            remote = ""
        else:
            remote = args.remote

        # process the database
        process_database(conn, remote)

        conn.close()

        if args.refresh_cycle:
            logging.info("Sleeping for {} minutes".format(args.refresh_cycle))
            time.sleep(int(args.refresh_cycle) * 60)
        else:
            break
