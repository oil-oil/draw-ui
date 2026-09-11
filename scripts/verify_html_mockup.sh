#!/usr/bin/env bash
# 兼容脚本名称；截图由当前已授权的宿主浏览器生成，不再隐式启动另一套浏览器。
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/verify_capture.py" "$@"
