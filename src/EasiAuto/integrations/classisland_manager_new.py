import json
import shlex
from copy import deepcopy
from pathlib import Path
from typing import cast

import pywintypes
import win32api
import win32con
import win32event
from loguru import logger
from pydantic import AliasPath, BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from PySide6.QtCore import QObject, Signal

from EasiAuto.common.consts import EA_PREFIX


class CiSubject(BaseModel):
    id: str
    name: str


class CiAutomation(BaseModel):
    """基本 ClassIsland 自动化"""

    model_config = ConfigDict(validate_by_name=True)
    _raw_data: dict = PrivateAttr(default_factory=dict)

    guid: str = Field(validation_alias=AliasPath("ActionSet", "Guid"))
    name: str = Field(validation_alias=AliasPath("ActionSet", "Name"))

    @model_validator(mode="before")
    @classmethod
    def capture_raw_data(cls, data: dict) -> dict:
        cls._raw_data = data
        return data

    def dump_ci_dict(self) -> dict:
        return self._raw_data

    @property
    def is_managed(self) -> bool:
        return self.name.startswith(EA_PREFIX)


class ManagedCiAutomation(CiAutomation):
    """受管理的 ClassIsland 自动化"""

    is_enabled: bool = Field(validation_alias=AliasPath("ActionSet", "IsEnabled"))
    subject_id: str = Field(validation_alias=AliasPath("Ruleset", "Groups", 0, "Rules", 0, "Settings", "SubjectId"))
    pretime: int = Field(validation_alias=AliasPath("Triggers", 0, "Settings", "TimeSeconds"))
    args: str = Field(validation_alias=AliasPath("ActionSet", "Actions", 0, "Settings", "Args"))

    def dump_ci_dict(self) -> dict:
        result = deepcopy(self._raw_data)

        result["ActionSet"]["Guid"] = self.guid
        result["ActionSet"]["Name"] = self.name
        result["ActionSet"]["IsEnabled"] = self.is_enabled
        result["ActionSet"]["Actions"][0]["Settings"]["Args"] = self.args
        result["Ruleset"]["Groups"][0]["Rules"][0]["Settings"]["SubjectId"] = self.subject_id
        result["Triggers"][0]["Settings"]["TimeSeconds"] = self.pretime

        return result

    def get_arg(self, flag: str) -> str | None:
        try:
            tokens = shlex.split(self.args)
            if flag in tokens:
                return tokens[tokens.index(flag) + 1]
        except (ValueError, IndexError):
            pass
        return None

    @property
    def account(self) -> str | None:
        return self.get_arg("account")

    @property
    def password(self) -> str | None:
        return self.get_arg("password")

    @property
    def id(self) -> str | None:
        return self.get_arg("id")


class ClassIslandManager(QObject):
    automationChanged = Signal()

    def __init__(self, exe_path: Path | str):
        super().__init__()
        self.exe_path = Path(exe_path)
        if not self.exe_path.exists():
            raise FileNotFoundError(f"ClassIsland 程序不存在: {exe_path}")

        self.is_v2 = self._check_is_v2()
        self.ci_settings: dict = {}
        self.ci_profile: dict = {}
        self.ci_automations_raw: list[dict] = []

        self.unmanaged_automations: list[dict] = []
        self.managed_automations: list[ManagedCiAutomation] = []

        self.reload()

    def _check_is_v2(self) -> bool:
        try:
            info = win32api.GetFileVersionInfo(str(self.exe_path), "\\")
            ms = info["FileVersionMS"]
            return (ms >> 16) >= 2
        except Exception:
            return False

    @property
    def data_dir(self) -> Path:
        return self.exe_path.parent / "data" if self.is_v2 else self.exe_path.parent

    @property
    def settings_path(self) -> Path:
        return self.data_dir / "Settings.json"

    @property
    def current_profile_path(self) -> Path:
        name = self.ci_settings.get("SelectedProfile", "Default.json")
        return self.data_dir / "Profiles" / name

    @property
    def current_automation_path(self) -> Path:
        name = self.ci_settings.get("CurrentAutomationConfig", "Default")
        return self.data_dir / "Config" / "Automations" / f"{name}.json"

    def reload(self):
        """重新加载所有配置"""
        try:
            self.ci_settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
            self.ci_profile = json.loads(self.current_profile_path.read_text(encoding="utf-8"))
            self.ci_automations_raw = json.loads(self.current_automation_path.read_text(encoding="utf-8"))

            self._resolve_automations()
        except Exception as e:
            logger.error(f"重新加载 ClassIsland 配置时出错: {e}")

    def _resolve_automations(self) -> None:
        """将原始自动化按照受管理状态分离"""
        self.unmanaged_automations = []
        self.managed_automations = []
        for raw in self.ci_automations_raw:
            if CiAutomation(**raw).is_managed:
                self.managed_automations.append(ManagedCiAutomation(**raw))
            else:
                self.unmanaged_automations.append(raw)

    def get_automations(self) -> list[ManagedCiAutomation]:
        return self.managed_automations

    def save_automations(self, automations: list[ManagedCiAutomation]) -> bool:
        """保存自动化至 ClassIsland"""

        try:
            output = self.unmanaged_automations
            for auto in automations:
                output.append(auto.dump_ci_dict())

            content = json.dumps(output)
            self.current_automation_path.write_text(content, encoding="utf-8")

            self.reload()
            return True
        except Exception as e:
            logger.error(f"保存自动化至 ClassIsland 时出错: {e}")
            return False

    def get_subjects(self) -> list[CiSubject]:
        subjects = self.ci_profile.get("Subjects", {})
        return [CiSubject(id=k, name=v.get("Name", "Unknown")) for k, v in subjects.items()]

    @property
    def is_running(self) -> bool:
        """使用互斥锁检查 ClassIsland 的运行状态"""
        mutex = "Global\\ClassIsland.Lock" if self.is_v2 else "ClassIsland.Lock"
        try:
            h = win32event.OpenMutex(win32con.SYNCHRONIZE, False, mutex)
            if h:
                win32api.CloseHandle(h)
                return True
        except pywintypes.error:
            pass
        return False


class _ClassIslandManagerProxy:
    """ClassIslandManager 代理，以便动态初始化单例"""

    def __init__(self):
        self._impl = None

    def initialize(self, path: Path):
        self._impl = ClassIslandManager(path)

    def __getattr__(self, item):
        return getattr(self._impl, item)

    def __bool__(self):
        return self._impl is not None


classisland_manager = cast(ClassIslandManager, _ClassIslandManagerProxy())
