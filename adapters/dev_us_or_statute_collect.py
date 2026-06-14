#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OR 오리건 법전 (oregonlegislature.gov) — 정적 ors{NNN}.html (인덱스 SPA 우회·2026-06-14).

배경 = ORS.aspx 목록은 SharePoint SPA(JS 렌더) → 정적 코어 0파싱(run27437998104).
★ 우회 = 챕터별 정적 HTML ors{NNN}.html 직수집(리서치 0614). 인덱스 파싱 대신 챕터번호
  생성+probe 로 실재 챕터만 열거(추정 단일 URL 단정 금지·diag 선행으로 패턴 확증·계명1).
본문 단위 = 챕터(각 ors{NNN}.html 1파일 = 1챕터 전조문). 라이선스 = 퍼블릭도메인.
실행 = GHA(미국 IP) 전용. 로컬 금지(지오블록).

모드: --diag(샘플 probe로 패턴·소프트404 측정) / --enum(1~MAX probe) / --collect / --verify
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _us_html_statute_core as core  # noqa: E402

CONFIG = {
    "state": "or",
    "base": "https://www.oregonlegislature.gov",
    "index_url": "https://www.oregonlegislature.gov/bills_laws/ors/",
    "ext": ".html",
}

# 챕터 정적 HTML 템플릿 [리서치 0614·diag 확증 전제]. {n:03d} = 001..NNN 제로패딩.
ORS_TMPL = "https://www.oregonlegislature.gov/bills_laws/ors/ors{n:03d}.html"
MAX_CHAPTER = 999  # ORS 챕터 상한 여유(실재만 probe 로 채택). 결손 챕터는 비2xx로 자동 제외.
MIN_BODY = int(os.environ.get("OR_MIN_BODY", "3000"))  # 소프트404 컷(diag 측정으로 보정 가능)


def or_diag(cfg):
    # 정적 ors{NNN}.html 패턴·소프트404 측정(관찰 전용·조작 아님). 존재/결손 챕터 혼합 샘플.
    print(f"=== OR 법전 DIAG (정적 ors{{NNN}}.html · {cfg['base']}) ===")
    for n in (1, 100, 174, 401, 656, 850, 999):
        url = ORS_TMPL.format(n=n)
        try:
            code, body = core.http_get(url, timeout=60)
            head = body[:200].decode("utf-8", "ignore").replace("\n", " ")
            print(f"[DIAG] ors{n:03d} status={code} len={len(body)} head={head[:90]}")
        except Exception as e:
            print(f"[DIAG ERR] ors{n:03d} {type(e).__name__}: {e}")
        time.sleep(core.DELAY)
    print(f"주의: 200+len>{MIN_BODY} 를 실재 챕터로 채택(소프트404 컷). enum 전 본 샘플로 컷 보정.")
    sys.exit(0)


def or_enum(cfg):
    raw, enum_file = core._paths(cfg)
    os.makedirs(raw, exist_ok=True)
    found, miss = [], 0
    smoke = core.SMOKE
    for n in range(1, MAX_CHAPTER + 1):
        url = ORS_TMPL.format(n=n)
        ok = False
        for attempt in range(3):
            try:
                code, body = core.http_get(url, timeout=60)
                if 200 <= code < 300 and len(body) >= MIN_BODY:
                    found.append(url)
                    ok = True
                break
            except Exception:
                time.sleep(1.5 * (attempt + 1))
        if not ok:
            miss += 1
        if n % 100 == 0:
            print(f"  probe {n}/{MAX_CHAPTER} 실재={len(found)}", flush=True)
        time.sleep(core.DELAY)
        if smoke and len(found) >= smoke:
            break
    if not found:
        print("[FATAL] OR ors{NNN}.html 실재 0건 — 패턴 미확인(계명1). diag 로그 확인 후 보정.")
        sys.exit(1)
    with open(enum_file, "w") as f:
        for u in found:
            f.write(u + "\n")
    print(f"[OK] OR 열거 정본 저장: {enum_file} (실재 챕터={len(found)})")


def run(cfg):
    mode = sys.argv[1] if len(sys.argv) > 1 else "--diag"
    if mode == "--diag":
        or_diag(cfg)
    elif mode == "--enum":
        or_enum(cfg)
    elif mode == "--collect":
        core.collect(cfg)
    elif mode == "--verify":
        core.verify(cfg)
    else:
        print(f"미구현 모드: {mode}")


if __name__ == "__main__":
    run(CONFIG)
