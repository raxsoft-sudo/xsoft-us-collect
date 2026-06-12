#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""일리노이 법전 (www.ilga.gov) — ④HTML파서 스캐폴드. 본문 PD.
도메인=매트릭스 본표 [측정] / index·셀렉터=[추정] GHA probe 로그로 보정 전제.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

# 관찰[측정:diag 27411025879] = ilcs.asp 가 챕터 링크 /Legislation/ILCS/Acts?ChapterID=N 를 나열(2단 트리).
#   섹션 link_re 는 챕터 페이지 내부 구조를 diag 챕터 덤프로 관찰 후 확정(추측 금지).
CONFIG = {
    "state": "il",
    "base": "https://www.ilga.gov",
    "index_url": "https://www.ilga.gov/legislation/ilcs/ilcs.asp",
    "chapter_re": re.compile(
        r'href=["\'](/Legislation/ILCS/Acts\?ChapterID=\d+[^"\']*)["\']', re.IGNORECASE
    ),
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
