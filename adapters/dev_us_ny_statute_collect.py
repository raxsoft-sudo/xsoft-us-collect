#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NY 법전 (OpenLeg API v3 + 폴백 HTML) 수집기.

어댑터 유형 = API 우선 · HTML 폴백 (지오블록 · GHA 실행 필요).
  1순위: OpenLeg API v3
    목록  = GET https://legislation.nysenate.gov/api/3/laws?key=$NY_OPENLEG_KEY
    상세  = GET https://legislation.nysenate.gov/api/3/laws/{lawId}?full=true&key=$NY_OPENLEG_KEY
    저장  = RAW_DIR/<lawId>.json
  2순위: HTML 스크레이프 (키 없거나 401/403)
    URL   = https://www.nysenate.gov/legislation/laws/{lawId}
    저장  = RAW_DIR/<lawId>.html
  모두 막히면: 비0 exit + "NY_BLOCKED" 로그

키: os.environ["NY_OPENLEG_KEY"] (코드 하드코딩 절대 금지)

모드:
  --probe   : API 또는 HTML 접속 가능 여부 확인 로그
  --enum    : lawId 목록 열거 → _enum_laws.txt
  --collect : _enum_laws.txt 순회 → JSON/HTML 저장
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
import urllib.parse

API_BASE = "https://legislation.nysenate.gov/api/3"
HTML_BASE = "https://www.nysenate.gov/legislation/laws"
RAW_DIR = os.environ.get("RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-ny/statute")
ENUM_FILE = os.path.join(RAW_DIR, "_enum_laws.txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
DELAY = float(os.environ.get("NY_DELAY", "0.5"))
SMOKE = int(os.environ.get("SMOKE", "0"))
API_KEY = os.environ.get("NY_OPENLEG_KEY", "")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

LAW_ID_RE = re.compile(r'/legislation/laws/([A-Z0-9]+)', re.IGNORECASE)
LEGINFO_BASE = "https://public.leginfo.state.ny.us"  # 2순위 무키 LRS (lawssrch.cgi)


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def http_get(url, timeout=30, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
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
            if e.code in (401, 403):
                print(f"[AUTH] {e.code} {url}")
                return None  # 인증 실패 구분
            return False
        except Exception as ex:
            print(f"[ERR attempt={attempt}] {type(ex).__name__}: {ex}")
            time.sleep(wait)
            wait *= 2
    return False


def api_available():
    """API 키 존재 + 응답 200 확인."""
    if not API_KEY:
        return False
    url = f"{API_BASE}/laws?key={API_KEY}&limit=1"
    try:
        code, _ = http_get(url)
        return code == 200
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(f"[API] 인증 실패 {e.code} — HTML 폴백 전환")
        return False
    except Exception:
        return False


def get_law_ids_api():
    """API → lawId 목록 반환."""
    law_ids = []
    offset = 0
    limit = 100
    while True:
        url = f"{API_BASE}/laws?key={API_KEY}&limit={limit}&offset={offset}"
        try:
            code, body = http_get(url)
            if code != 200:
                break
            data = json.loads(body.decode("utf-8", "ignore"))
            items = data.get("result", {}).get("items", [])
            if not items:
                break
            for item in items:
                law_id = item.get("lawId") or item.get("lawid") or item.get("id")
                if law_id and law_id not in set(law_ids):
                    law_ids.append(law_id)
            total = data.get("result", {}).get("total", 0)
            offset += limit
            if offset >= total or not items:
                break
        except Exception as e:
            print(f"[API list ERR] {type(e).__name__}: {e}")
            break
        time.sleep(DELAY)
        if SMOKE > 0 and len(law_ids) >= SMOKE:
            return law_ids[:SMOKE]
    return law_ids


def get_law_ids_html():
    """HTML 메인 페이지 → lawId 링크 파싱."""
    url = "https://www.nysenate.gov/legislation/laws"
    try:
        code, body = http_get(url)
        text = body.decode("utf-8", "ignore")
        ids = list(dict.fromkeys(m.group(1).upper() for m in LAW_ID_RE.finditer(text)))
        return ids
    except Exception as e:
        print(f"[HTML list ERR] {type(e).__name__}: {e}")
        return []


def probe():
    print("=== NY 법전 probe (OpenLeg API v3 + HTML 폴백) ===")
    os.makedirs(RAW_DIR, exist_ok=True)
    if API_KEY:
        print(f"[API] 키 존재 (앞4자 = {API_KEY[:4]}****)")
        ok = api_available()
        print(f"[API] 접속 가능 = {ok}")
        if ok:
            # 법령 목록 샘플
            url = f"{API_BASE}/laws?key={API_KEY}&limit=5"
            try:
                code, body = http_get(url)
                data = json.loads(body.decode("utf-8", "ignore"))
                items = data.get("result", {}).get("items", [])
                print(f"[API] 법령 샘플: {[i.get('lawId') or i.get('id') for i in items]}")
            except Exception as e:
                print(f"[API] {type(e).__name__}: {e}")
    else:
        print("[API] NY_OPENLEG_KEY 없음 — HTML 폴백 전환")
        url = "https://www.nysenate.gov/legislation/laws"
        try:
            code, body = http_get(url)
            print(f"[HTML] status={code} body_len={len(body)}")
            ids = list(dict.fromkeys(m.group(1).upper() for m in LAW_ID_RE.finditer(body.decode("utf-8","ignore"))))
            print(f"[HTML] lawId 후보 샘플: {ids[:10]}")
        except Exception as e:
            print(f"[HTML] ERR {type(e).__name__}: {e}")
            print("NY_BLOCKED: 두 경로 모두 막힘")
    print("주의: 지오블록 가능. GHA 미국 IP 실행 필요.")


def enum():
    """API 또는 HTML → lawId 열거 → _enum_laws.txt."""
    os.makedirs(RAW_DIR, exist_ok=True)
    if api_available():
        print("[enum] API 경로 사용")
        law_ids = get_law_ids_api()
    else:
        print("[enum] HTML 폴백 경로 사용")
        law_ids = get_law_ids_html()

    if not law_ids:
        print("[ERR] lawId 열거 실패 — NY_BLOCKED 가능")
        sys.exit(1)

    if SMOKE > 0:
        law_ids = law_ids[:SMOKE]
    with open(ENUM_FILE, "w") as f:
        for lid in law_ids:
            f.write(lid + "\n")
    print(f"[OK] 열거 정본 저장: {ENUM_FILE} ({len(law_ids)}건)")


def collect():
    """_enum_laws.txt lawId 순회 → JSON(API) 또는 HTML(폴백) 저장."""
    if not os.path.exists(ENUM_FILE):
        print(f"열거 정본 없음: {ENUM_FILE} (먼저 --enum)")
        sys.exit(1)
    with open(ENUM_FILE) as f:
        ids = [ln.strip() for ln in f if ln.strip()]
    os.makedirs(RAW_DIR, exist_ok=True)
    use_api = api_available()
    ok = miss = skip = 0
    for i, law_id in enumerate(ids, 1):
        if use_api:
            url = f"{API_BASE}/laws/{law_id}?full=true&key={API_KEY}"
            path = os.path.join(RAW_DIR, f"{law_id}.json")
        else:
            url = f"{HTML_BASE}/{law_id}"
            path = os.path.join(RAW_DIR, f"{law_id}.html")

        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue

        result = fetch_to_file_retry(url, path)
        if result is None:
            # 인증 실패 → HTML 폴백
            use_api = False
            url2 = f"{HTML_BASE}/{law_id}"
            path2 = os.path.join(RAW_DIR, f"{law_id}.html")
            if fetch_to_file_retry(url2, path2):
                ok += 1
            else:
                print("NY_BLOCKED: API 인증 실패 + HTML 접근 불가")
                miss += 1
        elif result:
            ok += 1
        else:
            miss += 1

        if i % 50 == 0:
            print(f"  진행 {i}/{len(ids)} ok={ok} skip={skip} miss={miss}", flush=True)
        time.sleep(DELAY)

    print(f"[collect] 총={len(ids)} ok={ok} skip={skip} miss={miss}")
    if ok == 0 and miss > 0:
        print("NY_BLOCKED: 모든 요청 실패")
        sys.exit(1)


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
        if (n.endswith(".json") or n.endswith(".html")) and not n.startswith("_"):
            body_ids.add(n.rsplit(".", 1)[0])
    absent = enum_set - body_ids
    orphan = body_ids - enum_set
    rate = (len(absent) / len(enum_set) * 100) if enum_set else 0.0
    print("=== NY STATUTE 검증 4지표 ===")
    print(f"모수(lawId) = {len(enum_set)}")
    print(f"저장 파일 수 = {len(body_ids)}")
    print(f"부재 = {len(absent)} ({rate:.4f}%)")
    print(f"계층 고아 = {len(orphan)}")
    print(f"식별자 중복 = {dup}")
    ok = rate < 1.0 and len(orphan) == 0 and dup == 0
    print(f"판정 = {'PASS' if ok else 'FAIL'}")


def _dump(label, url, extra_res=None, timeout=30):
    """무키 경로 진단용 = status·body_len·head·href 덤프 (완전 브라우저 헤더)."""
    try:
        code, body = http_get(url, timeout=timeout, headers=BROWSER_HEADERS)
        text = body.decode("utf-8", "ignore")
        print(f"[{label}] {url} status={code} body_len={len(body)}")
        print(f"[{label}] head1200={text[:1200]!r}")
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', text, re.IGNORECASE)
        print(f"[{label}] href수={len(hrefs)} 샘플30={hrefs[:30]}")
        forms = re.findall(r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>', text, re.IGNORECASE)
        print(f"[{label}] form action={forms[:6]}")
        if extra_res:
            for pat in extra_res:
                hits = re.findall(pat, text, re.IGNORECASE)
                print(f"[{label}] re({pat})={len(hits)} 샘플10={hits[:10]}")
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")


def diag():
    """무키 NY 경로 종합 진단 = API 무키코드 + leginfo LRS 구조 + nysenate HTML (추정 발진 금지·실데이터 확인)."""
    print("=== NY 법전 DIAG (무키 경로 규명) ===")
    print(f"[API_KEY] 존재={'Y' if API_KEY else 'N'}")
    # 1) API 무키 호출 = 401이면 키 필수 / 200이면 무키 가능
    try:
        code, body = http_get(f"{API_BASE}/laws?limit=1")
        print(f"[API nokey] status={code} body_len={len(body)} head300={body[:300]!r}")
    except urllib.error.HTTPError as e:
        print(f"[API nokey] HTTPError {e.code} = {'키필수' if e.code in (401,403) else e.reason}")
    except Exception as e:
        print(f"[API nokey] ERR {type(e).__name__}: {e}")
    # 2) leginfo LRS (2순위 무키) = http + 긴 타임아웃(서버 느림 대응)
    _dump("LEGINFO http menugetf", "http://public.leginfo.state.ny.us/menugetf.cgi?COMMONQUERY=LAWS", timeout=60)
    _dump("LEGINFO http navigate", "http://public.leginfo.state.ny.us/navigate.cgi", timeout=60)
    # 3) leginfo 메뉴 JS 자산 = 법령 목록·네비 명령 구조 규명 (CSVARRAY = 법령배열 추정)
    _dump("LEGINFO csvarray", "http://public.leginfo.state.ny.us/STATDOC/CSVARRAY.js", [r'"([A-Z]{2,4})"', r"'([A-Z]{2,4})'"], timeout=60)
    _dump("LEGINFO navjs", "http://public.leginfo.state.ny.us/statdoc/NVMUJ04P.js", timeout=60)
    _dump("LEGINFO lawssrch http", "http://public.leginfo.state.ny.us/lawssrch.cgi", timeout=60)
    # 4) ★ 결정적 시험 = 사이트 JS(getlawCMA) 그대로 POST → 법령 본문 회수 여부 (쿠키 세션 포함)
    try:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj),
            urllib.request.HTTPSHandler(context=CTX),
        )
        opener.addheaders = list(BROWSER_HEADERS.items())
        # 세션 establish
        opener.open("http://public.leginfo.state.ny.us/navigate.cgi", timeout=60).read()
        print(f"[POST test] 쿠키수={len(cj)}")
        action = "http://public.leginfo.state.ny.us/lawssrch.cgi?NVLWO:+&QLAWDATA=**CMA+&SEATYPE=AQUA+&LIST=LAW"
        data = urllib.parse.urlencode({"hwebpage": "LAWS"}).encode()
        r = opener.open(urllib.request.Request(action, data=data), timeout=60)
        rb = r.read()
        rtext = rb.decode("utf-8", "ignore")
        print(f"[POST test CMA] status={r.getcode()} body_len={len(rb)}")
        # ★ 열거원 추출 = 응답 메뉴에 박힌 전체 법령 LAWID·SEATYPE
        qlaw = sorted(set(re.findall(r'QLAWDATA=\*\*([A-Z0-9]+)', rtext)))
        seat = sorted(set(re.findall(r'SEATYPE=([A-Z0-9]+)', rtext)))
        getl = sorted(set(re.findall(r'getlaw([A-Z0-9]+)\s*\(', rtext)))
        pairs = sorted(set(re.findall(r'QLAWDATA=\*\*([A-Z0-9]+)\+&SEATYPE=([A-Z0-9]+)', rtext)))
        print(f"[POST test CMA] QLAWDATA distinct={len(qlaw)} 샘플40={qlaw[:40]}")
        print(f"[POST test CMA] SEATYPE distinct={len(seat)} = {seat}")
        print(f"[POST test CMA] getlaw fn={len(getl)} 샘플40={getl[:40]}")
        print(f"[POST test CMA] (LAWID,SEATYPE)쌍={len(pairs)} 샘플20={pairs[:20]}")
        # 본문 단위 추출 가능성 = 섹션 마커
        secs = re.findall(r'(?:&sect;|SECTION|§)\s*([0-9]+[0-9a-z\-\.]*)', rtext)
        print(f"[POST test CMA] 섹션마커 추정={len(secs)} 샘플10={secs[:10]}")
        # ★ 실제 링크 형식 규명 = head + 모든 href + onclick + 모든 getlaw(...) 인자
        print(f"[POST test CMA] head3000={rtext[:3000]!r}")
        hrefs = re.findall(r'href=["\']?([^"\'>\s]+)', rtext, re.IGNORECASE)
        print(f"[POST test CMA] href수={len(hrefs)} 샘플40={hrefs[:40]}")
        oncl = re.findall(r'onclick=["\']([^"\']+)["\']', rtext, re.IGNORECASE)
        print(f"[POST test CMA] onclick수={len(oncl)} 샘플20={oncl[:20]}")
        gl_args = re.findall(r"getlaw\s*\(([^)]*)\)", rtext)
        print(f"[POST test CMA] getlaw인자수={len(gl_args)} 샘플20={gl_args[:20]}")
        # 모든 ** 데이터 토큰 (QLAWDATA prefix 없이도)
        stars = sorted(set(re.findall(r"\*\*([A-Z0-9]{2,})", rtext)))
        print(f"[POST test CMA] **토큰distinct={len(stars)} 샘플60={stars[:60]}")
        # ★ 법령 목록 본문부 (네비 이후) + submitForm 인자 전수
        print(f"[POST test CMA] body3000_12000={rtext[3000:12000]!r}")
        sf = re.findall(r"submitForm\(([^)]*)\)", rtext)
        print(f"[POST test CMA] submitForm수={len(sf)} 샘플40={sf[:40]}")
        # CSVARRAY.js = 법령 배열 후보
        try:
            cc, cb = http_get("http://public.leginfo.state.ny.us/STATDOC/CSVARRAY.js", timeout=60, headers=BROWSER_HEADERS)
            ct = cb.decode("utf-8", "ignore")
            print(f"[CSVARRAY] status={cc} body_len={len(cb)} head2500={ct[:2500]!r}")
        except Exception as e:
            print(f"[CSVARRAY] ERR {type(e).__name__}: {e}")
        # ★★ 법령 인덱스(전체 lawID 열거원) = "Laws of New York" 메뉴 = submitForm("NVLWO","NVSTO")
        # submitForm 정의 = 매 페이지 로드되는 NMCOM57P.js·NVMUJ04P.js 후보 전수 규명
        for jsf in ["NMCOM57P.js", "NVMUJ04P.js", "CFUN07P.js"]:
            try:
                jc, jb = http_get(f"http://public.leginfo.state.ny.us/statdoc/{jsf}", timeout=60, headers=BROWSER_HEADERS)
                jt = jb.decode("utf-8", "ignore")
                mfn = re.search(r"function submitForm\b.{0,900}?\n\}", jt, re.DOTALL)
                print(f"[{jsf}] len={len(jt)} submitForm={'O' if mfn else 'X'}")
                if mfn:
                    print(f"[{jsf} submitForm]={mfn.group(0)[:900]!r}")
            except Exception as e:
                print(f"[{jsf}] ERR {type(e).__name__}: {e}")
        # 법령 인덱스 직접 요청 후보 4종
        for label, act, body in [
            ("idx navNVLWO", "http://public.leginfo.state.ny.us/navigate.cgi?NVLWO:", {"hwebpage": "NVLWO", "parm1": "NVSTO"}),
            ("idx lawNVSTO", "http://public.leginfo.state.ny.us/lawssrch.cgi?NVLWO:", {"hwebpage": "NVSTO"}),
            ("idx lawLIST", "http://public.leginfo.state.ny.us/lawssrch.cgi?NVLWO:+&LIST=LAW", {"hwebpage": "LAWS"}),
        ]:
            try:
                rr = opener.open(urllib.request.Request(act, data=urllib.parse.urlencode(body).encode()), timeout=60)
                bb = rr.read().decode("utf-8", "ignore")
                ids = sorted(set(re.findall(r"\*\*([A-Z0-9]{2,4})", bb)))
                sfa = re.findall(r"getlaw\s*\(([^)]{0,120})\)", bb)
                print(f"[{label}] status={rr.getcode()} len={len(bb)} **id수={len(ids)} 샘플60={ids[:60]}")
                print(f"[{label}] getlaw인자수={len(sfa)} 샘플20={sfa[:20]}")
                if len(ids) < 5 and len(sfa) < 5:
                    print(f"[{label}] body2000_9000={bb[2000:9000]!r}")
            except Exception as e:
                print(f"[{label}] ERR {type(e).__name__}: {e}")
    except Exception as e:
        print(f"[POST test CMA] ERR {type(e).__name__}: {e}")
    print("=== DIAG 끝 (로그로 무키 경로·열거·섹션 구조 판정) ===")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--probe"
    if mode == "--probe":
        probe()
    elif mode == "--diag":
        diag()
    elif mode == "--enum":
        enum()
    elif mode == "--collect":
        collect()
    elif mode == "--verify":
        verify()
    else:
        print(f"미구현 모드: {mode}")
