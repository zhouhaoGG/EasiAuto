# EasiAuto AI Agent Instructions

帮助 AI Agent 理解本仓库，减少重复探索，快速定位关键目录。

## 项目概述

- Windows 桌面应用，使用 `PySide6` + `qfluentwidgets` (Fluent Design)
- 为**希沃白板 (EasiNote)**提供自动登录，及通过 ClassIsland 自动触发登录任务
- 深度架构分析 → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 项目结构速览

```
main.py                  # 入口：调用 Launcher
src/EasiAuto/
  launcher.py            # 启动、参数解析、单例、命令分发
  common/                # 配置(config)、档案(profile)、常量(consts)、加密(secret_store)
    runtime/             # 异常处理、IPC、单例锁
  core/
    automator/           # 四种登录方案 (FIXED/CV/UIA/INJECT) + AutomationManager
    binding_sync.py      # ClassIsland 绑定同步
  integrations/          # ClassIsland 配置管理
  view/                  # UI (MSFluentWindow, 5 个页面)
data/                    # 运行时数据 (config.json, profile.json, logs/)
resources/               # 图片资源 (EasiNoteUI/, icons/)
tools/                   # 构建脚本、公告管理、发布脚本
vendors/                 # Snoop 注入器 (仅 FULL 版使用)
build/                   # Nuitka 编译输出
```

## 编码规范

- **语言**：注释、日志、UI 文本一律使用**简体中文**
- **Docstring**：简单函数不需要；复杂函数需说明参数、返回值、可能异常
- **标记**：`TODO` 标记待完成，`NOTE` 标记需特别注意
