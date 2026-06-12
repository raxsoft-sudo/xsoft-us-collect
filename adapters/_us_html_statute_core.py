#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""④HTML파서 공용 코어 — 주별 설정(CONFIG)을 받아 index→링크→본문 수집.

설계 의도 = 본문 PD(public domain) 주의 statute HTML 트리를 GHA(미국 IP)에서 수집.
  WSL(한국 IP)에서는 전부 지오블록(000/403)이라 probe 불가 → 어댑터 = 스캐폴드.
  링크 패턴(LINK_RE 등)은 매트릭스 본표의 도메인만 [측정]이고, 셀렉터는 [추정] =
  반드시 GHA --probe 로그로 보정한 뒤 --collect 발진한다(OH 어댑터 선례).

주별 파일(dev_us_<주>_statute_collect.py)은 이 코어를 import 후 CONFIG dict로 run() 호출.

CONFIG 키:
  state      : 주 코드 (소문자)
  base       : 스킴+호스트 (예 https://malegislature.gov)
  index_url  : 법전 목차/진입 URL
  link_re    : 본문 섹션 링크 정규식 (group(1)=href) [추정·probe 보정]
  chapter_re : (선택) 챕터 링크 정규식 — 2단계 트리일 때
  ext        : 본문 저장 확장자 (.html 기본 · .pdf 가능)

★ 조작 폴백 금지(0순위 계명1) = 인덱스에서 링크 0건 파싱 시 hard-fail(sys.exit 1).
  추정 챕터 범위로 무작정 채우지 않는다. GHA 미국 IP enum 로그로 셀렉터 보정 후 재발진.

모드: --probe / --enum / --collect / --verify
"""
import os
import re
import sys
import time
import ssl
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
DELAY = float(os.environ.get("HTML_DELAY", "0.4"))
SMOKE = int(os.environ.get("SMOKE", "0"))

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 제네릭 섹션 링크 패턴 [추정] — 주별 CONFIG에 link_re 없으면 사용. GHA probe 보정 전제.
DEFAULT_LINK_RE = re.compile(
    r'href=["\']([^"\']*(?:section|chapter|title|statute|nrs|hrs|ilcs|mca|/laws/|/code/|/rcw/|/ic/)[^"\']*\d[^"\']*)["\']',
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
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
                if r.getcode() != 200:
                    return False
                tmp = path + ".part"
                with open(tmp, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                os.replace(tmp, path)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(wait)
                wait *= 2
                continue
            return False
        except Exception as ex:
            print(f"[ERR attempt={attempt}] {type(ex).__name__}: {ex}", flush=True)
            time.sleep(wait)
            wait *= 2
    return False


def _abs(base, index_url, href):
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return base + href
    return index_url.rstrip("/") + "/" + href


def _links(base, index_url, html_bytes, pattern):
    text = html_bytes.decode("utf-8", "ignore")
    out, seen = [], set()
    for href in pattern.findall(text):
        u = _abs(base, index_url, href)
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _paths(cfg):
    raw = os.environ.get(
        "RAW_DIR", f"/mnt/wsl/usdata/xsoft_data/raw/us-{cfg['state']}/statute"
    )
    return raw, os.path.join(raw, "_enum_laws.txt")


def probe(cfg):
    base, index_url = cfg["base"], cfg["index_url"]
    raw, _ = _paths(cfg)
    os.makedirs(raw, exist_ok=True)
    print(f"=== {cfg['state'].upper()} 법전 probe ({base}) ===")
    try:
        code, body = http_get(index_url)
        print(f"[index] {index_url} status={code} body_len={len(body)}")
        secs = _links(base, index_url, body, cfg.get("link_re", DEFAULT_LINK_RE))
        print(f"[index] 섹션 링크 수={len(secs)} 샘플={secs[:5]}")
        if cfg.get("chapter_re"):
            chs = _links(base, index_url, body, cfg["chapter_re"])
            print(f"[index] 챕터 링크 수={len(chs)} 샘플={chs[:5]}")
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}")
    print("주의: 지오블록 가능. 셀렉터는 GHA probe 로그로 보정 필요 [추정]")


_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def _dump_hrefs(body, n=40):
    # 0파싱 시 실제 href 구조를 GHA 미국 IP 로그에 노출 = 셀렉터 보정 근거(조작 아님·관찰).
    if not body:
        print("[DIAG hrefs] 본문 없음(챕터 순회 단계)")
        return
    text = body.decode("utf-8", "ignore")
    all_h = _HREF_RE.findall(text)
    digit_h = [h for h in all_h if any(c.isdigit() for c in h)]
    seen, sample = set(), []
    for h in digit_h:
        if h not in seen:
            seen.add(h)
            sample.append(h)
        if len(sample) >= n:
            break
    print(f"[DIAG hrefs] 전체href={len(all_h)} 숫자포함distinct={len(set(digit_h))} 샘플{len(sample)}:")
    for h in sample:
        print(f"  HREF {h[:160]}")


def _fatal_zero(kind, index_url, body=b""):
    # 0순위 계명1 = 무작정 조작 폴백 금지. 0파싱 = 구조 미확인 → hard-fail.
    # GHA(미국 IP) enum 로그의 실제 응답으로 셀렉터(link_re·chapter_re) 보정 후 재발진.
    print(f"[FATAL] 인덱스 {kind} 파싱 0건 — 구조 미확인. 조작 폴백 제거됨(계명1).")
    print(f"[FATAL] INDEX_URL={index_url} 응답을 GHA 로그로 확인하고 셀렉터 보정 필요.")
    _dump_hrefs(body)
    sys.exit(1)


def diag(cfg):
    # 관찰 전용(조작 아님) = 인덱스 실제 href 구조를 GHA 미국 IP 로그에 노출.
    # 현재 link_re/chapter_re 매칭 수도 같이 출력 → 셀렉터 보정 근거.
    base, index_url = cfg["base"], cfg["index_url"]
    print(f"=== {cfg['state'].upper()} 법전 DIAG ({base}) ===")
    try:
        code, body = http_get(index_url)
    except Exception as e:
        print(f"[FATAL] index fetch {type(e).__name__}: {e}")
        sys.exit(1)
    print(f"[DIAG index] {index_url} status={code} body_len={len(body)}")
    cur_link = cfg.get("link_re", DEFAULT_LINK_RE)
    print(f"[DIAG] 현재 link_re 매칭={len(_links(base, index_url, body, cur_link))}")
    if cfg.get("chapter_re"):
        print(f"[DIAG] 현재 chapter_re 매칭={len(_links(base, index_url, body, cfg['chapter_re']))}")
    _dump_hrefs(body, n=80)
    sys.exit(0)


def _enum_urls(cfg):
    base, index_url = cfg["base"], cfg["index_url"]
    code, body = http_get(index_url)
    if code != 200:
        print(f"[ERR] 인덱스 비200: {code}")
        sys.exit(1)
    print(f"[DIAG index] {index_url} status={code} body_len={len(body)}")
    # 1단계: 챕터 트리가 있으면 챕터별 섹션 수집
    if cfg.get("chapter_re"):
        chapters = _links(base, index_url, body, cfg["chapter_re"])
        if not chapters:
            _fatal_zero("챕터", index_url, body)
        out, seen = [], set()
        for ci, ch in enumerate(chapters, 1):
            try:
                c2, b2 = http_get(ch)
                if c2 == 200:
                    for s in _links(base, index_url, b2, cfg.get("link_re", DEFAULT_LINK_RE)):
                        if s not in seen:
                            seen.add(s)
                            out.append(s)
                if ci % 20 == 0:
                    print(f"  챕터 {ci}/{len(chapters)} 누적={len(out)}", flush=True)
            except Exception as e:
                print(f"[ch {ci}] ERR {type(e).__name__}: {e}")
            time.sleep(DELAY)
            if SMOKE and len(out) >= SMOKE:
                return out[:SMOKE]
        if not out:
            _fatal_zero("섹션(챕터 순회)", index_url)
        return out
    # 1단계 직접: 인덱스에서 바로 섹션 링크
    secs = _links(base, index_url, body, cfg.get("link_re", DEFAULT_LINK_RE))
    if not secs:
        _fatal_zero("섹션", index_url, body)
    return secs[:SMOKE] if SMOKE else secs


def enum(cfg):
    raw, enum_file = _paths(cfg)
    os.makedirs(raw, exist_ok=True)
    urls = _enum_urls(cfg)
    with open(enum_file, "w") as f:
        for u in urls:
            f.write(u + "\n")
    print(f"[OK] 열거 정본 저장: {enum_file} ({len(urls)}건)")


def _fname(cfg, url):
    base = cfg["base"]
    stem = url.replace(base, "").lstrip("/").replace("/", "_").replace("?", "_")
    return (stem or "index") + cfg.get("ext", ".html")


def collect(cfg):
    raw, enum_file = _paths(cfg)
    if not os.path.exists(enum_file):
        print(f"열거 정본 없음: {enum_file} (먼저 --enum)")
        sys.exit(1)
    with open(enum_file) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    os.makedirs(raw, exist_ok=True)
    ok = miss = skip = 0
    for i, url in enumerate(urls, 1):
        path = os.path.join(raw, _fname(cfg, url))
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
    print(f"[collect {cfg['state']}] 총={len(urls)} ok={ok} skip={skip} miss={miss}")


def verify(cfg):
    raw, enum_file = _paths(cfg)
    if not os.path.exists(enum_file):
        print(f"열거 정본 없음: {enum_file}")
        sys.exit(1)
    with open(enum_file) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    enum_set = set(urls)
    dup = len(urls) - len(enum_set)
    enum_fnames = {_fname(cfg, u) for u in enum_set}
    ext = cfg.get("ext", ".html")
    body = {
        n for n in os.listdir(raw)
        if n.endswith(ext) and not n.startswith("_") and not n.endswith(".part")
    }
    absent = enum_fnames - body
    orphan = body - enum_fnames
    rate = (len(absent) / len(enum_fnames) * 100) if enum_fnames else 0.0
    print(f"=== {cfg['state'].upper()} STATUTE 검증 4지표 ===")
    print(f"모수(섹션 URL) = {len(enum_set)}")
    print(f"저장 파일 수 = {len(body)}")
    print(f"부재 = {len(absent)} ({rate:.4f}%)")
    print(f"계층 고아 = {len(orphan)}")
    print(f"식별자 중복 = {dup}")
    ok = rate < 1.0 and len(orphan) == 0 and dup == 0
    print(f"판정 = {'PASS' if ok else 'FAIL'}")
    print("주의: 셀렉터는 GHA probe 로그로 보정 필요 [추정]")


def run(cfg):
    mode = sys.argv[1] if len(sys.argv) > 1 else "--probe"
    {"--probe": probe, "--diag": diag, "--enum": enum, "--collect": collect, "--verify": verify}.get(
        mode, lambda c: print(f"미구현 모드: {mode}")
    )(cfg)
