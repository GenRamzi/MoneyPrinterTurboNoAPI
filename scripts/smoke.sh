#!/usr/bin/env bash
set -euo pipefail

base_url="${MPT_SMOKE_URL:-http://127.0.0.1:8501}"
payload='{"topic":"Smoke test","script":"This is a local smoke test for the complete video pipeline.","duration":10,"provider":"gemini","voice":"en-US-AvaNeural","subtitles":true,"batch_count":1,"aspect_ratio":"16:9","clip_duration":2}'

response="$(curl -fsS -H 'Content-Type: application/json' -d "$payload" "$base_url/api/tasks")"
task_id="$(printf '%s' "$response" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')"
if [ -z "$task_id" ]; then
  printf 'Could not create smoke-test task: %s\n' "$response" >&2
  exit 1
fi

printf 'Created task %s\n' "$task_id"
for attempt in $(seq 1 90); do
  status_json="$(curl -fsS "$base_url/api/tasks/$task_id")"
  state="$(printf '%s' "$status_json" | sed -n 's/.*"state":"\([^"]*\)".*/\1/p')"
  progress="$(printf '%s' "$status_json" | sed -n 's/.*"progress":\([0-9]*\).*/\1/p')"
  printf 'Attempt %s: %s (%s%%)\n' "$attempt" "$state" "$progress"

  case "$state" in
    completed)
      filename="$(printf '%s' "$status_json" | sed -n 's/.*"output_files":\["\([^"]*\)"\].*/\1/p')"
      test -n "$filename"
      output="$(mktemp --suffix=.mp4)"
      artifact="$(mktemp --suffix=.txt)"
      trap 'rm -f "$output" "$artifact"' EXIT
      curl -fsS -o "$output" "$base_url/api/tasks/$task_id/files/$filename"
      curl -fsS -o "$artifact" "$base_url/api/tasks/$task_id/artifacts/script.txt"
      test -s "$output"
      test -s "$artifact"
      ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$output"
      printf 'Smoke test passed for task %s\n' "$task_id"
      exit 0
      ;;
    failed|cancelled)
      printf 'Smoke test ended in %s: %s\n' "$state" "$status_json" >&2
      exit 1
      ;;
  esac
  sleep 2
done

printf 'Smoke test timed out for task %s\n' "$task_id" >&2
exit 1
