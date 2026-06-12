#!/usr/bin/env python3
"""Utah statute collector.

Utah publishes the ENTIRE code as one authoritative master XML
(current-version base stamp 1800010118000101):
    https://le.utah.gov/xcode/C_1800010118000101.xml
A single GET yields all titles/chapters/parts/sections. No per-chapter
enumeration needed. Not geoblocked (reachable from KR IP), so this runs
locally as well as in GHA.
"""
import os
import re
import sys
import urllib.request

RAW_DIR = os.environ.get(
    "RAW_DIR",
    os.environ.get("UT_RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-ut/statute"),
)
VERSION = "1800010118000101"
MASTER_URL = f"https://le.utah.gov/xcode/C_{VERSION}.xml"
MASTER_FILE = os.path.join(RAW_DIR, f"ut_code_full_{VERSION}.xml")
UA = "Mozilla/5.0 (compatible; xsoft-comply/1.0)"


def _fetch(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def enum():
    # Single master file; "enumeration" is just the one target.
    os.makedirs(RAW_DIR, exist_ok=True)
    print(f"[ut][enum] 1 target: {MASTER_URL}")


def collect():
    os.makedirs(RAW_DIR, exist_ok=True)
    data = _fetch(MASTER_URL)
    with open(MASTER_FILE, "wb") as f:
        f.write(data)
    print(f"[ut][collect] {len(data)} bytes -> {MASTER_FILE}")


def verify():
    if not os.path.exists(MASTER_FILE):
        print("[ut][verify] FAIL master file missing")
        sys.exit(0)
    blob = open(MASTER_FILE, "rb").read()
    txt = blob.decode("utf-8", "replace")
    titles = len(re.findall(r"<title number=", txt))
    chapters = len(re.findall(r"<chapter number=", txt))
    sections = re.findall(r'<section number="([^"]+)"', txt)
    distinct = len(set(sections))
    complete = txt.rstrip().endswith("</code>")
    miss = 0 if complete else 1
    print(
        f"[ut][verify] titles={titles} chapters={chapters} "
        f"sections={len(sections)} distinct={distinct} "
        f"complete={complete} miss={miss}"
    )


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "--collect"
    if arg == "--enum":
        enum()
    elif arg == "--collect":
        collect()
    elif arg == "--verify":
        verify()
    else:
        print(f"unknown arg {arg}")
        sys.exit(2)


if __name__ == "__main__":
    main()
