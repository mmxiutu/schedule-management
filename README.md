# 日程管理助手

面向个人日常时间管理的轻量桌面应用（记录 / 提醒 / 推进 / 沉淀）。  
同一套源码运行于 **Windows 10/11** 与 **树莓派 4B 桌面**。界面使用标准库 **tkinter**（冷启动快、打包体积小），数据保存在 CouchDB。

数据库地址、库名、账号密码，以及和风天气凭据，都只放本机配置（不要写进源码或提交 Git）。复制仓库根目录的示例文件并填入真实值：

- `connection.example.json` → `connection.json`（`url` / `user` / `password` / `db`）
- `qweather.example.json` → `qweather.json`（API Host 与 JWT）

保存位置：

- Windows：`%APPDATA%\ScheduleAssistant\`
- Linux / 树莓派：`~/.config/schedule-assistant/`

未配置 CouchDB 时可在应用顶部「设置」里填写并测试连接。未配置和风天气时，待机页显示「天气暂不可用」。

## Windows 运行

需要 Python 3.11+（自带 tkinter）。

```powershell
cd d:\Workspace\raspberry
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
schedule-assistant
```

或：

```powershell
python -m schedule_assistant.main
```

打包成可双击运行的程序：双击 `build_win_gui.bat`，生成 `dist\ScheduleAssistant\ScheduleAssistant.exe`。

## 树莓派 4B（Raspberry Pi OS 桌面）

32-bit / 64-bit 均可（不再依赖 PySide6）。

**方式 A：直接跑 Python（开发、日常推荐）**

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-tk python3-pil python3-pil.imagetk fonts-noto-cjk
cd ~/raspberry
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
schedule-assistant
```

**方式 B：打成可执行文件（类似 Windows 绿色版）**

必须在树莓派本机打包，不能用 Windows 编出来的 exe。系统还需 tk/PIL：

```bash
sudo apt install -y python3-venv python3-pip python3-tk python3-pil python3-pil.imagetk
chmod +x build_linux.sh
./build_linux.sh
./dist/ScheduleAssistant/ScheduleAssistant
```

打包后目录里有 `ScheduleAssistant` 二进制，以及 `日程管理助手.desktop`。把 `.desktop` 拷到桌面后，首次可能要右键「允许启动」才能双击。

无系统托盘时，到期提醒会尝试弹出通知；失败则显示主窗口。

## 测试

```bash
pytest
```

## 界面约定

顶部仅四钮：新建任务、周期任务、设置、待机。  
左侧仅四视图：月历、今日、看板、记事本。  
看板任务：双击编辑，右键可改状态。
