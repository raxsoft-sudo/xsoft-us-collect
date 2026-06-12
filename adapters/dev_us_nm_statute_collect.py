#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""뉴멕시코 법전 NMSA 1978 (nmonesource.com) — SPA(검색 포털) Playwright 스캐폴드.
관찰[측정:WebSearch 2026-06-13] = NMOneSource.com = NM 법원·입법부 공식 무료 포털
  (NMSA 1978 master DB·검색형 JS 앱). srca.nm.gov 는 NMAC(행정규칙)라 statute 아님 → 제외.
  검색 포털 = SPA → 정적 코어 0파싱 예상. SPA 코어 --diag/--netcap 로 렌더 DOM·XHR API 실측.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제.
★ link_re 미기재 = GHA --diag/--netcap 실측 후 보정(추정 금지·계명1)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "nm",
    "base": "https://nmonesource.com",
    "index_url": "https://nmonesource.com/",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
