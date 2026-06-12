#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OR 오리건 법전 (oregonlegislature.gov) — SPA(SharePoint) Playwright 전환 2026-06-13.

정적 코어 0파싱 확정(diag run27437998104 link_re=0·href=_layouts/15·SiteAssets=SharePoint).
ORS.aspx statute 목록이 SharePoint 리스트 JS 렌더 → SPA 코어 측정. ★ 옛 추정 link_re(ors\\d+) 제거.
★ link_re 미기재 = GHA --diag 렌더 DOM href 실측 후 보정(추정 금지·계명1).
단서 = owssvr.dll?XMLDATA=1 SharePoint XML 엔드포인트(2차 정적 측정 후보).
실행 = GHA(미국 IP) headless chromium 전용. 로컬 Playwright 금지(OOM).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "or",
    "base": "https://www.oregonlegislature.gov",
    "index_url": "https://www.oregonlegislature.gov/bills_laws/Pages/ORS.aspx",
    "ext": ".html",
    # link_re = GHA --diag 실측 후 보정(추정 금지). diag 는 link_re 없이 동작.
}

if __name__ == "__main__":
    run(CONFIG)
