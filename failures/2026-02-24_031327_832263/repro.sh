#!/usr/bin/env bash
python3 -m src.cli pbt replay "$(cd "$(dirname "$0")" && pwd)"
