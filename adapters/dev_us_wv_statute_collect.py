#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""웨스트버지니아 법전 (code.wvlegislature.gov) — ④HTML파서. 본문 PD.
도메인=매트릭스 본표 [측정] / 셀렉터=GHA 미국 IP href 덤프(run27406616135)로 보정 [측정].
인덱스(WordPress)가 챕터-아티클을 /N-N/ 형태로 직접 링크 → link_re 그 패턴.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제."""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "wv",
    "base": "https://code.wvlegislature.gov",
    "index_url": "https://code.wvlegislature.gov/",
    # /1-1/ /1-2/ … = 챕터-아티클 페이지 [측정=GHA href 덤프]. 숫자[영문]-숫자[영문] 패턴
    "link_re": re.compile(r'href=["\'](/\d+[a-zA-Z]?-\d+[a-zA-Z]?/)["\']', re.IGNORECASE),
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
