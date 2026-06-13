#!/usr/bin/env bash
# archive.org enum 경로 직접 다운로드 워커 (ND/VT 등 CC0 PD)
# 사용: dl_archive_enum.sh <state> <item>
set -u
s="$1"; it="$2"
base="/mnt/wsl/usdata_ssd/xsoft_data/raw/03.US/us-$s/statute"
enum="$base/_enum_files.txt"
ok=0; miss=0; skip=0; n=0
total=$(grep -c . "$enum")
while IFS= read -r path; do
  [ -z "$path" ] && continue
  n=$((n+1))
  out="$base/$(echo "$path" | tr '/' '__')"
  if [ -s "$out" ]; then skip=$((skip+1)); continue; fi
  url="https://archive.org/download/$it/$path"
  if ionice -c3 curl -sfL --retry 4 --retry-delay 3 -o "$out" "$url"; then
    ok=$((ok+1))
  else
    rm -f "$out"; miss=$((miss+1))
  fi
  [ $((n % 50)) -eq 0 ] && echo "[$s] $n/$total ok=$ok skip=$skip miss=$miss"
  sleep 0.15
done < "$enum"
echo "${s}_DLDONE total=$total ok=$ok skip=$skip miss=$miss"
