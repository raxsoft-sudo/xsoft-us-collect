#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WA 주법전 (app.leg.wa.gov/RCW/) 수집기 — HTML 계층 열거 방식.

어댑터 유형 = 공식 .gov HTML 계층 열거 (타이틀→챕터→섹션).
소스 = app.leg.wa.gov (Revised Code of Washington 공식. eu_fetch_guard ALLOW 등재).
URL·정규식 전부 이 파일 내부 (eu_fetch_guard 통과 목적).

★ 실측 확인된 URL 구조 (probe 2026-06-11 [측정:curl]):
  타이틀 목록 = https://app.leg.wa.gov/RCW/default.aspx          (cite=N · 점0개 · 84개)
  타이틀 페이지 = https://app.leg.wa.gov/RCW/default.aspx?cite={T}     (챕터 cite=T.MM · 점1개)
  챕터 페이지  = https://app.leg.wa.gov/RCW/default.aspx?cite={T.C}    (섹션 cite=T.C.SSS · 점2개)
  섹션 본문   = https://app.leg.wa.gov/RCW/default.aspx?cite={T.C.S}   (200·약108KB)
  섹션 식별자  = {T}.{C}.{S} 형태 (예: 1.04.010)  [측정]
  타이틀 수   = 84  [측정]

모드:
  --probe   : 타이틀 목록→타이틀1→챕터1→섹션1 실측 확인. PASS/BLOCKED 출력.
  --enum    : 타이틀 전체 순회 → _enum_sections.txt (식별자 1줄 1개)
  --collect : _enum_sections.txt 순회 → 섹션 본문 HTML 저장 (1워커 직렬)
              SMOKE=N 환경변수 → N건 성공 후 중단 (미설정 = 전체)
  --verify  : 4지표 (모수 distinct·부재율<1%·계층고아 0·식별자중복 0)

저장 위치:
  원천 raw  = /mnt/wsl/usdata/xsoft_data/raw/us-wa/statute/
  열거 정본 = .../us-wa/statute/_enum_sections.txt
  본문 파일 = {섹션식별자}.html  (예: 1.04.010.html)

주의:
  - 호스트당 동시요청 = 1 (1워커 직렬 디폴트. ≤2 절대)
  - 429 시 지수 백오프 30초+
  - 멱등 skip = 파일 존재 & size > 0
  - /mnt/d 저장 금지 (결정_100 = ext4 raw 전용)
"""

import os
import re
import sys
import time
import ssl
import urllib.request
import urllib.error

# ── 상수 ──────────────────────────────────────────────────────────────────────
HOST      = "app.leg.wa.gov"
BASE      = "https://" + HOST
TOC_URL   = BASE + "/RCW/default.aspx"
RAW_DIR   = os.environ.get("RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-wa/statute")
ENUM_FILE = os.path.join(RAW_DIR, "_enum_sections.txt")
LOG_FILE  = os.path.join(RAW_DIR, "_run.log")

UA    = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 wa-statute-collect/1.0"
DELAY = float(os.environ.get("WA_DELAY", "1.0"))
BACKOFF_BASE = float(os.environ.get("WA_BACKOFF", "30.0"))
SMOKE = os.environ.get("SMOKE", "")  # SMOKE=N → N건 성공 후 중단

# ★ 실측 확인 정규식 (probe 2026-06-11 [측정:curl])
# cite 값 추출 후 점 개수로 분류: 0=타이틀, 1=챕터, 2=섹션
CITE_RE = re.compile(r'[Cc]ite=([0-9]+(?:\.[0-9A-Za-z]+){0,2})', re.IGNORECASE)


def _dots(cite: str) -> int:
    return cite.count(".")


def _sec_url(cite: str) -> str:
    return f"{BASE}/RCW/default.aspx?cite={cite}"


CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE


# ── 유틸 ──────────────────────────────────────────────────────────────────────
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        os.makedirs(RAW_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def http_get(url: str, timeout: int = 30) -> tuple:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.getcode(), r.read()


def fetch_retry(url: str, backoff: float = BACKOFF_BASE, max_retry: int = 5) -> tuple:
    wait = backoff
    for attempt in range(max_retry):
        try:
            code, body = http_get(url)
            if code == 200 and body:
                return True, body
            if code == 429:
                log(f"  429 백오프 {wait:.0f}s [{url}]")
                time.sleep(wait)
                wait *= 2
                continue
            log(f"  HTTP {code} [{url}]")
            return False, b""
        except urllib.error.HTTPError as e:
            if e.code == 429:
                log(f"  429 백오프 {wait:.0f}s [{url}]")
                time.sleep(wait)
                wait *= 2
                continue
            log(f"  HTTPError {e.code} [{url}]")
            return False, b""
        except Exception as ex:
            log(f"  오류({type(ex).__name__}) 백오프 {wait:.0f}s [{url}]")
            time.sleep(wait)
            wait *= 2
    return False, b""


def fetch_to_file(url: str, path: str) -> bool:
    ok, body = fetch_retry(url)
    if ok:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(body)
    return ok


# ── probe ─────────────────────────────────────────────────────────────────────
def probe():
    log("=== WA 법전 probe (app.leg.wa.gov/RCW/) ===")
    os.makedirs(RAW_DIR, exist_ok=True)

    log(f"[1] 타이틀 목록 GET: {TOC_URL}")
    ok, body = fetch_retry(TOC_URL)
    if not ok:
        log("BLOCKED: 타이틀 목록 접속 실패")
        sys.exit(2)
    txt = body.decode("utf-8", "ignore")
    titles = sorted({c for c in CITE_RE.findall(txt) if _dots(c) == 0}, key=lambda x: int(x))
    log(f"  타이틀 {len(titles)}개 (첫8: {titles[:8]})")
    if not titles:
        log("BLOCKED: 타이틀 cite 패턴 미발견 — JS 렌더링 또는 구조 변경")
        log(f"  응답 앞 500자: {txt[:500]}")
        sys.exit(2)
    time.sleep(DELAY)

    t0 = titles[0]
    log(f"[2] 타이틀{t0} GET: {_sec_url(t0)}")
    ok, body = fetch_retry(_sec_url(t0))
    if not ok:
        log(f"BLOCKED: 타이틀{t0} 접속 실패")
        sys.exit(2)
    txt2 = body.decode("utf-8", "ignore")
    chapters = sorted({c for c in CITE_RE.findall(txt2) if _dots(c) == 1})
    log(f"  챕터 {len(chapters)}개 (첫3: {chapters[:3]})")
    if not chapters:
        log("BLOCKED: 챕터 cite 패턴 미발견")
        sys.exit(2)
    time.sleep(DELAY)

    c0 = chapters[0]
    log(f"[3] 챕터{c0} GET: {_sec_url(c0)}")
    ok, body = fetch_retry(_sec_url(c0))
    if not ok:
        log(f"BLOCKED: 챕터{c0} 접속 실패")
        sys.exit(2)
    txt3 = body.decode("utf-8", "ignore")
    secs = sorted({c for c in CITE_RE.findall(txt3) if _dots(c) == 2})
    log(f"  섹션 {len(secs)}개 (첫5: {secs[:5]})")
    if not secs:
        log("BLOCKED: 섹션 cite 패턴 미발견")
        sys.exit(2)
    time.sleep(DELAY)

    s0 = secs[0]
    log(f"[4] 섹션 본문 GET: {_sec_url(s0)}")
    ok, body = fetch_retry(_sec_url(s0))
    if not ok:
        log(f"BLOCKED: 섹션 본문 접속 실패 {_sec_url(s0)}")
        sys.exit(2)
    log(f"  섹션 본문 응답 크기={len(body)}B — PASS")

    log("=== probe PASS ===")
    log(f"  타이틀 수={len(titles)} · 타이틀{t0} 챕터={len(chapters)} · 챕터{c0} 섹션={len(secs)}")
    log("  [미확인] 전체 모수 = --enum 실행 후 확정")


# ── enum ──────────────────────────────────────────────────────────────────────
def enum():
    os.makedirs(RAW_DIR, exist_ok=True)
    log("=== WA 법전 enum 시작 ===")

    ok, body = fetch_retry(TOC_URL)
    if not ok:
        log("BLOCKED: 타이틀 목록 접속 실패 — enum 중단")
        sys.exit(2)
    txt = body.decode("utf-8", "ignore")
    titles = sorted({c for c in CITE_RE.findall(txt) if _dots(c) == 0}, key=lambda x: int(x))
    log(f"  타이틀 {len(titles)}개")
    if not titles:
        log("BLOCKED: 타이틀 패턴 미발견 — enum 중단")
        sys.exit(2)
    time.sleep(DELAY)

    seen: set = set()
    for ti, t in enumerate(titles, 1):
        ok, body = fetch_retry(_sec_url(t))
        if not ok:
            log(f"  [skip] 타이틀{t} 접속 실패")
            time.sleep(DELAY)
            continue
        txt_t = body.decode("utf-8", "ignore")
        chapters = sorted({c for c in CITE_RE.findall(txt_t) if _dots(c) == 1})
        time.sleep(DELAY)

        for c in chapters:
            ok2, body2 = fetch_retry(_sec_url(c))
            if not ok2:
                log(f"  [skip] 챕터{c} 접속 실패")
                time.sleep(DELAY)
                continue
            txt_c = body2.decode("utf-8", "ignore")
            secs = [s for s in CITE_RE.findall(txt_c) if _dots(s) == 2 and s.startswith(c + ".")]
            before = len(seen)
            for s in secs:
                seen.add(s)
            added = len(seen) - before
            if added > 0:
                log(f"    챕터{c} +{added}섹션 → 누적={len(seen)}")
            time.sleep(DELAY)
        log(f"  [{ti}/{len(titles)}] 타이틀{t} 완료 누적={len(seen)}")

    def sort_key(cite: str):
        parts = cite.split(".")
        return tuple(int(re.sub(r"[^0-9]", "", p) or "0") for p in parts)

    sorted_secs = sorted(seen, key=sort_key)
    with open(ENUM_FILE, "w", encoding="utf-8") as f:
        for s in sorted_secs:
            f.write(s + "\n")
    log(f"[OK] 열거 정본 저장: {ENUM_FILE} ({len(sorted_secs)}건)")
    log("[미확인] 일부 챕터 접속 실패 시 모수 과소. --verify로 부재율 확인 필요.")


# ── collect ───────────────────────────────────────────────────────────────────
def collect():
    if not os.path.exists(ENUM_FILE):
        log(f"BLOCKED: 열거 정본 없음 ({ENUM_FILE}) — 먼저 --enum 실행")
        sys.exit(2)

    smoke_limit = 0
    if SMOKE:
        try:
            smoke_limit = int(SMOKE)
        except ValueError:
            log(f"SMOKE 환경변수 오류: '{SMOKE}' — 정수 필요")
            sys.exit(1)

    with open(ENUM_FILE, encoding="utf-8") as f:
        entries = [ln.strip() for ln in f if ln.strip()]

    os.makedirs(RAW_DIR, exist_ok=True)
    ok_cnt = miss_cnt = skip_cnt = 0
    total = len(entries)
    log(f"=== WA 법전 collect 시작 (총={total}, SMOKE={smoke_limit or '전체'}) ===")

    for i, sec_id in enumerate(entries, 1):
        safe_id = re.sub(r"[/\\:*?\"<>|]", "_", sec_id)
        path = os.path.join(RAW_DIR, f"{safe_id}.html")

        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip_cnt += 1
            if smoke_limit and ok_cnt >= smoke_limit:
                break
            continue

        ok = fetch_to_file(_sec_url(sec_id), path)
        if ok:
            ok_cnt += 1
        else:
            miss_cnt += 1

        if i % 200 == 0:
            log(f"  진행 {i}/{total} ok={ok_cnt} skip={skip_cnt} miss={miss_cnt}")

        if smoke_limit and ok_cnt >= smoke_limit:
            log(f"[SMOKE={smoke_limit}] 목표 달성 → 중단")
            break
        time.sleep(DELAY)

    log(f"[collect 완료] 총={total} ok={ok_cnt} skip={skip_cnt} miss={miss_cnt}")


# ── verify ────────────────────────────────────────────────────────────────────
def verify():
    if not os.path.exists(ENUM_FILE):
        log(f"BLOCKED: 열거 정본 없음 ({ENUM_FILE})")
        sys.exit(2)

    with open(ENUM_FILE, encoding="utf-8") as f:
        enum_ids = [ln.strip() for ln in f if ln.strip()]
    enum_set  = set(enum_ids)
    dup_count = len(enum_ids) - len(enum_set)

    body_ids: set = set()
    if os.path.exists(RAW_DIR):
        for fn in os.listdir(RAW_DIR):
            if fn.endswith(".html") and not fn.startswith("_"):
                body_ids.add(fn[:-5])

    file_count = len(body_ids)
    absent_count = max(0, len(enum_set) - file_count)
    rate = (absent_count / len(enum_set) * 100) if enum_set else 0.0
    orphan_count = max(0, file_count - len(enum_set))

    log("=== WA STATUTE 검증 4지표 ===")
    log(f"  모수(distinct 섹션 id) = {len(enum_set)}")
    log(f"  본문 저장 파일 수      = {file_count}")
    log(f"  부재(열거-파일)        = {absent_count} ({rate:.4f}%)")
    log(f"  계층 고아(파일>열거)   = {orphan_count}")
    log(f"  식별자 중복            = {dup_count}")
    passed = rate < 1.0 and orphan_count == 0 and dup_count == 0
    log(f"  판정 = {'PASS' if passed else 'FAIL'}")
    if rate >= 1.0:
        log(f"  [미달] 부재율 {rate:.4f}% ≥ 1% → 재수집 필요")


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--probe"
    os.makedirs(RAW_DIR, exist_ok=True)
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
        print("사용법: python3 dev_us_wa_statute_collect.py [--probe|--enum|--collect|--verify]")
