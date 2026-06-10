#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RI 법전 (webserver.rilegislature.gov) 수집기 — 정적 HTML 크롤.

어댑터 유형 = 정적 HTML 트리 (지오블록 · GHA 실행 필요).
  인덱스  = http://webserver.rilegislature.gov/Statutes/
  타이틀  = /Statutes/TITLE<N>.htm  (N=1~46)
  챕터    = /Statutes/TITLE<N>/<챕터>.htm (링크 파싱)
  섹션    = /Statutes/TITLE<N>/<섹션>.htm (링크 파싱)

모드:
  --probe   : 인덱스 응답 확인 + 타이틀 1~3 링크 파싱 로그
  --enum    : 전체 섹션 ID(경로) 열거 → _enum_laws.txt
  --collect : _enum_laws.txt 순회 → HTML 저장
  --verify  : 4지표 검증
"""
import os
import re
import sys
import time
import ssl
import urllib.request
import urllib.error
from html.parser import HTMLParser

BASE = "http://webserver.rilegislature.gov"
INDEX_URL = BASE + "/Statutes/"
RAW_DIR = os.environ.get("RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-ri/statute")
ENUM_FILE = os.path.join(RAW_DIR, "_enum_laws.txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
DELAY = float(os.environ.get("RI_DELAY", "0.4"))
SMOKE = int(os.environ.get("SMOKE", "0"))
TITLE_MAX = 46

# http (평문) = SSL 컨텍스트 불필요하지만 통일
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

HREF_RE = re.compile(r'href=["\']([^"\']+\.htm[^"\']*)["\']', re.IGNORECASE)


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
        except Exception:
            time.sleep(wait)
            wait *= 2
    return False


def extract_links(html_bytes, base_url):
    """href .htm 링크를 절대 URL로 반환."""
    text = html_bytes.decode("utf-8", "ignore")
    links = []
    for m in HREF_RE.finditer(text):
        href = m.group(1).strip()
        if href.startswith("http"):
            links.append(href)
        elif href.startswith("/"):
            links.append(BASE + href)
        else:
            # 상대경로 = base_url 기준
            bdir = base_url.rsplit("/", 1)[0]
            links.append(bdir + "/" + href)
    return links


def probe():
    print("=== RI 법전 probe (webserver.rilegislature.gov) ===")
    os.makedirs(RAW_DIR, exist_ok=True)
    try:
        code, body = http_get(INDEX_URL)
        print(f"[index] status={code} body_len={len(body)}")
        links = extract_links(body, INDEX_URL)
        htm_links = [l for l in links if "/Statutes/" in l][:10]
        print(f"[index] /Statutes/ 링크 샘플: {htm_links[:5]}")
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}")
    # 타이틀 1 시도
    for t in range(1, 4):
        url = f"{INDEX_URL}TITLE{t}.htm"
        try:
            code, body = http_get(url)
            links = extract_links(body, url)
            print(f"[TITLE{t}] status={code} 링크수={len(links)} 샘플={links[:3]}")
        except Exception as e:
            print(f"[TITLE{t}] ERR {type(e).__name__}: {e}")
        time.sleep(DELAY)
    print("주의: 지오블록 가능. GHA 미국 IP 실행 필요. 링크 구조를 GHA 로그로 보정할 것.")


def enum():
    """타이틀 1~46 → 챕터/섹션 링크 파싱 → 섹션 URL 열거."""
    os.makedirs(RAW_DIR, exist_ok=True)
    all_sections = []
    seen = set()

    for t in range(1, TITLE_MAX + 1):
        title_url = f"{INDEX_URL}TITLE{t}.htm"
        try:
            code, body = http_get(title_url)
            if code != 200:
                print(f"[TITLE{t}] 비200 = {code}")
                time.sleep(DELAY)
                continue
        except Exception as e:
            print(f"[TITLE{t}] ERR {type(e).__name__}: {e}")
            time.sleep(DELAY)
            continue

        links = extract_links(body, title_url)
        # 섹션 패턴 탐지: .htm 파일 중 TITLE<N> 하위 경로
        sec_links = [l for l in links if f"TITLE{t}" in l and l.endswith(".htm")]
        for sl in sec_links:
            if sl not in seen:
                seen.add(sl)
                all_sections.append(sl)
        print(f"[TITLE{t}] 섹션 후보={len(sec_links)} 누적={len(all_sections)}")
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
        # URL을 파일명으로 변환 (/ → _)
        fname = url.replace(BASE, "").lstrip("/").replace("/", "_")
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
    """4지표 = 모수·부재율·계층고아·식별자중복."""
    if not os.path.exists(ENUM_FILE):
        print(f"열거 정본 없음: {ENUM_FILE}")
        sys.exit(1)
    with open(ENUM_FILE) as f:
        enum_ids = [ln.strip() for ln in f if ln.strip()]
    enum_set = set(enum_ids)
    dup = len(enum_ids) - len(enum_set)
    body_files = set()
    for n in os.listdir(RAW_DIR):
        if n.endswith(".htm") and not n.startswith("_"):
            body_files.add(n)
    # enum URL → 파일명 변환 후 대조
    enum_fnames = set(
        u.replace(BASE, "").lstrip("/").replace("/", "_") for u in enum_set
    )
    absent = enum_fnames - body_files
    orphan = body_files - enum_fnames
    rate = (len(absent) / len(enum_fnames) * 100) if enum_fnames else 0.0
    print("=== RI STATUTE 검증 4지표 ===")
    print(f"모수(섹션 URL) = {len(enum_set)}")
    print(f"저장 파일 수 = {len(body_files)}")
    print(f"부재 = {len(absent)} ({rate:.4f}%)")
    print(f"계층 고아 = {len(orphan)}")
    print(f"식별자 중복 = {dup}")
    ok = rate < 1.0 and len(orphan) == 0 and dup == 0
    print(f"판정 = {'PASS' if ok else 'FAIL'}")
    print("주의: 링크 구조(타이틀/챕터/섹션 계층)는 GHA probe 로그로 보정 필요 [추정]")


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
