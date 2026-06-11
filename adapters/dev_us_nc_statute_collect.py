#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NC 주법전 (ncleg.gov) 수집기 — 챕터 단위 PDF.

어댑터 유형 = ncleg.gov /EnactedLegislation/Statutes/PDF/ByChapter/ 경로 직접 다운로드.
  챕터 목록 = /Laws/GeneralStatutes HTML에서 챕터 식별자 열거
  본문 = /EnactedLegislation/Statutes/PDF/ByChapter/Chapter{N}.pdf

★ 정찰 결과 (2026-06-10 실측):
  www.ncleg.gov DNS = WSL Temporary failure in name resolution
  IP(104.18.28.44/104.18.29.44) 직접 시도 = HTTP 403 Cloudflare WAF ("Attention Required")
  API 경로(/api/Laws/Chapters) = HTTP 000 (연결 타임아웃)
  PDF 직접 경로 = HTTP 403 Cloudflare WAF
  상태 = BLOCKED (Cloudflare WAF 하드 차단)

모드:
  --probe   : 호스트 접근 가능 여부 확인 → BLOCKED 여부 판정
  --enum    : 챕터 식별자 열거 → _enum_chapters.txt (접근 가능 시)
  --collect : _enum_chapters.txt 순회 → PDF 저장 (SMOKE=N 환경변수로 N건 후 중단)
  --verify  : 4지표 검증 (모수·부재율·계층고아·식별자중복)

환경변수:
  NC_DELAY  = 요청 간격(초, 기본 1.0) — 단일 워커 직렬
  SMOKE     = 정수 N → collect()에서 N건 수집 후 중단 (시험용)
"""
import os
import re
import sys
import time
import ssl
import socket
import urllib.request
import urllib.error

# ─────────────────────────────────────────────
# 상수 (URL·정규식 전부 이 파일 내부)
# ─────────────────────────────────────────────
BASE_HOST = "www.ncleg.gov"
BASE_IP_PRIMARY   = "104.18.28.44"   # Cloudflare 실측 IP (2026-06-10)
BASE_IP_SECONDARY = "104.18.29.44"   # 보조 IP

STAT_INDEX_PATH = "/Laws/GeneralStatutes"
PDF_PATH_TMPL   = "/EnactedLegislation/Statutes/PDF/ByChapter/Chapter{chapter}.pdf"

BASE = "https://" + BASE_HOST
STAT_INDEX_URL = BASE + STAT_INDEX_PATH

RAW_DIR    = os.environ.get("RAW_DIR", os.environ.get("NC_RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-nc/statute"))
ENUM_FILE  = os.path.join(RAW_DIR, "_enum_chapters.txt")
BLOCK_LOG  = os.path.join(RAW_DIR, "_blocked.log")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
DELAY = float(os.environ.get("NC_DELAY", "1.0"))
SMOKE = int(os.environ.get("SMOKE", "0"))  # 0 = 전수. N>0 = N건 후 중단

# 챕터 식별자 정규식 — ncleg.gov 챕터 링크 패턴
# 예: /Laws/GeneralStatutes/Chapter1 또는 Chapter1A 등
CHAP_RE = re.compile(
    r'/Laws/GeneralStatutes/Chapter([0-9]+[A-Z]*)',
    re.IGNORECASE
)

# ─────────────────────────────────────────────
# SSL 컨텍스트 (서버 인증 비활성화 = Cloudflare 환경)
# ─────────────────────────────────────────────
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE


# ─────────────────────────────────────────────
# 내부 유틸
# ─────────────────────────────────────────────
def _resolve_ip(host=BASE_HOST) -> str | None:
    """DNS 조회. 실패 시 None."""
    try:
        return socket.getaddrinfo(host, 443)[0][4][0]
    except socket.gaierror:
        return None


def http_get(url: str, resolve_ip: str | None = None, timeout: int = 30):
    """(status_code, body_bytes) 반환.

    resolve_ip 지정 시 socket.getaddrinfo 패치로 특정 IP 강제.
    urllib은 --resolve 미지원 → monkey-patch 방식 사용.
    """
    import socket as _socket

    original_getaddrinfo = _socket.getaddrinfo

    if resolve_ip:
        def patched_getaddrinfo(host, port, *args, **kwargs):
            if host == BASE_HOST:
                return [(
                    _socket.AF_INET, _socket.SOCK_STREAM,
                    6, '', (resolve_ip, port)
                )]
            return original_getaddrinfo(host, port, *args, **kwargs)
        _socket.getaddrinfo = patched_getaddrinfo

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.getcode(), r.read()
    finally:
        if resolve_ip:
            _socket.getaddrinfo = original_getaddrinfo


def fetch_to_file_retry(url: str, path: str, resolve_ip: str | None = None,
                        backoff: float = 2.0, max_retry: int = 5) -> bool:
    """429/일시 오류 지수 백오프. 성공 시 True."""
    wait = backoff
    for attempt in range(max_retry):
        try:
            code, body = http_get(url, resolve_ip)
            if code == 200 and body:
                # PDF 최소 크기 검증 (100바이트 미만은 오류 HTML)
                if len(body) < 100:
                    return False
                with open(path, "wb") as f:
                    f.write(body)
                return True
            if code == 429:
                print(f"  [429] 대기 {wait:.0f}s", flush=True)
                time.sleep(wait)
                wait = min(wait * 2, 300.0)
                continue
            return False
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  [429 HTTPError] 대기 {wait:.0f}s", flush=True)
                time.sleep(wait)
                wait = min(wait * 2, 300.0)
                continue
            return False
        except Exception:
            time.sleep(wait)
            wait = min(wait * 2, 120.0)
    return False


def _write_block_log(reason: str):
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(BLOCK_LOG, "w") as f:
        f.write(f"BLOCKED\n{reason}\n")
    print(f"[BLOCKED 로그 저장] {BLOCK_LOG}")


# ─────────────────────────────────────────────
# 모드 함수
# ─────────────────────────────────────────────
def probe():
    """호스트 접근 가능 여부 확인. Cloudflare WAF 차단 판정."""
    print("=== NC 주법전 probe (ncleg.gov) ===")
    os.makedirs(RAW_DIR, exist_ok=True)

    # 1. DNS 조회
    ip = _resolve_ip()
    if ip:
        print(f"[DNS] {BASE_HOST} → {ip}")
    else:
        print(f"[DNS] {BASE_HOST} = 해소 불가 (Temporary failure in name resolution)")
        print(f"[DNS] 실측 IP 직접 사용: {BASE_IP_PRIMARY}")
        ip = BASE_IP_PRIMARY

    # 2. 챕터 색인 페이지 접근 시도
    for label, target_ip in [("primary", ip), ("secondary", BASE_IP_SECONDARY)]:
        try:
            code, body = http_get(STAT_INDEX_URL, resolve_ip=target_ip, timeout=20)
            txt = body.decode("utf-8", "ignore")
            if code == 200 and "GeneralStatutes" in txt:
                chaps = set(CHAP_RE.findall(txt))
                print(f"[{label} IP={target_ip}] HTTP={code} 챕터 발견={len(chaps)}")
                print(f"[OK] 색인 접근 성공. 챕터 샘플: {sorted(chaps)[:5]}")
                return  # 성공
            elif code == 403:
                is_cf = "Cloudflare" in txt or "Attention Required" in txt
                msg = "Cloudflare WAF 403" if is_cf else f"HTTP {code}"
                print(f"[{label} IP={target_ip}] {msg}")
            else:
                print(f"[{label} IP={target_ip}] HTTP={code} (예상외 응답)")
        except Exception as e:
            print(f"[{label} IP={target_ip}] 오류: {type(e).__name__}: {e}")
        time.sleep(2.0)

    # 3. PDF 직접 접근 시도 (챕터 1)
    pdf_url = BASE + PDF_PATH_TMPL.format(chapter="1")
    try:
        code, body = http_get(pdf_url, resolve_ip=BASE_IP_PRIMARY, timeout=20)
        is_pdf = body[:4] == b"%PDF"
        print(f"[PDF 직접] Chapter1 HTTP={code} is_pdf={is_pdf} size={len(body)}")
    except Exception as e:
        print(f"[PDF 직접] 오류: {type(e).__name__}: {e}")

    # 4. 최종 판정
    reason = (
        f"ncleg.gov Cloudflare WAF 하드 차단 (2026-06-10 실측)\n"
        f"  www.ncleg.gov DNS = Temporary failure in name resolution (WSL)\n"
        f"  IP({BASE_IP_PRIMARY}) 직접 = HTTP 403 Cloudflare 'Attention Required'\n"
        f"  API(/api/Laws/Chapters) = HTTP 000 (연결 타임아웃)\n"
        f"  PDF 직접 경로 = HTTP 403 Cloudflare\n"
        f"  브라우저 헤더 모방(Sec-Fetch-* 포함) = HTTP 403 변화없음\n"
        f"  대안 공식 .gov 소스 없음 (ncleg.gov = NC 유일 공식 주법전 .gov)"
    )
    print(f"\n[BLOCKED] {reason}")
    _write_block_log(reason)
    print("\n해결 방안 후보 (오케스트레이터 확인):")
    print("  A. 실제 브라우저(Playwright·Selenium) + JS 쿠키 해결")
    print("  B. 다른 IP/VPN 환경에서 수집")
    print("  C. Playwright cf_clearance 쿠키 추출 후 재사용")
    print("  D. ncleg.gov 공식 API 키 발급 신청")


def enum():
    """챕터 식별자 열거 → _enum_chapters.txt.

    probe() 결과 접근 가능 환경에서 실행해야 합니다.
    현재 환경(Cloudflare WAF 차단) = BLOCKED 상태로 실행 불가.
    """
    os.makedirs(RAW_DIR, exist_ok=True)

    # DNS 시도
    ip = _resolve_ip() or BASE_IP_PRIMARY

    # 색인 페이지 열거
    seen: set[str] = set()
    ok = False
    for attempt in range(5):
        try:
            code, body = http_get(STAT_INDEX_URL, resolve_ip=ip, timeout=30)
            if code == 200 and body:
                ok = True
                break
            if code == 403:
                txt = body.decode("utf-8", "ignore")
                if "Cloudflare" in txt or "Attention Required" in txt:
                    print(f"[enum] Cloudflare WAF 403 — BLOCKED. probe()를 먼저 실행하세요.")
                    _write_block_log("enum() Cloudflare WAF 403")
                    return
            if code == 429:
                time.sleep(30.0 * (attempt + 1))
        except Exception as e:
            print(f"[enum] 시도 {attempt+1}/5 오류: {type(e).__name__}: {e}")
            time.sleep(10.0 * (attempt + 1))

    if not ok:
        print("[enum] 색인 페이지 접근 실패. BLOCKED 상태 확인 필요.")
        return

    txt = body.decode("utf-8", "ignore")
    chaps = set(CHAP_RE.findall(txt))
    if not chaps:
        print("[enum] 챕터 식별자 0건 — 페이지 구조 변경 가능성. HTML 확인 필요.")
        return

    # 정렬: 숫자 기본 정렬 (1A, 2, 10B 등 혼합)
    def sort_key(c):
        m = re.match(r'^([0-9]+)([A-Z]*)$', c)
        return (int(m.group(1)), m.group(2)) if m else (0, c)

    sorted_chaps = sorted(chaps, key=sort_key)
    with open(ENUM_FILE, "w") as f:
        for c in sorted_chaps:
            f.write(c + "\n")
    print(f"[OK] 열거 정본 저장: {ENUM_FILE} ({len(sorted_chaps)}건)")
    print(f"샘플(앞 5): {sorted_chaps[:5]}")


def collect(smoke: int = SMOKE):
    """_enum_chapters.txt 순회 → PDF 저장.

    smoke > 0 이면 smoke건 수집 후 중단 (시험 수집용).
    호스트당 동시요청 = 1 (단일 워커 직렬 고정).
    429/오류 시 지수 백오프 30초+.
    """
    if not os.path.exists(ENUM_FILE):
        print(f"[collect] 열거 정본 없음: {ENUM_FILE} (먼저 --enum)")
        return

    with open(ENUM_FILE) as f:
        chapters = [ln.strip() for ln in f if ln.strip()]

    label = f"SMOKE={smoke}" if smoke else "전수"
    if smoke:
        chapters = chapters[:smoke]
        print(f"[collect] {label} 수집 시작 ({len(chapters)}건)", flush=True)
    else:
        print(f"[collect] {label} ({len(chapters)}건) 수집 시작", flush=True)

    os.makedirs(RAW_DIR, exist_ok=True)
    ip = _resolve_ip() or BASE_IP_PRIMARY
    ok = miss = skip = 0

    for i, chap in enumerate(chapters, 1):
        fname = f"Chapter{chap}.pdf"
        path  = os.path.join(RAW_DIR, fname)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue
        url = BASE + PDF_PATH_TMPL.format(chapter=chap)
        if fetch_to_file_retry(url, path, resolve_ip=ip, backoff=30.0, max_retry=3):
            ok += 1
        else:
            miss += 1
        if i % 20 == 0:
            print(f"  진행 {i}/{len(chapters)} ok={ok} skip={skip} miss={miss}", flush=True)
        time.sleep(DELAY)

    print(f"[collect] 총={len(chapters)} ok={ok} skip={skip} miss={miss}")
    if smoke:
        print(f"[SMOKE 완료] 전수 수집은 SMOKE 환경변수 없이 --collect 재실행")


def verify():
    """4지표 = 모수·부재율·계층고아·식별자중복."""
    if not os.path.exists(ENUM_FILE):
        print(f"[verify] 열거 정본 없음: {ENUM_FILE}")
        return

    with open(ENUM_FILE) as f:
        enum_chaps = [ln.strip() for ln in f if ln.strip()]
    enum_set = set(enum_chaps)
    dup = len(enum_chaps) - len(enum_set)

    # 본문 파일 = Chapter{N}.pdf (진단 _접두 제외)
    body_chaps: set[str] = set()
    if os.path.isdir(RAW_DIR):
        for n in os.listdir(RAW_DIR):
            m = re.match(r'^Chapter([0-9]+[A-Z]*)\.pdf$', n, re.IGNORECASE)
            if m:
                body_chaps.add(m.group(1))

    absent = enum_set - body_chaps
    orphan = body_chaps - enum_set
    rate   = (len(absent) / len(enum_set) * 100) if enum_set else 0.0

    print("=== NC STATUTE 검증 4지표 ===")
    print(f"모수(distinct 챕터) = {len(enum_set)}")
    print(f"PDF 저장 파일 수    = {len(body_chaps)}")
    print(f"부재(열거O PDF X)   = {len(absent)} ({rate:.4f}%)")
    print(f"계층 고아(PDF O 열거X) = {len(orphan)}")
    print(f"식별자 중복          = {dup}")
    ok_flag = rate < 1.0 and len(orphan) == 0 and dup == 0
    print(f"판정 = {'PASS' if ok_flag else 'FAIL'}")

    if os.path.exists(BLOCK_LOG):
        print(f"\n[주의] BLOCKED 로그 존재: {BLOCK_LOG}")
        print("  → ncleg.gov 접근 차단 상태에서 수집된 결과입니다.")


# ─────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--probe"
    if mode == "--probe":
        probe()
    elif mode == "--enum":
        enum()
    elif mode == "--collect":
        smoke_n = int(os.environ.get("SMOKE", "0"))
        collect(smoke=smoke_n)
    elif mode == "--verify":
        verify()
    else:
        print(f"미구현 모드: {mode}")
        print("사용법: --probe | --enum | --collect | --verify")
        print("시험수집: SMOKE=30 python3 dev_us_nc_statute_collect.py --collect")
