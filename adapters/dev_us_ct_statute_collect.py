#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""코네티컷 법전 (www.cga.ct.gov) — ④HTML파서 스캐폴드. 본문 PD.
도메인=매트릭스 본표 [측정] / index·셀렉터=[추정] GHA probe 로그로 보정 전제.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

# 관찰[측정:diag 27411025879] = titles.htm 가 title_NN[a-z].htm 상대링크 81개를 나열.
#   상대경로라 _abs(urljoin)로 current/pub/ 기준 결합돼야 다운로드됨(옛 _abs 버그로 collect 0였음).
CONFIG = {
    "state": "ct",
    "base": "https://www.cga.ct.gov",
    "index_url": "https://www.cga.ct.gov/current/pub/titles.htm",
    "link_re": re.compile(r'href=["\'](title_\d+[a-z]?\.htm)["\']', re.IGNORECASE),
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
