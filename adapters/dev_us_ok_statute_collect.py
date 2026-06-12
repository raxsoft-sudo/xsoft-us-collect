#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""오클라호마 법전 (www.oklegislature.gov) — SPA(ASP.NET postback) Playwright 전환 2026-06-13.
정적 코어 0파싱 확정(diag run27437998104 link_re=0·href=css/EBillTrack/미디어).
TitleIndex.aspx 는 __doPostBack JS 네비 → SPA 코어 렌더 측정. ★ link_re 미기재(추정 금지·계명1).
실행 = GHA(미국 IP) headless chromium 전용. 로컬 Playwright 금지(OOM)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "ok",
    "base": "https://www.oklegislature.gov",
    "index_url": "https://www.oklegislature.gov/TitleIndex.aspx",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
