#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""펜실베이니아 법전 (www.legis.state.pa.us) — ④HTML파서 스캐폴드. 본문 PD.
도메인=매트릭스 본표 [측정] / index·셀렉터=[추정] GHA probe 로그로 보정 전제.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

# 관찰[측정:diag 27411025879] = cons_index.cfm 가 타이틀별 HTM 뷰 링크를 직접 나열.
#   /statutes/consolidated/view-statute?txtType=HTM&amp;ttl=NN (HTM·PDF·DOC 혼재 → HTM만).
CONFIG = {
    "state": "pa",
    "base": "https://www.legis.state.pa.us",
    "index_url": "https://www.legis.state.pa.us/cfdocs/legis/LI/Public/cons_index.cfm",
    "link_re": re.compile(
        r'href=["\'](/statutes/consolidated/view-statute\?txtType=HTM&amp;ttl=\d+)["\']',
        re.IGNORECASE,
    ),
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
