import subprocess
import time
import win32api
import win32con
import win32gui
from pathlib import Path
import os

from loguru import logger

from EasiAuto.common.config import config
from EasiAuto.common.runtime import capture_handled_exception
from EasiAuto.common.utils import get_window_by_title, switch_window

from .base import BaseAutomator, LoginCancelled


class BanyouAutomator(BaseAutomator):
    """班级优化大师自动登录器"""

    # 启动路径
    start_paths = [
        r"C:\Program Files (x86)\Seewo\EasiCare\EasiCare\EasiCare.exe",
        r"D:\Program Files (x86)\Seewo\EasiCare\EasiCare\EasiCare.exe"]
    
    start_path = ''
    for path in start_paths:
        if os.path.exists(path):
            start_path = path
            break

    
    # UV坐标配置（相对于窗口）
    COORDINATES = {
        "click_1": (0.699079, 0.204487),   # 点击账号输入框
        "click_2": (0.551784, 0.437446),   # 点击账号输入框确认
        "click_3": (0.555811, 0.511648),   # 点击密码输入框
        "click_4": (0.507480, 0.729077),   # 点击登录按钮
        "click_5": (0.644419, 0.611734),   # 点击确认/跳过
    }

    def _uv_to_screen(self, hwnd: int, uv: tuple[float, float]) -> tuple[int, int]:
        """将UV相对坐标转换为屏幕绝对坐标"""
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        x = int(left + uv[0] * width)
        y = int(top + uv[1] * height)
        return x, y

    def _mouse_click(self, x: int, y: int):
        """鼠标点击操作"""
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        time.sleep(0.02)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
        time.sleep(0.1)

    def _input_text(self, text: str):
        """输入文本（模拟Ctrl+V粘贴）"""
        import pyperclip
        
        logger.debug(f"输入: {text}")
        pyperclip.copy(text)
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord('V'), 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)

    def _find_window(self) -> int | None:
        """查找班级优化大师窗口"""
        hwnds = get_window_by_title("班级优化大师")
        if hwnds:
            return hwnds[0]
        return None

    def _start_app_if_needed(self) -> int | None:
        """如果应用未运行则启动"""
        hwnd = self._find_window()
        if hwnd:
            logger.debug("已找到班级优化大师窗口")
            return hwnd
        
        # 未找到则尝试启动
        start_path = Path(self.start_path)
        if start_path.exists():
            logger.info("启动班级优化大师...")
            subprocess.Popen([str(start_path)])
            
            # 启动后先等待8秒让页面完全加载
            self.update_progress("等待页面加载完成（8秒）...")
            for _ in range(16):  # 8秒 = 16 * 0.5秒
                self.check_interruption()
                time.sleep(0.5)
            logger.success("页面加载完成")
            
            # 页面加载完成后，查找窗口（最多3次尝试）
            self.update_progress("查找班级优化大师窗口")
            for attempt in range(3):
                self.check_interruption()
                hwnd = self._find_window()
                if hwnd:
                    logger.success(f"成功获取窗口句柄（尝试 {attempt + 1}/3）")
                    return hwnd
                if attempt < 2:  # 前两次失败才等待
                    logger.warning(f"第 {attempt + 1} 次尝试未找到窗口，等待1秒后重试...")
                    time.sleep(1)
            
            logger.error("未能获取到有效的窗口句柄")
            return None
        else:
            logger.error(f"未找到启动文件: {self.start_path}")
            return None

    def login(self):
        """执行班级优化大师自动登录"""
        # 查找或启动窗口（_start_app_if_needed内部已经更新了进度）
        hwnd = self._start_app_if_needed()
        
        if not hwnd:
            raise RuntimeError("未找到班级优化大师窗口，无法继续")
        
        # 激活窗口
        self.update_progress("激活窗口")
        switch_window(hwnd)
        time.sleep(0.5)
        
        # 点击1 - 打开账号输入
        self.check_interruption()
        self.update_progress("打开账号输入")
        x, y = self._uv_to_screen(hwnd, self.COORDINATES["click_1"])
        self._mouse_click(x, y)
        time.sleep(0.3)
        
        # 点击2 - 聚焦账号输入框
        self.check_interruption()
        self.update_progress("聚焦账号输入框")
        x, y = self._uv_to_screen(hwnd, self.COORDINATES["click_2"])
        self._mouse_click(x, y)
        time.sleep(0.3)
        
        # 输入账号
        self.check_interruption()
        self.update_progress("输入账号")
        self._input_text(self.account)
        time.sleep(0.3)
        
        # 点击3 - 聚焦密码输入框
        self.check_interruption()
        self.update_progress("聚焦密码输入框")
        x, y = self._uv_to_screen(hwnd, self.COORDINATES["click_3"])
        self._mouse_click(x, y)
        time.sleep(0.3)
        
        # 输入密码
        self.check_interruption()
        self.update_progress("输入密码")
        self._input_text(self.password)
        time.sleep(0.3)
        
        # 点击4 - 点击登录按钮
        self.check_interruption()
        self.update_progress("点击登录按钮")
        x, y = self._uv_to_screen(hwnd, self.COORDINATES["click_4"])
        self._mouse_click(x, y)
        time.sleep(0.5)
        
        # 点击5 - 确认/跳过
        self.check_interruption()
        self.update_progress("完成登录")
        x, y = self._uv_to_screen(hwnd, self.COORDINATES["click_5"])
        self._mouse_click(x, y)
        time.sleep(0.3)

    def run(self):
        """班级优化大师完整登录流程（重写以适配特殊需求）"""
        
        # 统计数据
        import time as time_module
        time_start = time_module.monotonic()
        config.Statistics.LoginCounts += 1
        if config.Statistics.LoginCountsPerAccount.get(self.account) is None:
            config.Statistics.LoginCountsPerAccount[self.account] = 0
        config.Statistics.LoginCountsPerAccount[self.account] += 1

        retries = 0
        while True:
            try:
                self.check_interruption()

                self.update_progress("开始登录")
                self.update_task("启动班级优化大师")

                self.update_task("正在自动登录")
                self.login()

                self.update_progress("登录完成")
                self.update_task("完成")

                config.Statistics.LoginSuccessCounts += 1
                self.successed.emit()
                break
            except LoginCancelled:
                config.Statistics.LoginInterruptCounts += 1
                self.interrupted.emit()
                break
            except Exception as e:
                retries += 1

                if retries <= config.App.MaxRetries:
                    logger.error(f"登录过程中发生错误\n{type(e).__name__}: {e}")
                    logger.warning(f"将在2s后重试 (尝试 {retries}/{config.App.MaxRetries}) ")
                    time.sleep(2)
                else:
                    logger.critical(f"{retries}次尝试均登录失败\n{type(e).__name__}: {e}")
                    capture_handled_exception(
                        e,
                        source="automator",
                        extra_context={
                            "retries": f"{retries}/{config.App.MaxRetries}",
                            "automator": self.__class__.__name__,
                            "current_task": self._prev_task,
                            "current_progress": self._prev_progress,
                        },
                    )
                    self.failed.emit(str(e))
                    break

        elapsed = time_module.monotonic() - time_start
        logger.info(f"登录流程耗时: {elapsed:.2f}秒")
        config.Statistics.TotalLoginTime += elapsed
        config.Statistics.MaxLoginTime = max(config.Statistics.MaxLoginTime, elapsed)
