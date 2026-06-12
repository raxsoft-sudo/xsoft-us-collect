#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""매사추세츠 법전 (malegislature.gov) — 정적 다단 2026-06-13.
헤더 보정(07a8725)으로 정적 200 도달(rediag run27438905611 link_re=11).
섹션 href 관찰 = /Laws/GeneralLaws/{Part}/{Title}/{Chapter}/{Section}.
★ chapter_re = 관찰 섹션 URL에서 파생한 Chapter 목록 링크(Section 없이 끝)
  = 추정 아님(데이터 파생). 2단 트리 매칭은 GHA --diag 로 검증 후 enum.
실행 = GHA(미국 IP). 한국 IP 지오블록."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "ma",
    "base": "https://malegislature.gov",
    "index_url": "https://malegislature.gov/Laws/GeneralLaws/PartI",
    "ext": ".html",
    # chapter 목록 링크(Section 없이 Chapter 로 끝) — 관찰 섹션 URL 파생·diag 검증 전제
    "chapter_re": re.compile(
        r'href=["\']([^"\']*/Laws/GeneralLaws/Part[A-Za-z]+/Title[A-Za-z]+/Chapter[0-9A-Za-z]+)["\']',
        re.IGNORECASE,
    ),
}

if __name__ == "__main__":
    run(CONFIG)
