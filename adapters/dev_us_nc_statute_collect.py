#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NC 주법전 (archive.org CC0 벌크) 수집기 — 재저작 2026-06-13.

전(前) 어댑터 = ncleg.gov 직접 → Cloudflare WAF 하드 차단(BLOCKED).
  (보존 = _us_nc_ncleg_fallback.py = 增分 폴백용)
재저작 사유 = 리서치 0610 A표 = archive.org/details/gov.nc.code 가 CC0(Public Domain Zero,
  상업 재배포 허용)·지오블록 없음. 1차 벌크 소스로 채택.

★ 구조 실측 (2026-06-13 metadata API):
  archive.org item = gov.nc.code / license = CC0 1.0
  release 폴더 8개 = release77.2021.06 … release85.2023.06 (최신)
  본체 = release85.2023.06/gov.nc.stat.title.NNN.rtf (챕터 단위) + 헌법·index
  AG 의견서(gov.nc.ag.opinions)·court.rules 는 statute 아님 → 필터 제외
  ★ 현행성 = 2023.06 (2024+ 아님) = 보강용. 현행 增分은 ncleg.gov 폴백 [측정]

모드:
  --probe / --diag : metadata API 로 release 폴더·파일수 구조 덤프
  --enum    : 최신 release 의 gov.nc.stat.*.rtf 다운로드 URL 열거 → _enum_laws.txt
  --collect : _enum_laws.txt 순회 → RTF 저장 (SMOKE=N 환경변수로 N건 후 중단)
  --verify  : 4지표 검증 (모수·부재율·계층고아·식별자중복)

환경변수:
  RAW_DIR   = 저장 경로 (기본 /mnt/wsl/usdata/xsoft_data/raw/us-nc/statute)
  NC_DELAY  = 요청 간격(초, 기본 0.5) — archive.org 단일 워커 직렬
  NC_RELEASE= release 폴더 강제 지정 (기본 = metadata 최신)
  SMOKE     = 정수 N → collect()에서 N건 후 중단 (시험용)
"""
import os
import re
import sys
import json
import time
import urllib.request
import urllib.error

ITEM = "gov.nc.code"
META_URL = f"https://archive.org/metadata/{ITEM}"
DL_BASE = f"https://archive.org/download/{ITEM}"
EXT = ".rtf"
STAT_PREFIX = "gov.nc.stat."   # General Statutes + 헌법 + index (ag.opinions·court.rules 제외)
DELAY = float(os.environ.get("NC_DELAY", "0.5"))
UA = "Mozilla/5.0 (compatible; xsoft-comply-collector/1.0)"


def _paths():
    raw = os.environ.get("RAW_DIR", "/mnt/wsl/usdata/xsoft_data/raw/us-nc/statute")
    return raw, os.path.join(raw, "_enum_laws.txt")


def _fetch_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _latest_release(files):
    rels = set()
    for f in files:
        m = re.match(r"(release[\d.]+)/", f.get("name", ""))
        if m:
            rels.add(m.group(1))
    if not rels:
        return None

    def key(r):
        m = re.match(r"release(\d+)", r)
        return int(m.group(1)) if m else 0

    return sorted(rels, key=key)[-1]


def _stat_files(files, release):
    out = []
    for f in files:
        n = f.get("name", "")
        if not n.startswith(release + "/"):
            continue
        base = n.split("/")[-1]
        if base.startswith(STAT_PREFIX) and base.endswith(EXT):
            out.append(n)
    return sorted(out)


def probe():
    try:
        d = _fetch_json(META_URL)
    except Exception as e:
        print(f"[probe nc] metadata 접근 실패: {e}")
        sys.exit(1)
    md = d.get("metadata", {})
    files = d.get("files", [])
    rel = _latest_release(files)
    stat = _stat_files(files, rel) if rel else []
    print("=== NC archive.org CC0 구조 ===")
    print(f"license = {md.get('licenseurl')}")
    print(f"총 파일수 = {len(files)}")
    print(f"최신 release = {rel}")
    print(f"statute(gov.nc.stat.*.rtf) 수 = {len(stat)}")
    for s in stat[:8]:
        print(f"  {s}")


diag = probe


def enum():
    raw, enum_file = _paths()
    os.makedirs(raw, exist_ok=True)
    d = _fetch_json(META_URL)
    files = d.get("files", [])
    release = os.environ.get("NC_RELEASE") or _latest_release(files)
    if not release:
        print("[enum nc] release 폴더 없음 → hard-fail")
        sys.exit(1)
    names = _stat_files(files, release)
    if not names:
        print(f"[enum nc] {release} 에 gov.nc.stat.*.rtf 0건 → hard-fail (추정 폴백 금지)")
        sys.exit(1)
    urls = [f"{DL_BASE}/{n}" for n in names]
    with open(enum_file, "w") as f:
        for u in urls:
            f.write(u + "\n")
    print(f"[OK] 열거 정본 저장: {enum_file} ({len(urls)}건, release={release})")


def _fname(url):
    return url.split("/")[-1]


def _download(url, path, tries=3):
    for t in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
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
            time.sleep(DELAY * t)
    return False


def collect():
    raw, enum_file = _paths()
    if not os.path.exists(enum_file):
        print(f"열거 정본 없음: {enum_file} (먼저 --enum)")
        sys.exit(1)
    with open(enum_file) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    os.makedirs(raw, exist_ok=True)
    smoke = int(os.environ.get("SMOKE", "0"))
    ok = miss = skip = 0
    for i, url in enumerate(urls, 1):
        path = os.path.join(raw, _fname(url))
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue
        if _download(url, path):
            ok += 1
        else:
            miss += 1
        if i % 50 == 0:
            print(f"  진행 {i}/{len(urls)} ok={ok} skip={skip} miss={miss}", flush=True)
        if smoke and ok >= smoke:
            print(f"  [SMOKE] {smoke}건 후 중단")
            break
        time.sleep(DELAY)
    print(f"[collect nc] 총={len(urls)} ok={ok} skip={skip} miss={miss}")


def verify():
    raw, enum_file = _paths()
    if not os.path.exists(enum_file):
        print(f"열거 정본 없음: {enum_file}")
        sys.exit(1)
    with open(enum_file) as f:
        urls = [ln.strip() for ln in f if ln.strip()]
    enum_set = set(urls)
    dup = len(urls) - len(enum_set)
    enum_fnames = {_fname(u) for u in enum_set}
    body = {
        n for n in os.listdir(raw)
        if n.endswith(EXT) and not n.startswith("_") and not n.endswith(".part")
    }
    absent = enum_fnames - body
    orphan = body - enum_fnames
    rate = (len(absent) / len(enum_fnames) * 100) if enum_fnames else 0.0
    print("=== NC STATUTE 검증 4지표 ===")
    print(f"모수(섹션 URL) = {len(enum_set)}")
    print(f"저장 파일 수 = {len(body)}")
    print(f"부재 = {len(absent)} ({rate:.4f}%)")
    print(f"계층 고아 = {len(orphan)}")
    print(f"식별자 중복 = {dup}")
    ok = rate < 1.0 and len(orphan) == 0 and dup == 0
    print(f"판정 = {'PASS' if ok else 'FAIL'}")
    print("출처 = archive.org gov.nc.code CC0 (현행성 2023.06·보강용·ncleg 增分 폴백) [측정]")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--probe"
    {
        "--probe": probe, "--diag": diag, "--enum": enum,
        "--collect": collect, "--verify": verify,
    }.get(mode, lambda: print(f"미구현 모드: {mode}"))()


if __name__ == "__main__":
    main()
