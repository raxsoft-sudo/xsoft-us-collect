#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""앨라배마 법전 (alison.legislature.state.al.us) — SPA(Next.js) Playwright 전환 2026-06-13.
정적 코어 0파싱 확정(diag run27437998104 link_re=0·href=cms logo/_next/static).
→ SPA 코어. ★ link_re 미기재 = GHA --diag 렌더 DOM href 실측 후 보정(추정 금지·계명1).
실행 = GHA(미국 IP) headless chromium 전용. 로컬 Playwright 금지(OOM)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "al",
    "base": "https://alison.legislature.state.al.us",
    "index_url": "https://alison.legislature.state.al.us/code-of-alabama",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
