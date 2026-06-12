#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OR 오리건 법전 (oregonlegislature.gov) — ①공식벌크(챕터별 HTML) 스캐폴드.

본문 PD [측정=매트릭스 본표]. 도메인 oregonlegislature.gov [측정] (public.law 가공본 존재).
Oregon Revised Statutes = 챕터별 HTML/PDF. URL 템플릿·챕터 상한=[추정] GHA probe 보정 전제.
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
    # ors NNN.html 링크 [추정]
    "link_re": re.compile(r'href=["\']([^"\']*ors\d+[^"\']*\.html?)["\']', re.IGNORECASE),
    # 링크 파싱 실패 시 챕터 1~838 HTML 직접 폴백 [추정] (zero-pad 3자리)
    "fallback": (
        "https://www.oregonlegislature.gov/bills_laws/ors/ors{n:03d}.html",
        1,
        838,
    ),
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
