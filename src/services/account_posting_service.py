from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from playwright.sync_api import sync_playwright

from facebook.group_poster import post_to_group
from models.account_posting_plan import AccountPostingPlan
from models.listing_posting_task import ListingPostingTask
from models.posting_progress import PostingProgress
from models.posting_result_entry import PostingResultEntry
from models.post_result import PostResult
from services.account_session_registry import AccountSessionRegistry
from services.listing_service import ListingService
from services.post_interval import (
    MAX_POST_INTERVAL,
    MAX_ROUND_INTERVAL,
    MIN_POST_INTERVAL,
    MIN_ROUND_INTERVAL,
    wait_random_minutes,
)


ProgressCallback = Callable[[PostingProgress], None]
ResultCallback = Callable[[PostingResultEntry], None]
StopRequested = Callable[[], bool]


class AccountPostingService:
    def __init__(
        self,
        listing_service: ListingService | None = None,
        playwright_factory: Callable = sync_playwright,
        posting_function: Callable = post_to_group,
        wait_function: Callable = wait_random_minutes,
    ) -> None:
        self.listing_service = listing_service or ListingService()
        self.playwright_factory = playwright_factory
        self.posting_function = posting_function
        self.wait_function = wait_function

    def run_plan(
        self,
        session_path: Path,
        plan: AccountPostingPlan,
        progress_callback: ProgressCallback | None = None,
        result_callback: ResultCallback | None = None,
        stop_requested: StopRequested | None = None,
    ) -> list[PostingResultEntry]:
        working_plan = plan.fresh_copy()
        total = working_plan.total_attempts
        completed = 0
        attempted = 0
        failed = 0
        entries: list[PostingResultEntry] = []
        stopped = False
        should_stop = stop_requested or (lambda: False)

        def emit(
            *,
            current_group_name: str | None,
            next_group_name: str | None,
            listing_title: str | None,
            message: str,
            next_listing_title: str | None = None,
            finished: bool = False,
            was_stopped: bool = False,
        ) -> None:
            if progress_callback is not None:
                skipped = 0
                remaining = max(total - attempted, 0)
                progress_callback(
                    PostingProgress(
                        completed=completed,
                        total=total,
                        current_group_name=current_group_name,
                        next_group_name=next_group_name,
                        current_listing_title=listing_title,
                        message=message,
                        next_listing_title=next_listing_title,
                        attempted=attempted,
                        failed=failed,
                        skipped=skipped,
                        remaining=remaining,
                        finished=finished,
                        stopped=was_stopped,
                    )
                )

        with AccountSessionRegistry.exclusive(
            plan.account_name,
            session_path,
        ):
            try:
                prepared_tasks = [
                    (
                        task,
                        *self.listing_service.prepare_for_posting(
                            task.listing_id
                        ),
                    )
                    for task in working_plan.tasks
                ]

                emit(
                    current_group_name=None,
                    next_group_name=self._first_group_name(
                        working_plan.tasks[0]
                    ),
                    listing_title=working_plan.tasks[0].listing_title,
                    next_listing_title=working_plan.tasks[0].listing_title,
                    message="Kế hoạch đã sẵn sàng. Đang mở trình duyệt…",
                )

                with self.playwright_factory() as playwright:
                    context = playwright.chromium.launch_persistent_context(
                        user_data_dir=str(session_path),
                        headless=True,
                    )
                    context.grant_permissions(
                        ["clipboard-read", "clipboard-write"],
                        origin="https://www.facebook.com",
                    )
                    try:
                        page = (
                            context.pages[0]
                            if context.pages
                            else context.new_page()
                        )

                        round_number = 1
                        while self._has_active_targets(working_plan.tasks):
                            active_slots = [
                                (task, caption, images, target)
                                for task, caption, images in prepared_tasks
                                for target in task.group_targets
                                if target.active
                            ]
                            first_slot = active_slots[0]
                            emit(
                                current_group_name=None,
                                next_group_name=first_slot[0].group_name_for(
                                    first_slot[3].url
                                ),
                                listing_title=None,
                                next_listing_title=first_slot[0].listing_title,
                                message=(
                                    f"Vòng {round_number}: "
                                    f"{len(active_slots)} bài cần đăng"
                                ),
                            )

                            for slot_index, slot in enumerate(active_slots):
                                task, caption, images, target = slot
                                if should_stop():
                                    stopped = True
                                    break

                                next_slot = (
                                    active_slots[slot_index + 1]
                                    if slot_index + 1 < len(active_slots)
                                    else None
                                )
                                current_group_name = task.group_name_for(
                                    target.url
                                )
                                emit(
                                    current_group_name=current_group_name,
                                    next_group_name=(
                                        next_slot[0].group_name_for(
                                            next_slot[3].url
                                        )
                                        if next_slot is not None
                                        else None
                                    ),
                                    listing_title=task.listing_title,
                                    next_listing_title=(
                                        next_slot[0].listing_title
                                        if next_slot is not None
                                        else None
                                    ),
                                    message=(
                                        "Đang đăng lượt "
                                        f"{target.attempted_count + 1}/"
                                        f"{target.target_count} của nhóm"
                                    ),
                                )

                                result = self.posting_function(
                                    page=page,
                                    group_url=target.url,
                                    caption=caption,
                                    image_paths=images,
                                )
                                if (
                                    self._is_retryable_composer_timeout(result)
                                    and not should_stop()
                                ):
                                    emit(
                                        current_group_name=current_group_name,
                                        next_group_name=(
                                            next_slot[0].group_name_for(
                                                next_slot[3].url
                                            )
                                            if next_slot is not None
                                            else None
                                        ),
                                        listing_title=task.listing_title,
                                        next_listing_title=(
                                            next_slot[0].listing_title
                                            if next_slot is not None
                                            else None
                                        ),
                                        message=(
                                            "Chưa mở được ô viết bài. "
                                            "Đang thử lại lần cuối…"
                                        ),
                                    )
                                    result = self.posting_function(
                                        page=page,
                                        group_url=target.url,
                                        caption=caption,
                                        image_paths=images,
                                    )
                                result = self._with_configured_group_name(
                                    result,
                                    current_group_name,
                                )
                                attempted += 1
                                if result.success:
                                    target.mark_posted()
                                    completed += 1
                                    message = (
                                        "Đã đăng xong "
                                        f"(lượt {target.attempted_count}/"
                                        f"{target.target_count})"
                                    )
                                else:
                                    target.mark_attempt_failed()
                                    failed += 1
                                    message = (
                                        "Đăng không thành công "
                                        f"(lượt {target.attempted_count}/"
                                        f"{target.target_count}): "
                                        f"{result.error or 'Không có thông tin lỗi'}"
                                    )

                                entry = PostingResultEntry(
                                    account_name=plan.account_name,
                                    listing_id=task.listing_id,
                                    listing_title=task.listing_title,
                                    result=result,
                                )
                                entries.append(entry)
                                if result_callback is not None:
                                    result_callback(entry)

                                next_active = (
                                    next_slot
                                    if next_slot is not None
                                    else self._first_active_slot(prepared_tasks)
                                )
                                emit(
                                    current_group_name=current_group_name,
                                    next_group_name=(
                                        next_active[0].group_name_for(
                                            next_active[3].url
                                        )
                                        if next_active is not None
                                        else None
                                    ),
                                    listing_title=task.listing_title,
                                    next_listing_title=(
                                        next_active[0].listing_title
                                        if next_active is not None
                                        else None
                                    ),
                                    message=message,
                                )

                                if should_stop():
                                    stopped = True
                                    break

                                if next_slot is not None:
                                    next_task, _, _, next_target = next_slot

                                    def emit_post_wait(
                                        text: str,
                                        current_task=task,
                                        current_target=target,
                                        following_task=next_task,
                                        following_target=next_target,
                                    ) -> None:
                                        emit(
                                            current_group_name=(
                                                current_task.group_name_for(
                                                    current_target.url
                                                )
                                            ),
                                            next_group_name=(
                                                following_task.group_name_for(
                                                    following_target.url
                                                )
                                            ),
                                            listing_title=(
                                                current_task.listing_title
                                            ),
                                            next_listing_title=(
                                                following_task.listing_title
                                            ),
                                            message=text,
                                        )

                                    self.wait_function(
                                        MIN_POST_INTERVAL,
                                        MAX_POST_INTERVAL,
                                        "Chờ trước bài tiếp theo",
                                        progress_callback=emit_post_wait,
                                        stop_requested=should_stop,
                                    )
                                    if should_stop():
                                        stopped = True
                                        break

                            if stopped:
                                break

                            next_round_slot = self._first_active_slot(
                                prepared_tasks
                            )
                            if next_round_slot is not None:
                                next_task, _, _, next_target = next_round_slot

                                def emit_round_wait(
                                    text: str,
                                    following_task=next_task,
                                    following_target=next_target,
                                ) -> None:
                                    emit(
                                        current_group_name=None,
                                        next_group_name=(
                                            following_task.group_name_for(
                                                following_target.url
                                            )
                                        ),
                                        listing_title=None,
                                        next_listing_title=(
                                            following_task.listing_title
                                        ),
                                        message=text,
                                    )

                                emit(
                                    current_group_name=None,
                                    next_group_name=next_task.group_name_for(
                                        next_target.url
                                    ),
                                    listing_title=None,
                                    next_listing_title=next_task.listing_title,
                                    message=(
                                        f"Đã xong vòng {round_number}. "
                                        "Chờ trước khi bắt đầu vòng tiếp theo."
                                    ),
                                )
                                self.wait_function(
                                    MIN_ROUND_INTERVAL,
                                    MAX_ROUND_INTERVAL,
                                    "Chờ trước vòng tiếp theo",
                                    progress_callback=emit_round_wait,
                                    stop_requested=should_stop,
                                )
                                if should_stop():
                                    stopped = True
                                    break
                            round_number += 1
                    finally:
                        try:
                            context.close()
                        except Exception:
                            if not (stopped or should_stop()):
                                raise

                emit(
                    current_group_name=None,
                    next_group_name=None,
                    listing_title=None,
                    message=(
                        f"Đã dừng theo yêu cầu: {attempted}/{total} lượt đã xử lý"
                        if stopped
                        else (
                            f"Đã hoàn tất: {completed}/{total} lượt đăng thành công"
                            + (
                                f" · {total - attempted} lượt chưa thực hiện"
                                if attempted < total
                                else ""
                            )
                        )
                    ),
                    finished=True,
                    was_stopped=stopped,
                )
                return entries
            except Exception as error:
                emit(
                    current_group_name=None,
                    next_group_name=None,
                    listing_title=None,
                    message=f"Tiến trình đã dừng: {error}",
                    finished=True,
                )
                raise

    @staticmethod
    def _first_group_name(
        task: ListingPostingTask | None,
    ) -> str | None:
        if task is None or not task.group_targets:
            return None
        return task.group_name_for(task.group_targets[0].url)

    @staticmethod
    def _is_retryable_composer_timeout(result: PostResult) -> bool:
        return bool(
            not result.success
            and result.error
            and "Locator.press_sequentially" in result.error
            and "Timeout" in result.error
        )

    @staticmethod
    def _with_configured_group_name(
        result: PostResult,
        configured_name: str,
    ) -> PostResult:
        fetched_name = (result.group_name or "").strip()
        if fetched_name and fetched_name.casefold() not in {
            "unknown",
            "unknown group",
        }:
            return result
        return replace(result, group_name=configured_name)

    @staticmethod
    def _has_active_targets(tasks: list[ListingPostingTask]) -> bool:
        return any(
            target.active
            for task in tasks
            for target in task.group_targets
        )

    @staticmethod
    def _first_active_slot(prepared_tasks):
        return next(
            (
                (task, caption, images, target)
                for task, caption, images in prepared_tasks
                for target in task.group_targets
                if target.active
            ),
            None,
        )


def post_account_plan(
    session_path: Path,
    plan: AccountPostingPlan,
    progress_callback: ProgressCallback | None = None,
) -> list[PostResult]:
    entries = AccountPostingService().run_plan(
        session_path=session_path,
        plan=plan,
        progress_callback=progress_callback,
    )
    return [entry.result for entry in entries]
