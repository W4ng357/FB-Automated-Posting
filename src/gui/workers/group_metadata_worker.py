import traceback

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot

from facebook.group_metadata import (
    GroupMetadata,
    fetch_group_metadata_for_account,
)


class GroupMetadataWorker(QObject):
    started = Signal()
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        account_name: str,
        group_url: str,
        fetch_function: Callable[
            [str, str], GroupMetadata
        ] = fetch_group_metadata_for_account,
    ) -> None:
        super().__init__()
        self.account_name = account_name
        self.group_url = group_url
        self.fetch_function = fetch_function

    @Slot()
    def run(self) -> None:
        self.started.emit()
        try:
            metadata = self.fetch_function(
                self.account_name,
                self.group_url,
            )
        except Exception as error:
            traceback.print_exc()
            self.error.emit(str(error))
            return
        self.finished.emit(metadata)

