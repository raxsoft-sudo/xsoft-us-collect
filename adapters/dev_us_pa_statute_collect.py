#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""펜실베이니아 법전 (www.legis.state.pa.us) — ④HTML파서 스캐폴드. 본문 PD.
도메인=매트릭스 본표 [측정] / index·셀렉터=[추정] GHA probe 로그로 보정 전제.
지오블록으로 WSL(한국 IP) probe 불가 → GHA(미국 IP) 실행 전제."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

# 도메인 복원(2026-06-13) = palegis.us(7d11283) GHA 미국 IP에서도 index fetch 타임아웃
#   (run 27443366471 [FATAL] URLError: timed out) → 매트릭스 [측정] 도메인 legis.state.pa.us
#   /cfdocs/legis/LI/Public/cons_index.cfm(최초 측정 27411025879)로 되돌림.
#   link_re 는 제거 = palegis.us 경로(view-statute)가 cons_index.cfm 출력과 불일치할 수 있어
#   GHA --diag 실측 후 보정(추정 금지·계명1).
CONFIG = {
    "state": "pa",
    "base": "https://www.legis.state.pa.us",
    "index_url": "https://www.legis.state.pa.us/cfdocs/legis/LI/Public/cons_index.cfm",
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
