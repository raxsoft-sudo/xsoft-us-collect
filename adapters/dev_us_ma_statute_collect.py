#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""매사추세츠 법전 (malegislature.gov) — SPA(JS 렌더 트리) netcap 측정 전환 2026-06-13.
헤더 보정으로 정적 200 도달했으나 트리는 JS 렌더 확정 :
  GeneralLaws 루트 = Part 진입점 5개(PartI~PartV) 정적 실재(run27440421293 깊이분포 3:5)
  PartI 페이지(run27440508871 status200·body120KB) statute href=0 = Title/Chapter/Section
  트리가 전부 클라이언트 JS 렌더(정적 href 부재) → 정적 코어로 루트 아래 진입 불가.
★ SPA 코어 전환 = statute 목록 API URL 미측정 → --netcap 으로 XHR/fetch 응답 URL 데이터 발굴.
  발굴된 실제 API URL 로만 link_re/index_url 보정(추정 URL 금지·계명1). link_re 미기재.
실행 = GHA(미국 IP) headless chromium 전용. 로컬 Playwright 금지(OOM)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "ma",
    "base": "https://malegislature.gov",
    "index_url": "https://malegislature.gov/Laws/GeneralLaws",
    "ext": ".html",
    # link_re = --netcap 발굴 statute API URL 후 보정(추정 금지). netcap/diag 는 link_re 없이 동작.
}

if __name__ == "__main__":
    run(CONFIG)
