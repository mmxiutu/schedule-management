#!/usr/bin/env bash
# 在 Linux / 树莓派本机执行，生成可直接运行的二进制（不能在 Windows 上交叉编译）。
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "请在 Linux 或树莓派上运行本脚本，Windows 请用 build_win_gui.bat。"
  exit 1
fi

echo "[1/4] 准备虚拟环境..."
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/4] 安装依赖与 PyInstaller..."
python -m pip install -U pip
python -m pip install -e .
python -m pip install pyinstaller

echo "[3/4] 打包（onedir，无控制台窗口）..."
rm -rf build dist
pyinstaller --noconfirm --clean --windowed --onedir \
  --name ScheduleAssistant \
  --paths src \
  --collect-all chinese_calendar \
  --collect-all tzdata \
  --collect-all pystray \
  --hidden-import jwt \
  --hidden-import cryptography \
  --hidden-import PIL._tkinter_finder \
  --hidden-import schedule_assistant \
  --add-data "src/schedule_assistant/assets/fonts:schedule_assistant/assets/fonts" \
  src/schedule_assistant/main.py

APP_DIR="$(pwd)/dist/ScheduleAssistant"
BIN="$APP_DIR/ScheduleAssistant"
chmod +x "$BIN"

DESKTOP="$APP_DIR/日程管理助手.desktop"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=日程管理助手
Comment=轻量日程与时间看板
Exec=$BIN
Path=$APP_DIR
Terminal=false
Categories=Office;Calendar;
StartupNotify=true
EOF
chmod +x "$DESKTOP"

echo "[4/4] 完成。"
echo "直接运行: $BIN"
echo "桌面双击: 把 $DESKTOP 复制到 ~/Desktop 后，首次可能需右键“允许启动”。"
