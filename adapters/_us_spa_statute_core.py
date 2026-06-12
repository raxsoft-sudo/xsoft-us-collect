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
import sys
import time
from urllib.parse import urljoin

EXT_DEFAULT = ".html"
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
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                )
            )
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
    print(f"[DIAG hrefs] 샘플{min(20, len(nums))}:")
    for h in nums[:20]:
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


def collect(cfg):
    raw, enum_file = _paths(cfg)
    if not os.path.exists(enum_file):
        print(f"열거 정본 없음: {enum_file} (먼저 --enum)")
        sys.exit(1)
    with open(enum_file) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    ext = cfg.get("ext", EXT_DEFAULT)
    delay = float(os.environ.get("SPA_DELAY", "0.5"))
    smoke = int(os.environ.get("SMOKE", "0"))
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


def run(cfg):
    mode = sys.argv[1] if len(sys.argv) > 1 else "--diag"
    {
        "--diag": diag, "--probe": diag, "--enum": enum,
        "--collect": collect, "--verify": verify,
    }.get(mode, lambda c: print(f"미구현 모드: {mode}"))(cfg)
