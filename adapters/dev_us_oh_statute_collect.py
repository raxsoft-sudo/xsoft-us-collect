#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OH 법전 (codes.ohio.gov) 수집기 — HTML 스크레이프.

어댑터 유형 = HTML 트리 스크레이프 (지오블록 · GHA 실행 필요).
  베이스  = https://codes.ohio.gov/ohio-revised-code
  구조    = 타이틀 목록 → 챕터 → 섹션 HTML
  셀렉터  = <a href="/ohio-revised-code/section-<N>"> 패턴 (GHA probe 로그로 보정 전제)

모드:
  --probe   : 베이스 구조 확인 + 타이틀/챕터/섹션 링크 패턴 로그
  --enum    : 섹션 URL 전체 열거 → _enum_laws.txt
  --collect : _enum_laws.txt 순회 → 섹션 HTML 저장
  --verify  : 4지표 검증
"""
import os
import re
import sys
import time
import ssl
import urllib.request
import urllib.error

BASE = "https://codes.ohio.gov"
INDEX_URL = BASE + "/ohio-revised-code"
RAW_DIR = os.environ.get("RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-oh/statute")
ENUM_FILE = os.path.join(RAW_DIR, "_enum_laws.txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
DELAY = float(os.environ.get("OH_DELAY", "0.4"))
SMOKE = int(os.environ.get("SMOKE", "0"))

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 섹션 링크 패턴 (ORC 섹션 = /ohio-revised-code/section-N.NN 등)
SECTION_RE = re.compile(
    r'href=["\']([^"\']*(?:/ohio-revised-code/section-|/orc/)[0-9][^"\']*)["\']',
    re.IGNORECASE,
)
# 챕터 링크 패턴
CHAPTER_RE = re.compile(
    r'href=["\']([^"\']*(?:/ohio-revised-code/chapter-|/ohio-revised-code/)[0-9][^"\']*)["\']',
    re.IGNORECASE,
)
# 타이틀 링크 패턴
TITLE_RE = re.compile(
    r'href=["\']([^"\']*(?:/ohio-revised-code/title-|/ohio-revised-code/)[IVX0-9][^"\']*)["\']',
    re.IGNORECASE,
)


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


def extract_links_pattern(html_bytes, pattern):
    text = html_bytes.decode("utf-8", "ignore")
    found = pattern.findall(text)
    result = []
    seen = set()
    for href in found:
        href = href.strip()
        if not href.startswith("http"):
            href = BASE + href if href.startswith("/") else INDEX_URL + "/" + href
        if href not in seen:
            seen.add(href)
            result.append(href)
    return result


def probe():
    print("=== OH 법전 probe (codes.ohio.gov) ===")
    os.makedirs(RAW_DIR, exist_ok=True)
    try:
        code, body = http_get(INDEX_URL)
        print(f"[index] status={code} body_len={len(body)}")
        chapters = extract_links_pattern(body, CHAPTER_RE)
        titles = extract_links_pattern(body, TITLE_RE)
        sections = extract_links_pattern(body, SECTION_RE)
        print(f"[index] 타이틀 링크 수={len(titles)} 샘플={titles[:5]}")
        print(f"[index] 챕터 링크 수={len(chapters)} 샘플={chapters[:5]}")
        print(f"[index] 섹션 링크 수={len(sections)} 샘플={sections[:5]}")
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}")
    # 챕터 1 시도
    for ch_url in [BASE + "/ohio-revised-code/chapter-1", BASE + "/ohio-revised-code/1"]:
        try:
            code, body = http_get(ch_url)
            sections = extract_links_pattern(body, SECTION_RE)
            print(f"[{ch_url}] status={code} 섹션수={len(sections)} 샘플={sections[:5]}")
        except Exception as e:
            print(f"[{ch_url}] ERR {type(e).__name__}: {e}")
        time.sleep(DELAY)
    print("주의: 지오블록 가능. 셀렉터/링크 패턴은 GHA probe 로그로 보정 필요 [추정]")


def enum():
    """타이틀 → 챕터 → 섹션 순회 → 섹션 URL 열거."""
    os.makedirs(RAW_DIR, exist_ok=True)
    all_sections = []
    seen = set()

    # 1단계: 인덱스 → 챕터 링크 수집
    try:
        code, body = http_get(INDEX_URL)
        if code != 200:
            print(f"[ERR] 인덱스 비200: {code}")
            sys.exit(1)
        chapter_urls = extract_links_pattern(body, CHAPTER_RE)
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}")
        sys.exit(1)

    if not chapter_urls:
        # 폴백: 챕터 1~179 범위 [추정]
        print("[WARN] 챕터 링크 파싱 실패 — 폴백 챕터 1~179 [추정]")
        chapter_urls = [f"{BASE}/ohio-revised-code/chapter-{i}" for i in range(1, 180)]

    print(f"[enum] 챕터 후보={len(chapter_urls)}")

    # 2단계: 챕터 → 섹션 링크
    for ci, ch_url in enumerate(chapter_urls, 1):
        try:
            code, body = http_get(ch_url)
            if code != 200:
                print(f"[ch {ci}] 비200: {code} {ch_url}")
                time.sleep(DELAY)
                continue
            sec_links = extract_links_pattern(body, SECTION_RE)
            for sl in sec_links:
                if sl not in seen:
                    seen.add(sl)
                    all_sections.append(sl)
            if ci % 20 == 0:
                print(f"  챕터 {ci}/{len(chapter_urls)} 누적섹션={len(all_sections)}", flush=True)
        except Exception as e:
            print(f"[ch {ci}] ERR {type(e).__name__}: {e}")
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
    """_enum_laws.txt 섹션 URL 순회 → HTML 저장."""
    if not os.path.exists(ENUM_FILE):
        print(f"열거 정본 없음: {ENUM_FILE} (먼저 --enum)")
        sys.exit(1)
    with open(ENUM_FILE) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    os.makedirs(RAW_DIR, exist_ok=True)
    ok = miss = skip = 0
    for i, url in enumerate(urls, 1):
        fname = url.replace(BASE, "").lstrip("/").replace("/", "_") + ".html"
        path = os.path.join(RAW_DIR, fname)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue
        if fetch_to_file_retry(url, path):
            ok += 1
        else:
            miss += 1
        if i % 200 == 0:
            print(f"  진행 {i}/{len(urls)} ok={ok} skip={skip} miss={miss}", flush=True)
        time.sleep(DELAY)
    print(f"[collect] 총={len(urls)} ok={ok} skip={skip} miss={miss}")


def verify():
    """4지표 검증."""
    if not os.path.exists(ENUM_FILE):
        print(f"열거 정본 없음: {ENUM_FILE}")
        sys.exit(1)
    with open(ENUM_FILE) as f:
        enum_urls = [ln.strip() for ln in f if ln.strip()]
    enum_set = set(enum_urls)
    dup = len(enum_urls) - len(enum_set)
    enum_fnames = set(
        u.replace(BASE, "").lstrip("/").replace("/", "_") + ".html"
        for u in enum_set
    )
    body_files = set()
    for n in os.listdir(RAW_DIR):
        if n.endswith(".html") and not n.startswith("_"):
            body_files.add(n)
    absent = enum_fnames - body_files
    orphan = body_files - enum_fnames
    rate = (len(absent) / len(enum_fnames) * 100) if enum_fnames else 0.0
    print("=== OH STATUTE 검증 4지표 ===")
    print(f"모수(섹션 URL) = {len(enum_set)}")
    print(f"저장 파일 수 = {len(body_files)}")
    print(f"부재 = {len(absent)} ({rate:.4f}%)")
    print(f"계층 고아 = {len(orphan)}")
    print(f"식별자 중복 = {dup}")
    ok = rate < 1.0 and len(orphan) == 0 and dup == 0
    print(f"판정 = {'PASS' if ok else 'FAIL'}")
    print("주의: 챕터/섹션 링크 패턴은 GHA probe 로그로 보정 필요 [추정]")


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
