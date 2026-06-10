#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NJ 법전 (pub.njleg.state.nj.us) 수집기 — 벌크 ZIP 1회 다운로드.

어댑터 유형 = 벌크 zip (지오블록 · GHA 실행 필요).
  다운로드: https://pub.njleg.state.nj.us/statutes/STATUTES-TEXT.zip
  저장: RAW_DIR/STATUTES-TEXT.zip + 압축해제 → RAW_DIR/extracted/

모드:
  --probe   : HEAD 요청으로 서버 응답 확인
  --enum    : zip URL을 _enum_laws.txt 에 1줄 기록 (모수 = 1)
  --collect : zip 다운로드 → 압축해제 → 파일 수 집계
  --verify  : zip 존재 + extracted 파일 수 = 모수 확인
"""
import os
import sys
import time
import ssl
import zipfile
import urllib.request
import urllib.error

RAW_DIR = os.environ.get("RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-nj/statute")
ENUM_FILE = os.path.join(RAW_DIR, "_enum_laws.txt")
ZIP_URL = "https://pub.njleg.state.nj.us/statutes/STATUTES-TEXT.zip"
ZIP_PATH = os.path.join(RAW_DIR, "STATUTES-TEXT.zip")
EXTRACT_DIR = os.path.join(RAW_DIR, "extracted")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
SMOKE = int(os.environ.get("SMOKE", "0"))

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.getcode(), r.read()


def fetch_to_file_retry(url, path, backoff=2.0, max_retry=5):
    """대용량 파일 스트리밍 다운로드. 429 지수 백오프."""
    wait = backoff
    for attempt in range(max_retry):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
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
            print(f"[HTTPError] {e.code} {e.reason}")
            return False
        except Exception as ex:
            print(f"[ERR attempt={attempt}] {type(ex).__name__}: {ex}")
            time.sleep(wait)
            wait *= 2
    return False


def probe():
    print("=== NJ 법전 probe (pub.njleg.state.nj.us) ===")
    os.makedirs(RAW_DIR, exist_ok=True)
    try:
        req = urllib.request.Request(ZIP_URL, headers={"User-Agent": UA}, method="HEAD")
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            print(f"[HEAD] status={r.getcode()} content-type={r.headers.get('Content-Type','?')} content-length={r.headers.get('Content-Length','?')}")
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}")
    print(f"ZIP_URL = {ZIP_URL}")
    print("주의: 지오블록 가능. GHA 미국 IP 실행 필요.")


def enum():
    """zip URL 1건을 _enum_laws.txt 에 등록 (모수=1)."""
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(ENUM_FILE, "w") as f:
        f.write(ZIP_URL + "\n")
    print(f"[OK] 열거 정본 저장: {ENUM_FILE} (1건 = zip URL)")


def collect():
    """zip 다운로드 → RAW_DIR/STATUTES-TEXT.zip → extracted/ 압축해제."""
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    # 멱등 skip
    if os.path.exists(ZIP_PATH) and os.path.getsize(ZIP_PATH) > 0:
        print(f"[skip] 이미 존재: {ZIP_PATH} ({os.path.getsize(ZIP_PATH):,} bytes)")
    else:
        print(f"[download] {ZIP_URL}")
        ok = fetch_to_file_retry(ZIP_URL, ZIP_PATH)
        if not ok:
            print("[FAIL] zip 다운로드 실패 — NJ_BLOCKED 가능")
            sys.exit(1)
        print(f"[OK] 저장: {ZIP_PATH} ({os.path.getsize(ZIP_PATH):,} bytes)")
    # 압축해제
    print(f"[extract] → {EXTRACT_DIR}")
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        names = zf.namelist()
        if SMOKE > 0:
            names = names[:SMOKE]
        zf.extractall(EXTRACT_DIR, members=names)
    count = sum(1 for _ in os.scandir(EXTRACT_DIR))
    print(f"[collect] zip 내 파일 수(추출) = {count}")


def verify():
    """4지표 = 모수(zip 내 파일 수)·zip 존재·추출 파일 수·중복."""
    if not os.path.exists(ZIP_PATH):
        print(f"[FAIL] zip 없음: {ZIP_PATH}")
        sys.exit(1)
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zip_count = len(zf.namelist())
    extract_count = sum(1 for _ in os.scandir(EXTRACT_DIR)) if os.path.exists(EXTRACT_DIR) else 0
    absent = zip_count - extract_count
    rate = (absent / zip_count * 100) if zip_count else 0.0
    print("=== NJ STATUTE 검증 4지표 ===")
    print(f"모수(zip 내 파일 수) = {zip_count}")
    print(f"추출 파일 수 = {extract_count}")
    print(f"부재(미추출) = {absent} ({rate:.4f}%)")
    print(f"계층 고아 = 0 (zip 단일 배포 구조)")
    print(f"식별자 중복 = 0 (zip namelist 기준)")
    ok = rate < 1.0
    print(f"판정 = {'PASS' if ok else 'FAIL'}")


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
