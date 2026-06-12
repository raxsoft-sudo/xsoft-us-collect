#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OR 오리건 법전 (oregonlegislature.gov) — ④HTML파서 스캐폴드.

본문 PD [측정=매트릭스 본표]. 도메인 oregonlegislature.gov [측정] (public.law 가공본 존재).
index·셀렉터=[추정] GHA probe 로그로 보정 전제. 0파싱 시 코어 hard-fail(조작 폴백 금지·계명1).
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제.
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "or",
    "base": "https://www.oregonlegislature.gov",
    "index_url": "https://www.oregonlegislature.gov/bills_laws/Pages/ORS.aspx",
    # ors NNN.html 링크 [추정] — 0파싱 시 코어가 hard-fail(조작 폴백 금지·계명1)
    "link_re": re.compile(r'href=["\']([^"\']*ors\d+[^"\']*\.html?)["\']', re.IGNORECASE),
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
