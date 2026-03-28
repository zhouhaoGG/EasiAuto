from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from loguru import logger

from EasiAuto.common.config import config
from EasiAuto.common.profile import BindingItem, EasiAutomation, Profile, SubjectRef
from EasiAuto.integrations.classisland_manager import (
    CiSubject,
    ManagedCiAutomation,
)
from EasiAuto.integrations.classisland_manager import (
    classisland_manager as ci_manager,
)


class BindingSyncBackendBase(ABC):
    provider: str

    def __init__(self) -> None:
        self.last_errors: list[str] = []

    @abstractmethod
    def list_subjects(self) -> list[SubjectRef]:
        raise NotImplementedError

    @abstractmethod
    def sync(self, profile_data: Profile) -> bool:
        raise NotImplementedError

    def _set_errors(self, errors: list[str]) -> bool:
        self.last_errors = errors.copy()
        if errors:
            logger.warning(f"绑定同步失败: {'；'.join(errors)}")
            return False
        return True


@dataclass(slots=True)
class SyncTarget:
    binding: BindingItem
    subject_id: str
    automation: EasiAutomation
    subject: CiSubject


class ClassIslandBindingBackend(BindingSyncBackendBase):
    """ClassIsland 绑定同步后端实现"""

    provider = "classisland"

    def __init__(self) -> None:
        super().__init__()

    def list_subjects(self, reload: bool = False) -> list[SubjectRef]:
        """列出 ClassIsland 中的所有科目"""

        if not ci_manager:
            return []

        if reload:
            ci_manager.reload()

        return [SubjectRef(name=item.name, provider=self.provider, id=item.id) for item in ci_manager.get_subjects()]

    def sync(self, profile_data: Profile) -> bool:
        """执行与 ClassIsland 的同步操作"""
        errors: list[str] = []

        if not ci_manager:
            errors.append("ClassIsland 管理器未初始化")
            return self._set_errors(errors)

        ci_manager.reload()

        automations = list(ci_manager.get_automations())
        automation_index = {auto.guid: auto for auto in automations}
        subject_index: dict[str, CiSubject] = {item.id: item for item in ci_manager.get_subjects()}
        all_bindings = profile_data.list_bindings()

        # 规范化并过滤待同步绑定
        desired_bindings = self._build_desired_bindings(profile_data, all_bindings, subject_index)

        # 处理现有自动化配置
        managed_by_subject: dict[str, ManagedCiAutomation] = {}
        for item in automations:
            managed_by_subject[item.subject_id] = item

        used_guids: set[str] = set()
        desired_automations: list[ManagedCiAutomation] = []

        # 按解析结果构建最终自动化配置
        for target in desired_bindings:
            existing = self._resolve_existing(
                binding=target.binding,
                subject_id=target.subject_id,
                automation_index=automation_index,
                managed_by_subject=managed_by_subject,
                used_guids=used_guids,
            )

            guid = existing.guid if existing else str(uuid.uuid4())
            used_guids.add(guid)
            pretime = existing.pretime if existing else config.ClassIsland.DefaultPreTime

            built = ManagedCiAutomation(
                guid=guid,
                name=target.automation.get_automation_name(target.subject.name),
                is_enabled=target.automation.enabled,
                subject_id=target.subject_id,
                pretime=pretime,
                args=f"login --id {target.automation.id}",
            )

            # 更新绑定关系
            target.binding.id = guid
            desired_automations.append(built)

        if not ci_manager.save_automations(desired_automations):
            errors.append("保存 ClassIsland 自动化配置失败")

        return self._set_errors(errors)

    def _resolve_existing(
        self,
        binding: BindingItem,
        subject_id: str,
        automation_index: dict[str, ManagedCiAutomation],
        managed_by_subject: dict[str, ManagedCiAutomation],
        used_guids: set[str],
    ) -> ManagedCiAutomation | None:
        if binding_id := binding.id:
            if binding_id in used_guids:
                return None
            return automation_index.get(binding_id)

        if (existing := managed_by_subject.get(subject_id)) and existing.guid not in used_guids:
            return existing

        return None

    def _build_desired_bindings(
        self,
        profile_data: Profile,
        bindings: list[BindingItem],
        subject_index: dict[str, CiSubject],
    ) -> list[SyncTarget]:
        """构建可同步绑定列表（保持输入顺序，重复科目仅保留首条）"""
        desired: list[SyncTarget] = []
        seen_subject_ids: set[str] = set()

        for binding in bindings:
            if binding.subject.provider != self.provider:
                continue

            subject_id = self._resolve_subject_id(binding, subject_index)
            if subject_id is None:
                continue
            if subject_id in seen_subject_ids:
                continue
            subject = subject_index.get(subject_id)
            if subject is None:
                continue

            automation = profile_data.get_automation(binding.automation_id)
            if automation is None:
                continue
            if automation.account.strip() == "" or automation.password.strip() == "":
                continue

            seen_subject_ids.add(subject_id)
            desired.append(
                SyncTarget(
                    binding=binding,
                    subject_id=subject_id,
                    automation=automation,
                    subject=subject,
                )
            )

        return desired

    @staticmethod
    def _resolve_subject_id(binding: BindingItem, subject_map: dict[str, CiSubject]) -> str | None:
        """解析科目 ID"""
        subject = binding.subject

        if subject.id and subject.id in subject_map:
            return subject.id

        return None
