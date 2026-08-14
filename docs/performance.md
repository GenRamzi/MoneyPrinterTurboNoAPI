# Performance and GPU Notes

The repository benchmark measures the complete local path: task submission, neural TTS, ASS subtitle generation, FFmpeg composition, MP4 download, and encoder reporting. Run it with:

```bash
MPT_BENCH_URL=http://127.0.0.1:8501 ./scripts/benchmark.sh
```

The current validation environment exposes FFmpeg software support for `h264_nvenc`, `h264_qsv`, and `h264_vaapi`, but it has no usable NVIDIA runtime, no `/dev/dri/renderD128`, and no detected GPU. Therefore `MPT_GPU_BACKEND=auto` correctly selected `CPU / libx264`.

A real end-to-end benchmark using a ten-second custom narration completed successfully in approximately **7.095 seconds** and produced a valid MP4. A separate ASS integration run completed in approximately **6.768 seconds**, generated `captions.ass`, served it through the artifact endpoint, and passed ffprobe validation.

For parallel batch measurements, set `MPT_BENCH_BATCH_COUNT=2` before running the benchmark. The task engine renders the visual background and final MP4 for each variant concurrently, while keeping narration and subtitle preparation shared. `MPT_MAX_BATCH_WORKERS` defaults to 2 to avoid uncontrolled FFmpeg process growth; increase it only after measuring CPU, GPU memory, disk throughput, and thermal behavior on the target machine.

In the current validation environment, a real batch of two custom-narration videos completed in approximately **12.130 seconds** with `CPU / libx264`. This is a host-specific measurement, not a universal speedup claim.

GPU backends are selected only when both the FFmpeg encoder and a usable runtime are detected. Explicitly requesting an unavailable backend fails early with a clear API validation error; `auto` always remains safe and falls back to CPU. Because no GPU was present in this environment, a numeric GPU-vs-CPU speedup claim cannot be made without hardware-specific measurements.
