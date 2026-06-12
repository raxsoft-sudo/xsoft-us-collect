#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WI 법전 (docs.legis.wisconsin.gov) 수집기 — 챕터 PDF 크롤.

어댑터 유형 = 챕터 PDF 스크레이프 (지오블록 · GHA 실행 필요).
  베이스  = https://docs.legis.wisconsin.gov/statutes/statutes
  챕터 목록 인덱스 파싱 → 챕터 PDF 다운로드
  PDF 경로 패턴 = /statutes/statutes/<CH>  (HTML 리다이렉트 후 PDF 링크)
  또는 직접 = /document/statutes/ch.<N>  (GHA probe로 확인 필요)

모드:
  --probe   : 베이스 인덱스 응답 확인 + 챕터 링크 패턴 로그
  --enum    : 챕터 번호 목록 → _enum_laws.txt (숫자·문자 챕터 포함)
  --collect : _enum_laws.txt 순회 → 챕터 HTML/PDF 저장
  --verify  : 4지표 검증
"""
import os
import re
import sys
import time
import ssl
import urllib.request
import urllib.error

BASE = "https://docs.legis.wisconsin.gov"
INDEX_URL = BASE + "/statutes/statutes"
RAW_DIR = os.environ.get("RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-wi/statute")
ENUM_FILE = os.path.join(RAW_DIR, "_enum_laws.txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
DELAY = float(os.environ.get("WI_DELAY", "0.5"))
SMOKE = int(os.environ.get("SMOKE", "0"))

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 챕터 번호 패턴: /statutes/statutes/<CH> 또는 숫자 챕터
CHAPTER_RE = re.compile(
    r'href=["\']([^"\']*(?:statutes/statutes/|statutes/ch\.)[^"\']+)["\']',
    re.IGNORECASE,
)
CHAPTER_NUM_RE = re.compile(r'/statutes/(?:statutes/|ch\.)([0-9a-zA-Z_]+)', re.IGNORECASE)


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.getcode(), r.read()


def fetch_to_file_retry(url, path, backoff=2.0, max_retry=5):
    wait = backoff
    for attempt in range(max_retry):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                if r.getcode() != 200:
                    return False
                with open(path, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            return True
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
    print("=== WI 법전 probe (docs.legis.wisconsin.gov) ===")
    os.makedirs(RAW_DIR, exist_ok=True)
    try:
        code, body = http_get(INDEX_URL)
        text = body.decode("utf-8", "ignore")
        print(f"[index] status={code} body_len={len(body)}")
        # 챕터 링크 패턴 탐지
        chapter_links = CHAPTER_RE.findall(text)
        print(f"[index] 챕터 링크 후보 수: {len(chapter_links)}")
        print(f"[index] 샘플 (최대 10개): {chapter_links[:10]}")
        # 숫자 챕터 ID 추출 시도
        nums = [CHAPTER_NUM_RE.search(l) for l in chapter_links if CHAPTER_NUM_RE.search(l)]
        ids = [m.group(1) for m in nums if m]
        print(f"[index] 챕터 ID 샘플: {ids[:10]}")
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}")
    # 직접 PDF 패턴 시도
    for ch in [1, 2, 100]:
        url = f"{BASE}/document/statutes/ch.%20{ch}"
        try:
            code, body = http_get(url)
            print(f"[ch.{ch}] status={code} body_len={len(body)}")
        except Exception as e:
            print(f"[ch.{ch}] ERR {type(e).__name__}: {e}")
        time.sleep(DELAY)
    print("주의: 지오블록 가능. GHA probe 로그로 챕터 링크 구조 보정 필요 [추정]")


def enum():
    """인덱스 페이지 → 챕터 ID 목록 → _enum_laws.txt."""
    os.makedirs(RAW_DIR, exist_ok=True)
    try:
        code, body = http_get(INDEX_URL)
        if code != 200:
            print(f"[ERR] 인덱스 비200: {code}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}")
        sys.exit(1)

    text = body.decode("utf-8", "ignore")
    chapter_links = CHAPTER_RE.findall(text)
    ids = []
    seen = set()
    for link in chapter_links:
        m = CHAPTER_NUM_RE.search(link)
        if m:
            cid = m.group(1)
            if cid not in seen:
                seen.add(cid)
                ids.append(cid)

    if not ids:
        # 인덱스 파싱 0건 = 구조 미확인. 조작 폴백 금지(0순위 계명1).
        # GHA 미국 IP enum 로그로 실제 챕터 링크 패턴 확인 후 정규식 보정.
        print("[FATAL] 인덱스 챕터 링크 파싱 0건 — 구조 미확인. 조작 폴백 제거됨.")
        print(f"[FATAL] INDEX_URL={INDEX_URL} 응답을 GHA 로그로 확인하고 CHAPTER_RE 보정 필요.")
        sys.exit(1)

    if SMOKE > 0:
        ids = ids[:SMOKE]
        print(f"[SMOKE={SMOKE}] 열거 제한")

    with open(ENUM_FILE, "w") as f:
        for cid in ids:
            f.write(cid + "\n")
    print(f"[OK] 열거 정본 저장: {ENUM_FILE} ({len(ids)}건)")


def collect():
    """_enum_laws.txt 챕터 ID 순회 → HTML 저장."""
    if not os.path.exists(ENUM_FILE):
        print(f"열거 정본 없음: {ENUM_FILE} (먼저 --enum)")
        sys.exit(1)
    with open(ENUM_FILE) as f:
        ids = [ln.strip() for ln in f if ln.strip()]
    os.makedirs(RAW_DIR, exist_ok=True)
    ok = miss = skip = 0
    for i, cid in enumerate(ids, 1):
        # 챕터별 HTML 저장 (PDF는 GHA 로그 확인 후 보정)
        url = f"{INDEX_URL}/{cid}"
        path = os.path.join(RAW_DIR, f"ch_{cid}.html")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue
        if fetch_to_file_retry(url, path):
            ok += 1
        else:
            # PDF 패턴 시도
            url_pdf = f"{BASE}/document/statutes/ch.%20{cid}"
            path_pdf = os.path.join(RAW_DIR, f"ch_{cid}.pdf")
            if fetch_to_file_retry(url_pdf, path_pdf):
                ok += 1
            else:
                miss += 1
        if i % 100 == 0:
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
        if (n.endswith(".html") or n.endswith(".pdf")) and not n.startswith("_"):
            # ch_<N>.html 또는 ch_<N>.pdf
            cid = n.replace("ch_", "").rsplit(".", 1)[0]
            body_ids.add(cid)
    absent = enum_set - body_ids
    orphan = body_ids - enum_set
    rate = (len(absent) / len(enum_set) * 100) if enum_set else 0.0
    print("=== WI STATUTE 검증 4지표 ===")
    print(f"모수(챕터 ID) = {len(enum_set)}")
    print(f"저장 파일 수 = {len(body_ids)}")
    print(f"부재 = {len(absent)} ({rate:.4f}%)")
    print(f"계층 고아 = {len(orphan)}")
    print(f"식별자 중복 = {dup}")
    ok = rate < 1.0 and len(orphan) == 0 and dup == 0
    print(f"판정 = {'PASS' if ok else 'FAIL'}")
    print("주의: 챕터 링크 구조·PDF 경로는 GHA probe 로그로 보정 필요 [추정]")


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
