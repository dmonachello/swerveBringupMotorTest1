# Project Intent

## Why This Exists
This project exists because we needed a reliable bringup and diagnostics tool for CAN-based robot hardware. When devices misbehave or disappear on the bus, the standard workflow is slow and fragmented. This tool gives fast, repeatable visibility into:
- local device health (from the roboRIO),
- bus-level CAN health,
- passive PC-side CAN evidence.

The goal is to shorten the time from "something is wrong" to "we know exactly where to look."

## Why Build It This Way
We wanted a practical, field-useful tool that is:
- data-driven for hardware configuration,
- safe to use during bringup,
- fast to interpret by operators.

I also wanted a non-trivial project to evaluate the real-world usefulness of an AI coding assistant like Codex. This work primarily used the Codex plugin from VS Code. This repo is the result of that exploration: a real tool, built iteratively, with AI assistance applied to production-style work.

This repository is almost entirely AI-created, including both code and documentation.

## Related Ideas (Review Later)
- Profile validation with clear, actionable error messages.
- Offline replay of PCAP captures through the analyzer.
- A compact one-line "pit mode" summary.
- Optional dashboard view of key diagnostics.
- A small "experiment mode" for automated, repeatable traffic generation.

