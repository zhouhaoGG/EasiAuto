# EasiAuto AI Agent Instructions

## 目标

帮助 AI 代码代理快速理解并贡献本仓库。

## 项目概述

- 这是一个面向 Windows 的桌面应用程序，使用 `PySide6` 和 `qfluentwidget` 构建 UI。
- 主要功能是为希沃白板提供自动登录，及自动触发登录任务。
- 入口文件：`main.py`。
- 核心代码位于 `src/EasiAuto/`。

## 主要目录

- `src/EasiAuto/common/`: 通用功能和工具函数。
  - `config.py`: 基于 Pydantic 的分层配置系统，支持自动保存和类型验证。
  - `runtime/exception_handler.py`: 集成 Sentry 遥测和日志系统。
  - `runtime/ipc.py`: IPC 单例服务，确保仅一个实例运行。
- `src/EasiAuto/core/`: 自动化核心功能。
  - `automator/`: 多种登录方案实现（固定位置、图像识别、自动定位、进程注入）。
  - `binding_sync.py`: ClassIsland 自动化任务绑定与同步逻辑。
- `src/EasiAuto/view/`: UI 界面、页面、组件和窗口逻辑。
  - `main_window.py`: 主窗口与页面导航。
  - `pages/`: 各功能页面（设置、自动化、绑定、更新等）。
  - `components/`: 可复用 UI 组件（设置卡、弹窗、横幅等）。
- `tools/build.py`: 通过 `Nuitka` 打包生成 `full` / `lite` 可执行文件。
- `tools/release.py`: 发行脚本。
- `pyproject.toml`: 依赖、Python 版本、`ruff` 配置和 `uv` 运行环境。
- `README.md`: 产品简介、使用说明和下载说明。

## 编码规范和要求

- 回答用户和编写注释、日志、UI文本 时，总是使用简体中文。
- 对于功能简单或容易从函数名推断出作用的函数，不需要 docstring。
- 对于较为复杂或难以从函数名推断出作用的函数，给出 docstring。必要时，在整体性的步骤处加上注释辅助说明。
- 如果存在待完善的功能，使用 TODO 注释标记。
- 如果存在需要特别注意的代码，使用 NOTE 注释标记。

## 开发时注意点

- 这是一个 GUI 应用，许多行为依赖 Windows UI、进程和桌面环境。
- 仓库当前没有专门的测试目录，建议优先保持代码清晰、稳定和可读。
