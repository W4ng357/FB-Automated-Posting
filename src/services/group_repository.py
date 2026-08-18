import json
import re
import threading

from dataclasses import asdict
from pathlib import Path

from models.saved_group import SavedGroup


from app_paths import GROUPS_FILE

DEFAULT_GROUPS_FILE = GROUPS_FILE
_GROUPS_LOCK = threading.RLock()


class GroupRepository:
    def __init__(
        self,
        file_path: Path = DEFAULT_GROUPS_FILE,
    ) -> None:
        self.file_path = file_path

    def get_all(self) -> list[SavedGroup]:
        with _GROUPS_LOCK:
            return self._get_all_unlocked()

    def _get_all_unlocked(self) -> list[SavedGroup]:
        if not self.file_path.is_file():
            return []

        raw_data = self.file_path.read_text(
            encoding="utf-8"
        ).strip()
        if not raw_data:
            return []

        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Tệp danh sách nhóm có JSON không hợp lệ: {self.file_path}"
            ) from error

        if not isinstance(data, list) or not all(
            isinstance(item, dict) for item in data
        ):
            raise ValueError(
                f"Dữ liệu nhóm phải là một danh sách đối tượng JSON: "
                f"{self.file_path}"
            )

        return [SavedGroup(**item) for item in data]

    def get_by_id(self, group_id: str) -> SavedGroup | None:
        return next(
            (
                group
                for group in self.get_all()
                if group.id == group_id
            ),
            None,
        )

    def create(
        self,
        url: str,
        name: str,
        image_path: str | None = None,
        enabled: bool = True,
    ) -> SavedGroup:
        with _GROUPS_LOCK:
            groups = self._get_all_unlocked()
            if any(group.url == url for group in groups):
                raise ValueError(f"Nhóm có URL này đã được lưu: {url}")

            group = SavedGroup(
                id=self._generate_next_id(groups),
                url=url,
                name=name,
                image_path=image_path,
                enabled=enabled,
            )
            groups.append(group)
            self._save(groups)
            return group

    def update(
        self,
        group_id: str,
        **changes: object,
    ) -> SavedGroup:
        with _GROUPS_LOCK:
            groups = self._get_all_unlocked()

            for index, group in enumerate(groups):
                if group.id != group_id:
                    continue

                data = asdict(group)
                if "id" in changes:
                    raise ValueError("Không thể thay đổi mã nhóm.")

                invalid_fields = set(changes) - set(data)
                if invalid_fields:
                    raise ValueError(
                        f"Trường dữ liệu không hợp lệ: {invalid_fields}"
                    )

                next_url = str(changes.get("url", group.url))
                if any(
                    other.id != group_id
                    and other.url == next_url
                    for other in groups
                ):
                    raise ValueError(
                        f"Nhóm có URL này đã được lưu: {next_url}"
                    )

                data.update(changes)
                updated = SavedGroup(**data)
                groups[index] = updated
                self._save(groups)
                return updated

            raise KeyError(f"Không tìm thấy nhóm {group_id}.")

    def delete(self, group_id: str) -> bool:
        with _GROUPS_LOCK:
            groups = self._get_all_unlocked()
            updated = [
                group for group in groups if group.id != group_id
            ]
            if len(updated) == len(groups):
                return False
            self._save(updated)
            return True

    def _save(self, groups: list[SavedGroup]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(
            [asdict(group) for group in groups],
            ensure_ascii=False,
            indent=2,
        )
        temp_file = self.file_path.with_suffix(".tmp")
        temp_file.write_text(content, encoding="utf-8")
        temp_file.replace(self.file_path)

    @staticmethod
    def _generate_next_id(groups: list[SavedGroup]) -> str:
        highest_id = 0
        for group in groups:
            match = re.fullmatch(r"G(\d+)", group.id)
            if match:
                highest_id = max(highest_id, int(match.group(1)))
        return f"G{highest_id + 1:03d}"
