#!/usr/bin/env python3
"""Kansas statute collector.

Kansas Statutes Annotated (KSA) are published as a 3-level static tree on
the Revisor of Statutes site:

    index    : https://ksrevisor.gov/ksa.html
                 -> 91 chapter pages  statutes/ksa_ch{N}.html  (N may carry
                    an alpha suffix, e.g. ksa_ch16a.html)
    chapter  : https://ksrevisor.gov/statutes/ksa_ch{N}.html
                 -> section files  /statutes/chapters/ch{NN}/{sec}.html
    section  : one HTML file per statute section

A single GET of each level enumerates the next. Reachable from KR IP
(not geoblocked), but the per-section fan-out is large, so this is meant to
run in GHA where minutes are unmetered.
"""
import os
import re
import sys
import time
import urllib.request

RAW_DIR = os.environ.get(
    "RAW_DIR",
    os.environ.get("KS_RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-ks/statute"),
)
BASE = "https://ksrevisor.gov"
INDEX_URL = f"{BASE}/ksa.html"
UA = "Mozilla/5.0 (compatible; xsoft-comply/1.0)"
CHAPTERS_FILE = os.path.join(RAW_DIR, "_chapters.txt")
SECTIONS_FILE = os.path.join(RAW_DIR, "_sections.txt")


def _fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _chapter_urls():
    html = _fetch(INDEX_URL).decode("utf-8", "replace")
    rel = re.findall(r'statutes/ksa_ch[0-9]+[a-z]?\.html', html)
    seen, out = set(), []
    for r in rel:
        if r not in seen:
            seen.add(r)
            out.append(f"{BASE}/{r}")
    return out


def _section_urls_in_chapter(chapter_html):
    rel = re.findall(r'/statutes/chapters/ch[0-9a-z]+/[0-9a-z_]+\.html', chapter_html)
    seen, out = set(), []
    for r in rel:
        if r not in seen:
            seen.add(r)
            out.append(f"{BASE}{r}")
    return out


def enum():
    os.makedirs(RAW_DIR, exist_ok=True)
    chapters = _chapter_urls()
    with open(CHAPTERS_FILE, "w") as f:
        f.write("\n".join(chapters) + "\n")
    sections = []
    seen = set()
    for i, cu in enumerate(chapters, 1):
        try:
            chtml = _fetch(cu).decode("utf-8", "replace")
        except Exception as e:
            print(f"[ks][enum] chapter fail {cu}: {e}")
            continue
        for su in _section_urls_in_chapter(chtml):
            if su not in seen:
                seen.add(su)
                sections.append(su)
        if i % 10 == 0:
            print(f"[ks][enum] {i}/{len(chapters)} chapters, {len(sections)} sections")
        time.sleep(0.1)
    with open(SECTIONS_FILE, "w") as f:
        f.write("\n".join(sections) + "\n")
    print(f"[ks][enum] chapters={len(chapters)} sections={len(sections)}")


def _local_path(url):
    # /statutes/chapters/ch01/001_002_0001.html -> ch01/001_002_0001.html
    tail = url.split("/statutes/chapters/", 1)[1]
    return os.path.join(RAW_DIR, "chapters", tail)


def collect():
    os.makedirs(RAW_DIR, exist_ok=True)
    if not os.path.exists(SECTIONS_FILE):
        enum()
    urls = [u.strip() for u in open(SECTIONS_FILE) if u.strip()]
    ok = skip = miss = 0
    for i, u in enumerate(urls, 1):
        dest = _local_path(u)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            skip += 1
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            data = _fetch(u)
            with open(dest, "wb") as f:
                f.write(data)
            ok += 1
        except Exception as e:
            miss += 1
            if miss <= 20:
                print(f"[ks][collect] miss {u}: {e}")
        if i % 500 == 0:
            print(f"[ks][collect] {i}/{len(urls)} ok={ok} skip={skip} miss={miss}")
        time.sleep(0.05)
    print(f"[ks][collect] total={len(urls)} ok={ok} skip={skip} miss={miss}")


def verify():
    if not os.path.exists(SECTIONS_FILE):
        print("[ks][verify] FAIL sections enum missing")
        sys.exit(0)
    urls = [u.strip() for u in open(SECTIONS_FILE) if u.strip()]
    distinct = len(set(urls))
    present = 0
    for u in urls:
        dest = _local_path(u)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            present += 1
    miss = len(urls) - present
    miss_rate = (miss / len(urls) * 100) if urls else 100.0
    chapters = 0
    if os.path.exists(CHAPTERS_FILE):
        chapters = len({c.strip() for c in open(CHAPTERS_FILE) if c.strip()})
    print(
        f"[ks][verify] chapters={chapters} sections={len(urls)} "
        f"distinct={distinct} present={present} miss={miss} "
        f"miss_rate={miss_rate:.2f}% dup={len(urls)-distinct}"
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
