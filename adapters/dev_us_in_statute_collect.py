#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""인디애나 법전 (iga.in.gov) — SPA(React CRA) Playwright 표본 2026-06-13.

전환 사유 = 정적 코어 0파싱 확정(인박스 04:30 diag = body691B React CRA·정적 href 빈약).
  → SPA 코어(_us_spa_statute_core) 로 전환. ★ link_re 미기재 = GHA --diag 로 렌더된
  DOM href 실측 후 보정(추정 셀렉터 금지·계명1). diag 통과 전 enum/collect 발진 금지.
실행 = GHA(미국 IP) headless chromium 전용. 로컬 Playwright 금지(OOM)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "in",
    "base": "https://iga.in.gov",
    "index_url": "https://iga.in.gov/laws/current/ic",
    "ext": ".html",
    # link_re = GHA --diag 실측 후 보정(추정 금지). diag 는 link_re 없이 동작.
}

if __name__ == "__main__":
    run(CONFIG)
