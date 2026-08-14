#!/usr/bin/env bash
set -euo pipefail

base_url="${MPT_BENCH_URL:-http://127.0.0.1:8501}"
batch_count="${MPT_BENCH_BATCH_COUNT:-2}"
start_ms="$(date +%s%3N)"
backend_json="$(curl -fsS "$base_url/api/gpu")"
backend="$(printf '%s' "$backend_json" | sed -n 's/.*"selected":"\([^"]*\)".*/\1/p')"
payload="{\"topic\":\"Benchmark\",\"script\":\"This benchmark measures the complete local rendering path.\",\"duration\":10,\"provider\":\"gemini\",\"voice\":\"en-US-AvaNeural\",\"subtitles\":true,\"subtitle_format\":\"ass\",\"gpu_backend\":\"auto\",\"batch_count\":${batch_count},\"aspect_ratio\":\"16:9\",\"clip_duration\":2}"
response="$(curl -fsS -H 'Content-Type: application/json' -d "$payload" "$base_url/api/tasks")"
task_id="$(printf '%s' "$response" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')"
test -n "$task_id"

for _ in $(seq 1 120); do
  status_json="$(curl -fsS "$base_url/api/tasks/$task_id")"
  state="$(printf '%s' "$status_json" | sed -n 's/.*"state":"\([^"]*\)".*/\1/p')"
  if [ "$state" = "completed" ]; then
    end_ms="$(date +%s%3N)"
    elapsed_ms=$((end_ms - start_ms))
    encoder="$(printf '%s' "$status_json" | sed -n 's/.*"encoder":"\([^"]*\)".*/\1/p')"
    printf 'backend=%s encoder="%s" batch_count=%s elapsed_seconds=%.3f task=%s\n' "$backend" "$encoder" "$batch_count" "$(awk "BEGIN {print $elapsed_ms / 1000}")" "$task_id"
    exit 0
  fi
  if [ "$state" = "failed" ] || [ "$state" = "cancelled" ]; then
    printf '%s\n' "$status_json" >&2
    exit 1
  fi
  sleep 1
done
printf 'Benchmark timed out for task %s\n' "$task_id" >&2
exit 1
