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

# 도메인 복원+셀렉터 보정(2026-06-13) = palegis.us(7d11283) GHA 미국 IP에서도 타임아웃
#   (run 27443366471 [FATAL] URLError: timed out) → 매트릭스 [측정] 도메인 legis.state.pa.us
#   /cfdocs/legis/LI/Public/cons_index.cfm 복원 → diag(run 27444357162) status=200·숫자href312
#   ★ [측정] = cons_index.cfm 가 /statutes/consolidated/view-statute?txtType=HTM&ttl=NN 를
#   타이틀별 직접 나열(HTM·PDF·DOC·history 혼재 → HTM만 = 타이틀 중복 회피). DEFAULT 매칭 301건.
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
