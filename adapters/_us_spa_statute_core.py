#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""US 주법전 SPA(JavaScript 렌더) 공통 코어 — Playwright 표준 골격 2026-06-13.

대상 = 정적 fetch로 섹션 목록이 안 나오는 진짜 SPA 주.
  실측 분류(인박스 04:30·04:50) = in(iga.in.gov React CRA body691B)·sd(Vue)·
  al(Next.js)·or(SharePoint)·ok(ASP.NET postback). 정적 코어 0파싱 확정분.

★ 계명1 (추정 셀렉터 금지) = 정적 코어와 동일 철학.
  --diag 가 렌더된 DOM 의 href 를 전량 덤프 → 그 실구조로 link_re 를 보정한 뒤
  --enum/--collect. CONFIG 에 link_re 없으면 diag 만 동작(enum 은 hard-fail).
  추정 셀렉터로 enum/collect 선발진 절대 금지.

★ 실행 환경 = GHA(미국 IP) headless chromium 전용. 로컬(WSL) Playwright 설치·실행 절대 금지(OOM).
  playwright import 는 모드 함수 내부 = 로컬 py_compile(import 미실행) 통과용.

모드:
  --diag    : index_url 을 렌더 → <a href> 전량 + link_re 매칭 수 덤프(셀렉터 보정 근거)
  --netcap  : 렌더 중 자동 XHR/fetch 응답 URL 전량 캡처 → statute API 엔드포인트 데이터 발굴
              (추정 URL 금지·공개 API 만·발굴 실제 URL 로만 enum 보정. 6주 공통 표준)
  --enum    : 렌더 후 link_re 로 섹션 URL 추출 → _enum_laws.txt (link_re 필수)
  --collect : _enum_laws.txt 순회 → 각 섹션 렌더 후 HTML 저장 (SMOKE=N 지원)
  --verify  : 정적 코어와 동형 4지표(모수·저장·부재·고아·중복) — 네트워크 불요

CONFIG 키:
  state·base·index_url·ext(.html) + link_re(선택·diag후 보정)
  wait_until(기본 networkidle)·nav_timeout_ms(기본 60000)
환경변수:
  RAW_DIR·SMOKE·SPA_DELAY(초·기본 0.5)
"""
import os
import re
import ssl
import sys
import time
import urllib.request
from urllib.parse import urljoin, urlparse

EXT_DEFAULT = ".html"
SPA_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
# 제네릭 섹션 링크 패턴 [추정] — CONFIG link_re 없으면 diag 참고용. enum 은 CONFIG link_re 필수.
DEFAULT_LINK_RE = re.compile(
    r"(?:section|chapter|title|statute|article|/\d+-\d+|/ic/\d+)", re.I
)


def _paths(cfg):
    state = cfg["state"]
    raw = os.environ.get(
        "RAW_DIR", f"/mnt/wsl/usdata/xsoft_data/raw/us-{state}/statute"
    )
    return raw, os.path.join(raw, "_enum_laws.txt")


def _render(cfg, url):
    """playwright headless chromium 으로 url 렌더 후 (status, html, hrefs) 반환."""
    from playwright.sync_api import sync_playwright  # 로컬 import 회피(GHA 전용)

    wait = cfg.get("wait_until", "networkidle")
    nav_to = int(cfg.get("nav_timeout_ms", 60000))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=SPA_UA)
            resp = page.goto(url, wait_until=wait, timeout=nav_to)
            status = resp.status if resp else 0
            html = page.content()
            hrefs = page.eval_on_selector_all(
                "a[href]", "els => els.map(e => e.getAttribute('href'))"
            )
        finally:
            browser.close()
    hrefs = [h for h in hrefs if h]
    return status, html, hrefs


def _abs_links(base, index_url, hrefs, link_re):
    out = []
    seen = set()
    for h in hrefs:
        if not link_re.search(h):
            continue
        u = urljoin(index_url, h) if not h.startswith("http") else h
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def diag(cfg):
    base, index_url = cfg["base"], cfg["index_url"]
    print(f"=== {cfg['state'].upper()} 법전 SPA DIAG (Playwright) {base} ===")
    try:
        status, html, hrefs = _render(cfg, index_url)
    except Exception as e:
        print(f"[FATAL] SPA 렌더 실패: {type(e).__name__}: {e}")
        print(f"[FATAL] INDEX_URL={index_url} GHA 로그로 wait_until/timeout 보정 필요.")
        sys.exit(1)
    print(f"[DIAG index] {index_url} status={status} body_len={len(html)}")
    cur = cfg.get("link_re", DEFAULT_LINK_RE)
    matched = _abs_links(base, index_url, hrefs, cur)
    nums = sorted({h for h in hrefs if re.search(r"\d", h)})
    print(f"[DIAG] 렌더 후 전체href={len(hrefs)} 숫자포함distinct={len(nums)} link_re매칭={len(matched)}")
    # 디렉터리 prefix 분포 = 셀렉터 보정 근거(어느 경로가 본문 트리인지 관찰·추정 아님).
    prefix = {}
    for h in nums:
        p = re.sub(r"[^/]*$", "", urlparse(h).path)  # 마지막 파일명 제거 = 디렉터리
        prefix[p] = prefix.get(p, 0) + 1
    print("[DIAG prefix] (디렉터리별 숫자href 수, 상위 25):")
    for p, c in sorted(prefix.items(), key=lambda x: -x[1])[:25]:
        print(f"  {c:5d}  {p}")
    print(f"[DIAG hrefs] 샘플{min(80, len(nums))}:")
    for h in nums[:80]:
        print(f"  HREF {h}")


def enum(cfg):
    raw, enum_file = _paths(cfg)
    os.makedirs(raw, exist_ok=True)
    base, index_url = cfg["base"], cfg["index_url"]
    if "link_re" not in cfg:
        print("[FATAL enum] CONFIG link_re 없음 → diag 로 실구조 측정·보정 선행(추정 금지·계명1)")
        sys.exit(1)
    status, html, hrefs = _render(cfg, index_url)
    link_re = cfg["link_re"]
    urls = _abs_links(base, index_url, hrefs, link_re)
    if not urls:
        print(f"[FATAL enum] link_re 매칭 0건(status={status} href={len(hrefs)}) → 셀렉터 재보정")
        sys.exit(1)
    with open(enum_file, "w") as f:
        for u in urls:
            f.write(u + "\n")
    print(f"[OK] 열거 정본 저장: {enum_file} ({len(urls)}건)")


def _fname(url, ext):
    safe = re.sub(r"[^0-9A-Za-z._-]", "_", url.split("//", 1)[-1])
    return safe[-180:] + ext


_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _collect_http(cfg, raw, urls, ext, delay, smoke):
    # JSON/정적 API 응답을 Playwright 없이 직접 GET(렌더 불요). enum URL 은 netcap 발굴 정본.
    ok = miss = skip = 0
    for i, url in enumerate(urls, 1):
        path = os.path.join(raw, _fname(url, ext))
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": SPA_UA, "Accept": "application/json,*/*"}
            )
            with urllib.request.urlopen(req, timeout=120, context=_CTX) as r:
                data = r.read()
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
            ok += 1
        except Exception as e:
            print(f"  [miss] {url} ({type(e).__name__})")
            miss += 1
        if i % 25 == 0:
            print(f"  진행 {i}/{len(urls)} ok={ok} skip={skip} miss={miss}", flush=True)
        if smoke and ok >= smoke:
            print(f"  [SMOKE] {smoke}건 후 중단")
            break
        time.sleep(delay)
    print(f"[collect {cfg['state']}] 총={len(urls)} ok={ok} skip={skip} miss={miss}")


def collect(cfg):
    raw, enum_file = _paths(cfg)
    if not os.path.exists(enum_file):
        print(f"열거 정본 없음: {enum_file} (먼저 --enum/--netcap)")
        sys.exit(1)
    with open(enum_file) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    ext = cfg.get("ext", EXT_DEFAULT)
    delay = float(os.environ.get("SPA_DELAY", "0.5"))
    _sv = os.environ.get("SMOKE", "0").strip().lower()
    smoke = 5 if _sv in ("true", "yes") else (int(_sv) if _sv.isdigit() else 0)
    if cfg.get("http_json"):
        return _collect_http(cfg, raw, urls, ext, delay, smoke)
    ok = miss = skip = 0
    for i, url in enumerate(urls, 1):
        path = os.path.join(raw, _fname(url, ext))
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue
        try:
            _, html, _ = _render(cfg, url)
            tmp = path + ".part"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(html)
            os.replace(tmp, path)
            ok += 1
        except Exception as e:
            print(f"  [miss] {url} ({type(e).__name__})")
            miss += 1
        if i % 25 == 0:
            print(f"  진행 {i}/{len(urls)} ok={ok} skip={skip} miss={miss}", flush=True)
        if smoke and ok >= smoke:
            print(f"  [SMOKE] {smoke}건 후 중단")
            break
        time.sleep(delay)
    print(f"[collect {cfg['state']}] 총={len(urls)} ok={ok} skip={skip} miss={miss}")


def verify(cfg):
    raw, enum_file = _paths(cfg)
    ext = cfg.get("ext", EXT_DEFAULT)
    if not os.path.exists(enum_file):
        print(f"열거 정본 없음: {enum_file}")
        sys.exit(1)
    with open(enum_file) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    enum_set = set(urls)
    dup = len(urls) - len(enum_set)
    enum_fnames = {_fname(u, ext) for u in enum_set}
    body = {
        n for n in os.listdir(raw)
        if n.endswith(ext) and not n.startswith("_") and not n.endswith(".part")
    }
    absent = enum_fnames - body
    orphan = body - enum_fnames
    rate = (len(absent) / len(enum_fnames) * 100) if enum_fnames else 0.0
    print(f"=== {cfg['state'].upper()} STATUTE(SPA) 검증 4지표 ===")
    print(f"모수(섹션 URL) = {len(enum_set)}")
    print(f"저장 파일 수 = {len(body)}")
    print(f"부재 = {len(absent)} ({rate:.4f}%)")
    print(f"계층 고아 = {len(orphan)}")
    print(f"식별자 중복 = {dup}")
    ok = rate < 1.0 and len(orphan) == 0 and dup == 0
    print(f"판정 = {'PASS' if ok else 'FAIL'}")


def netcap(cfg):
    """index_url 렌더 중 자동 발생한 XHR/fetch 응답 URL 을 전량 캡처(추정 아님·관찰).
    statute 목록 API 엔드포인트를 데이터로 노출 → 그 실제 URL 로만 link_re/index_url 보정.
    공개 API 만·robots/ToS 준수·로그인/CAPTCHA 우회 안 함. 클릭 없는 초기 로드 XHR 한정."""
    base, index_url = cfg["base"], cfg["index_url"]
    print(f"=== {cfg['state'].upper()} 법전 SPA NETCAP (Playwright XHR/fetch URL 캡처) {base} ===")
    print("[NETCAP] 공개 API 만·robots/ToS 준수·로그인/CAPTCHA 우회 안 함·추정 URL 금지")
    from playwright.sync_api import sync_playwright  # 로컬 import 회피(GHA 전용)

    wait = cfg.get("wait_until", "networkidle")
    nav_to = int(cfg.get("nav_timeout_ms", 60000))
    settle = int(cfg.get("netcap_settle_ms", 4000))
    caps = []

    def on_resp(resp):
        try:
            rt = resp.request.resource_type
            if rt in ("xhr", "fetch"):
                # post_data = POST 바디 관찰(graphql 등 쿼리 바디가 열거 정본인 경우·추정 아님)
                try:
                    pd = resp.request.post_data
                except Exception:
                    pd = None
                caps.append((resp.status, rt, resp.headers.get("content-type", ""), resp.url, pd))
        except Exception:
            pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=SPA_UA)
                page.on("response", on_resp)
                try:
                    page.goto(index_url, wait_until=wait, timeout=nav_to)
                except Exception as e:
                    print(f"[NETCAP goto warn] {type(e).__name__}: {e}")
                page.wait_for_timeout(settle)
            finally:
                browser.close()
    except Exception as e:
        print(f"[FATAL netcap] {type(e).__name__}: {e}")
        sys.exit(1)

    seen, rows = set(), []
    for status, rt, ct, url, pd in caps:
        key = (url, pd)
        if key in seen:
            continue
        seen.add(key)
        rows.append((status, rt, ct, url, pd))
    data_rows = [r for r in rows if any(k in r[2].lower() for k in ("json", "xml"))]
    print(f"[NETCAP] XHR/fetch distinct 응답 {len(rows)}건 (json/xml {len(data_rows)}건)")
    print("[NETCAP data 후보(json/xml)] =====")
    for status, rt, ct, url, pd in data_rows:
        print(f"  [{status} {rt} {ct}] {url[:220]}")
        if pd:
            print(f"    [POST body] {pd[:600]}")
    print("[NETCAP 전체 XHR/fetch] =====")
    for status, rt, ct, url, pd in rows:
        print(f"  [{status} {rt} {ct}] {url[:220]}")
    if not rows:
        print("[NETCAP] 초기 로드 XHR/fetch 0건 = 클릭/상호작용 유발 필요(추정 클릭 금지·재보고)")
    # api_re = netcap 으로 잡힌 실제 응답 URL 중 statute API 패턴(관찰·추정 아님)을 enum 정본 저장.
    api_re = cfg.get("api_re")
    if api_re:
        raw, enum_file = _paths(cfg)
        os.makedirs(raw, exist_ok=True)
        api_urls = [u for (_, _, _, u, _) in rows if api_re.search(u)]
        # enum_sub = (정규식, 치환) = 관찰된 목록 URL을 측정으로 확인된 전문 URL 패턴으로 변환.
        #   예: in = 목차 .json 36건 enum → 확인된 .html(전문) 36건으로 치환(추정 아님·둘 다 측정).
        sub = cfg.get("enum_sub")
        if sub:
            api_urls = sorted({re.sub(sub[0], sub[1], u) for u in api_urls})
            print(f"[NETCAP enum] enum_sub 변환 적용 {sub[0]} → {sub[1]}")
        if api_urls:
            with open(enum_file, "w") as f:
                for u in api_urls:
                    f.write(u + "\n")
            print(f"[NETCAP enum] api_re 매칭 {len(api_urls)}건 → {enum_file} 저장")
        else:
            print("[NETCAP enum] api_re 매칭 0건 = enum 미저장(셀렉터 재측정·추정 금지)")
    sys.exit(0)


def run(cfg):
    mode = sys.argv[1] if len(sys.argv) > 1 else "--diag"
    {
        "--diag": diag, "--probe": diag, "--enum": enum,
        "--collect": collect, "--verify": verify, "--netcap": netcap,
    }.get(mode, lambda c: print(f"미구현 모드: {mode}"))(cfg)
