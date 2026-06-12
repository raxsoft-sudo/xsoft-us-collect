#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archive.org CC0 벌크 statute 공통 코어 — CONFIG 주입형 (2026-06-13).

NC 어댑터(da925da)가 입증한 패턴을 일반화 = metadata API → release/최상위 필터
  → enum(다운로드 URL 열거) → collect → verify(4지표). 추정 0·공개 CC0 item만.

CONFIG 키 (전부 측정으로 확정·빈칸0):
  state         : 주 약어 (저장경로 us-XX/statute)
  item          : archive.org identifier (예: gov.wy.code)
  ext           : 본문 확장자 (.rtf / .pdf)
  stat_re       : 본문 파일 basename 매칭 정규식 (예: r'^gov\\.wy\\.code\\..*\\.rtf$')
  release_re    : (선택) release 폴더 prefix 정규식 group1 (예: r'(release[\\d.]+)/').
                  None 이면 최상위 파일 직접 매칭(ga 볼륨형).
  release_num_re: (선택) 최신 release 정렬용 숫자 추출 (예: r'release(\\d+)')
  asof          : 현행성 메타 표기 (verify 출력용)

환경변수:
  RAW_DIR  = 저장 경로 (collect.yml이 out/us-XX/statute 주입)
  DELAY    = 요청 간격(초, 기본 0.5) — archive.org 단일 워커 직렬
  RELEASE  = release 폴더 강제 지정 (기본 = metadata 최신)
  SMOKE    = 정수 N → collect()에서 N건 후 중단 (시험용)
"""
import os
import re
import sys
import json
import time
import urllib.request
import urllib.parse

UA = "Mozilla/5.0 (compatible; xsoft-comply-collector/1.0)"


def _paths(cfg):
    raw = os.environ.get(
        "RAW_DIR", f"/home/xsoft/xsoft_data/raw/us-{cfg['state']}/statute"
    )
    return raw, os.path.join(raw, "_enum_laws.txt")


def _delay():
    return float(os.environ.get("DELAY", "0.5"))


def _fetch_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _latest_release(files, cfg):
    rel_re = cfg.get("release_re")
    if not rel_re:
        return None
    num_re = cfg.get("release_num_re")
    rels = set()
    for f in files:
        m = re.match(rel_re, f.get("name", ""))
        if m:
            rels.add(m.group(1))
    if not rels:
        return None

    def key(r):
        if num_re:
            m = re.search(num_re, r)
            return int(m.group(1)) if m else 0
        return r

    return sorted(rels, key=key)[-1]


def _stat_names(files, cfg, release):
    pat = re.compile(cfg["stat_re"])
    out = []
    for f in files:
        n = f.get("name", "")
        if release is not None and not n.startswith(release + "/"):
            continue
        if release is None and "/" in n:
            continue  # 최상위형(ga)은 하위폴더 제외
        base = n.split("/")[-1]
        if pat.match(base):
            out.append(n)
    return sorted(out)


def _meta(cfg):
    return _fetch_json(f"https://archive.org/metadata/{cfg['item']}")


def probe(cfg):
    try:
        d = _meta(cfg)
    except Exception as e:
        print(f"[probe {cfg['state']}] metadata 접근 실패: {e}")
        sys.exit(1)
    md = d.get("metadata", {})
    files = d.get("files", [])
    rel = os.environ.get("RELEASE") or _latest_release(files, cfg)
    stat = _stat_names(files, cfg, rel)
    print(f"=== {cfg['state'].upper()} archive.org CC0 구조 ===")
    print(f"item = {cfg['item']}")
    print(f"license = {md.get('licenseurl')}")
    print(f"총 파일수 = {len(files)}")
    print(f"release = {rel}")
    print(f"본문({cfg['stat_re']}) 수 = {len(stat)}")
    for s in stat[:8]:
        print(f"  {s}")


def enum(cfg):
    raw, enum_file = _paths(cfg)
    os.makedirs(raw, exist_ok=True)
    d = _meta(cfg)
    files = d.get("files", [])
    release = os.environ.get("RELEASE") or _latest_release(files, cfg)
    names = _stat_names(files, cfg, release)
    if not names:
        print(
            f"[enum {cfg['state']}] 본문 0건(release={release}) "
            f"→ hard-fail (추정 폴백 금지·계명1)"
        )
        sys.exit(1)
    base = f"https://archive.org/download/{cfg['item']}"
    urls = [f"{base}/{urllib.parse.quote(n)}" for n in names]
    with open(enum_file, "w") as f:
        for u in urls:
            f.write(u + "\n")
    print(f"[OK] 열거 정본 저장: {enum_file} ({len(urls)}건, release={release})")


def _fname(url):
    return urllib.parse.unquote(url.split("/")[-1])


def _download(url, path, delay, tries=3):
    for t in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            if not data:
                raise ValueError("빈 응답")
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
            return True
        except Exception as e:
            if t == tries:
                print(f"  [miss] {url} ({e})")
                return False
            time.sleep(delay * t)
    return False


def collect(cfg):
    raw, enum_file = _paths(cfg)
    if not os.path.exists(enum_file):
        print(f"열거 정본 없음: {enum_file} (먼저 --enum)")
        sys.exit(1)
    with open(enum_file) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    os.makedirs(raw, exist_ok=True)
    delay = _delay()
    _sv = os.environ.get("SMOKE", "0").strip().lower()
    smoke = 5 if _sv in ("true", "yes") else (int(_sv) if _sv.isdigit() else 0)
    ok = miss = skip = 0
    for i, url in enumerate(urls, 1):
        path = os.path.join(raw, _fname(url))
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue
        if _download(url, path, delay):
            ok += 1
        else:
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
    if not os.path.exists(enum_file):
        print(f"열거 정본 없음: {enum_file}")
        sys.exit(1)
    with open(enum_file) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    enum_set = set(urls)
    dup = len(urls) - len(enum_set)
    enum_fnames = {_fname(u) for u in enum_set}
    ext = cfg["ext"]
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
    print(
        f"출처 = archive.org {cfg['item']} CC0 "
        f"(현행성 {cfg.get('asof', '?')}·{cfg['ext']} 본문) [측정]"
    )


def run(cfg):
    mode = sys.argv[1] if len(sys.argv) > 1 else "--probe"
    fn = {
        "--probe": probe, "--diag": probe, "--enum": enum,
        "--collect": collect, "--verify": verify,
    }.get(mode)
    if fn:
        fn(cfg)
    else:
        print(f"미구현 모드: {mode}")
