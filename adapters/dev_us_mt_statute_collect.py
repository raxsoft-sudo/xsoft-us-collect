#!/usr/bin/env python3
"""Montana Code Annotated (MCA) collector.

MCA is published as a 5-level static tree on leg.mt.gov:

    index    : https://leg.mt.gov/bills/mca/index.html
                 -> title pages   title_{NNNN}/chapters_index.html
    title    : -> chapter pages   chapter_{NNNN}/parts_index.html
    chapter  : -> part pages      part_{NNNN}/sections_index.html
    part     : -> section files   section_{NNNN}/{a}-{b}-{c}-{d}.html
    section  : one HTML file per statute section

All relative; a single GET of each level enumerates the next. Reachable
from KR IP, but the per-section fan-out is large, so this runs in GHA
where minutes are unmetered.
"""
import os
import re
import sys
import time
import urllib.request

RAW_DIR = os.environ.get(
    "RAW_DIR",
    os.environ.get("MT_RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-mt/statute"),
)
BASE = "https://leg.mt.gov/bills/mca"
INDEX_URL = f"{BASE}/index.html"
UA = "Mozilla/5.0 (compatible; xsoft-comply/1.0)"
TITLES_FILE = os.path.join(RAW_DIR, "_titles.txt")
SECTIONS_FILE = os.path.join(RAW_DIR, "_sections.txt")


def _fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _chunk_slice(items, tag):
    # GHA 매트릭스 청크 분할: CHUNK_N>1 이면 i % CHUNK_N == CHUNK_I 슬라이스만 처리.
    # 기본값(CHUNK_N=1)은 무분할 = 전체. enum 결과는 결정적이라 청크 합집합 = 전수.
    cn = int(os.environ.get("CHUNK_N", "1"))
    ci = int(os.environ.get("CHUNK_I", "0"))
    if cn > 1:
        items = [x for idx, x in enumerate(items) if idx % cn == ci]
        print(f"[{tag}][chunk] CHUNK_N={cn} CHUNK_I={ci} -> {len(items)} items")
    return items


def _join(parent_url, rel):
    # parent_url ends with a file; resolve "./x" or "../x" against its dir
    base = parent_url.rsplit("/", 1)[0]
    while rel.startswith("../"):
        rel = rel[3:]
        base = base.rsplit("/", 1)[0]
    if rel.startswith("./"):
        rel = rel[2:]
    return f"{base}/{rel}"


def _links(html, pattern):
    seen, out = set(), []
    for m in re.findall(pattern, html):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def enum():
    os.makedirs(RAW_DIR, exist_ok=True)
    idx = _fetch(INDEX_URL).decode("utf-8", "replace")
    title_rels = _links(idx, r'title_[0-9]+/chapters_index\.html')
    titles = [_join(INDEX_URL, r) for r in title_rels]
    with open(TITLES_FILE, "w") as f:
        f.write("\n".join(titles) + "\n")
    sections, seen = [], set()
    for ti, turl in enumerate(titles, 1):
        try:
            thtml = _fetch(turl).decode("utf-8", "replace")
        except Exception as e:
            print(f"[mt][enum] title fail {turl}: {e}")
            continue
        ch_rels = _links(thtml, r'chapter_[0-9]+/parts_index\.html')
        for cr in ch_rels:
            curl = _join(turl, cr)
            try:
                chtml = _fetch(curl).decode("utf-8", "replace")
            except Exception as e:
                print(f"[mt][enum] chapter fail {curl}: {e}")
                continue
            pt_rels = _links(chtml, r'part_[0-9]+/sections_index\.html')
            for pr in pt_rels:
                purl = _join(curl, pr)
                try:
                    phtml = _fetch(purl).decode("utf-8", "replace")
                except Exception as e:
                    print(f"[mt][enum] part fail {purl}: {e}")
                    continue
                sec_rels = _links(phtml, r'section_[0-9]+/[0-9]+-[0-9]+-[0-9]+-[0-9]+\.html')
                for sr in sec_rels:
                    surl = _join(purl, sr)
                    if surl not in seen:
                        seen.add(surl)
                        sections.append(surl)
                time.sleep(0.03)
            time.sleep(0.03)
        if ti % 5 == 0:
            print(f"[mt][enum] {ti}/{len(titles)} titles, {len(sections)} sections")
        time.sleep(0.05)
    with open(SECTIONS_FILE, "w") as f:
        f.write("\n".join(sections) + "\n")
    print(f"[mt][enum] titles={len(titles)} sections={len(sections)}")


def _local_path(url):
    # .../bills/mca/title_0010/chapter_0010/part_0010/section_0010/0010-0010-0010-0010.html
    tail = url.split("/bills/mca/", 1)[1]
    return os.path.join(RAW_DIR, tail)


def collect():
    os.makedirs(RAW_DIR, exist_ok=True)
    if not os.path.exists(SECTIONS_FILE):
        enum()
    urls = [u.strip() for u in open(SECTIONS_FILE) if u.strip()]
    urls = _chunk_slice(urls, "mt")
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
                print(f"[mt][collect] miss {u}: {e}")
        if i % 500 == 0:
            print(f"[mt][collect] {i}/{len(urls)} ok={ok} skip={skip} miss={miss}")
        time.sleep(0.03)
    print(f"[mt][collect] total={len(urls)} ok={ok} skip={skip} miss={miss}")


def verify():
    if not os.path.exists(SECTIONS_FILE):
        print("[mt][verify] FAIL sections enum missing")
        sys.exit(0)
    urls = [u.strip() for u in open(SECTIONS_FILE) if u.strip()]
    urls = _chunk_slice(urls, "mt")
    distinct = len(set(urls))
    present = 0
    for u in urls:
        dest = _local_path(u)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            present += 1
    miss = len(urls) - present
    miss_rate = (miss / len(urls) * 100) if urls else 100.0
    titles = 0
    if os.path.exists(TITLES_FILE):
        titles = len({t.strip() for t in open(TITLES_FILE) if t.strip()})
    print(
        f"[mt][verify] titles={titles} sections={len(urls)} "
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
