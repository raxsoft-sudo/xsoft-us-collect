#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MO 법전 (revisor.mo.gov) 수집기 — 챕터 HTML 스크레이프.

어댑터 유형 = HTML 스크레이프 (지오블록 가능 · GHA 실행 필요).
  1순위: archive.org RSMo 컬렉션 — GHA 조회 시 식별자 발견되면 우선 사용
  폴백:  revisor.mo.gov/main/ONEBrowse.aspx
    인덱스 = https://revisor.mo.gov/main/ONEBrowse.aspx
    챕터   = https://revisor.mo.gov/main/OneSection.aspx?section=<N.NNN>
    또는    = https://revisor.mo.gov/main/ONEBrowse.aspx?bid=<N>

  archive.org 식별자 후보: 2024RSMOAppendicesTables 등 발견됨
  (전권 RSMo 단일 컬렉션 ID는 GHA에서 재확인 권장)

모드:
  --probe   : revisor.mo.gov 인덱스 + archive.org 검색 결과 로그
  --enum    : 챕터 섹션 열거 → _enum_laws.txt
  --collect : _enum_laws.txt 순회 → HTML 저장
  --verify  : 4지표 검증
"""
import os
import re
import sys
import time
import ssl
import json
import urllib.request
import urllib.error

BASE = "https://revisor.mo.gov"
INDEX_URL = BASE + "/main/ONEBrowse.aspx"
ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php?q=Missouri+Revised+Statutes+RSMo+full&fl[]=identifier&fl[]=title&rows=20&output=json"
RAW_DIR = os.environ.get("RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-mo/statute")
ENUM_FILE = os.path.join(RAW_DIR, "_enum_laws.txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
DELAY = float(os.environ.get("MO_DELAY", "0.5"))
SMOKE = int(os.environ.get("SMOKE", "0"))

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 섹션 링크 패턴
SECTION_RE = re.compile(
    r'href=["\']([^"\']*(?:OneSection\.aspx\?section=|ONEBrowse\.aspx\?bid=)[^"\']+)["\']',
    re.IGNORECASE,
)
CHAPTER_BID_RE = re.compile(r'bid=([0-9]+)', re.IGNORECASE)
SECTION_NUM_RE = re.compile(r'section=([\d.]+)', re.IGNORECASE)


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.getcode(), r.read()


def fetch_to_file_retry(url, path, backoff=2.0, max_retry=5):
    wait = backoff
    for attempt in range(max_retry):
        try:
            code, body = http_get(url)
            if code == 200 and body:
                with open(path, "wb") as f:
                    f.write(body)
                return True
            if code == 429:
                time.sleep(wait)
                wait *= 2
                continue
            return False
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(wait)
                wait *= 2
                continue
            return False
        except Exception as ex:
            print(f"[ERR attempt={attempt}] {type(ex).__name__}: {ex}")
            time.sleep(wait)
            wait *= 2
    return False


def probe():
    print("=== MO 법전 probe (revisor.mo.gov + archive.org) ===")
    os.makedirs(RAW_DIR, exist_ok=True)

    # archive.org 검색 (글로벌 접근 가능)
    print("[archive.org] RSMo 식별자 검색...")
    try:
        code, body = http_get(ARCHIVE_SEARCH, timeout=20)
        if code == 200:
            data = json.loads(body.decode("utf-8", "ignore"))
            items = data.get("response", {}).get("docs", [])
            print(f"[archive.org] 결과 {len(items)}건:")
            for item in items[:10]:
                print(f"  identifier={item.get('identifier','')} title={item.get('title','')[:60]}")
        else:
            print(f"[archive.org] 비200: {code}")
    except Exception as e:
        print(f"[archive.org] ERR {type(e).__name__}: {e}")

    # revisor.mo.gov 인덱스 (지오블록 가능)
    print(f"\n[revisor.mo.gov] 인덱스 접속: {INDEX_URL}")
    try:
        code, body = http_get(INDEX_URL)
        text = body.decode("utf-8", "ignore")
        print(f"[index] status={code} body_len={len(body)}")
        links = SECTION_RE.findall(text)
        print(f"[index] 링크 수={len(links)} 샘플={links[:5]}")
        bids = [CHAPTER_BID_RE.search(l) for l in links if CHAPTER_BID_RE.search(l)]
        print(f"[index] bid 샘플: {[m.group(1) for m in bids[:10]]}")
    except Exception as e:
        print(f"[revisor.mo.gov] ERR {type(e).__name__}: {e}")
    print("주의: revisor.mo.gov 지오블록 가능. GHA probe 로그로 링크 구조 보정 필요 [추정]")


def enum():
    """인덱스 챕터(bid) → 섹션 열거 → _enum_laws.txt."""
    os.makedirs(RAW_DIR, exist_ok=True)
    all_sections = []
    seen = set()

    try:
        code, body = http_get(INDEX_URL)
        if code != 200:
            print(f"[ERR] 인덱스 비200: {code}")
            sys.exit(1)
        text = body.decode("utf-8", "ignore")
        links = SECTION_RE.findall(text)
        bids = list({CHAPTER_BID_RE.search(l).group(1)
                     for l in links if CHAPTER_BID_RE.search(l)})
        print(f"[enum] 챕터(bid) 후보={len(bids)}")
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}")
        sys.exit(1)

    if not bids:
        # 폴백: bid 1~200 [추정]
        print("[WARN] 챕터 파싱 실패 — 폴백 bid 1~200 [추정]")
        bids = [str(i) for i in range(1, 201)]

    for bi, bid in enumerate(bids, 1):
        url = f"{INDEX_URL}?bid={bid}"
        try:
            code, body = http_get(url)
            if code != 200:
                print(f"[bid={bid}] 비200: {code}")
                time.sleep(DELAY)
                continue
            text = body.decode("utf-8", "ignore")
            sec_links = SECTION_RE.findall(text)
            for sl in sec_links:
                m = SECTION_NUM_RE.search(sl)
                if m:
                    sec_id = m.group(1)
                    if sec_id not in seen:
                        seen.add(sec_id)
                        all_sections.append(sec_id)
            if bi % 20 == 0:
                print(f"  bid {bi}/{len(bids)} 누적섹션={len(all_sections)}", flush=True)
        except Exception as e:
            print(f"[bid={bid}] ERR {type(e).__name__}: {e}")
        time.sleep(DELAY)
        if SMOKE > 0 and len(all_sections) >= SMOKE:
            all_sections = all_sections[:SMOKE]
            print(f"[SMOKE={SMOKE}] 열거 중단")
            break

    with open(ENUM_FILE, "w") as f:
        for s in all_sections:
            f.write(s + "\n")
    print(f"[OK] 열거 정본 저장: {ENUM_FILE} ({len(all_sections)}건)")


def collect():
    """_enum_laws.txt 섹션 번호 순회 → HTML 저장."""
    if not os.path.exists(ENUM_FILE):
        print(f"열거 정본 없음: {ENUM_FILE} (먼저 --enum)")
        sys.exit(1)
    with open(ENUM_FILE) as f:
        ids = [ln.strip() for ln in f if ln.strip()]
    os.makedirs(RAW_DIR, exist_ok=True)
    ok = miss = skip = 0
    for i, sec_id in enumerate(ids, 1):
        url = f"{BASE}/main/OneSection.aspx?section={sec_id}"
        path = os.path.join(RAW_DIR, f"{sec_id}.html")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue
        if fetch_to_file_retry(url, path):
            ok += 1
        else:
            miss += 1
        if i % 200 == 0:
            print(f"  진행 {i}/{len(ids)} ok={ok} skip={skip} miss={miss}", flush=True)
        time.sleep(DELAY)
    print(f"[collect] 총={len(ids)} ok={ok} skip={skip} miss={miss}")


def verify():
    """4지표 검증."""
    if not os.path.exists(ENUM_FILE):
        print(f"열거 정본 없음: {ENUM_FILE}")
        sys.exit(1)
    with open(ENUM_FILE) as f:
        enum_ids = [ln.strip() for ln in f if ln.strip()]
    enum_set = set(enum_ids)
    dup = len(enum_ids) - len(enum_set)
    body_ids = set()
    for n in os.listdir(RAW_DIR):
        if n.endswith(".html") and not n.startswith("_"):
            body_ids.add(n[:-5])
    absent = enum_set - body_ids
    orphan = body_ids - enum_set
    rate = (len(absent) / len(enum_set) * 100) if enum_set else 0.0
    print("=== MO STATUTE 검증 4지표 ===")
    print(f"모수(섹션 ID) = {len(enum_set)}")
    print(f"저장 파일 수 = {len(body_ids)}")
    print(f"부재 = {len(absent)} ({rate:.4f}%)")
    print(f"계층 고아 = {len(orphan)}")
    print(f"식별자 중복 = {dup}")
    ok = rate < 1.0 and len(orphan) == 0 and dup == 0
    print(f"판정 = {'PASS' if ok else 'FAIL'}")
    print("주의: archive.org RSMo 전권 컬렉션 미발견 → revisor.mo.gov 폴백 [추정]. GHA probe 로그 확인 필요")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--probe"
    if mode == "--probe":
        probe()
    elif mode == "--enum":
        enum()
    elif mode == "--collect":
        collect()
    elif mode == "--verify":
        verify()
    else:
        print(f"미구현 모드: {mode}")
