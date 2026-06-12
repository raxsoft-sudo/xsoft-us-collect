#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""메릴랜드 법전 (mgaleg.maryland.gov) — SPA(Statutes JS 트리) Playwright 전환 2026-06-13.
정적 코어 statute 링크 0 확정(diag run27437998104 href=BillMasterList.csv·legislation.json=법안만).
Statutes 페이지 트리가 JS 렌더 → SPA 코어 측정. ★ link_re 미기재(추정 금지·계명1).
실행 = GHA(미국 IP) headless chromium 전용. 로컬 Playwright 금지(OOM)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "md",
    "base": "https://mgaleg.maryland.gov",
    "index_url": "https://mgaleg.maryland.gov/mgawebsite/Laws/Statutes",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
