# Product

<!-- impeccable:product-schema 1 -->

## Platform

adaptive

> Assumption: “adaptive” here means one cross-platform Qt desktop application
> that must remain usable across desktop display sizes and operating systems;
> this is not a mobile product.

## Users

Primary users are Vietnamese rental-listing operators who prepare property
content and publish it to multiple Facebook groups from several saved Facebook
accounts. They work from a desktop, revisit the same listings and groups, and
need to see what every account is doing without losing control of a browser
profile.

> Assumption: the first release is operated by one person on one local machine;
> multi-user permissions and cloud collaboration are deliberately out of scope.

## Product Purpose

FB-Automated-Posting keeps rental metadata, images, reusable Facebook groups,
Facebook account identities, saved browser sessions, posting queues, execution
progress, and post results in one local desktop tool. Success means an operator
can add and recognize accounts by Facebook name/avatar, configure several
account plans, run different accounts concurrently, and understand each result
without manually rebuilding the same posting inputs.

## Positioning

The product orchestrates the same tested Playwright posting path for both CLI
and GUI while keeping each Facebook account in its own persistent Chromium
profile. It combines reusable local content and group libraries with explicit
per-account queues rather than treating every post as a disposable command.

## Operating Context

- The application is a resizable PySide6 / Qt Widgets desktop tool.
- Metadata is stored as local JSON; listing images and cached account avatars
  live beneath the project data directory.
- Facebook sessions are persistent Chromium profiles beneath
  `browser_sessions/`.
- Operators may prepare content in the GUI while different account workers are
  posting in the background.
- The CLI remains a supported entry point and shares backend services with the
  GUI.
- User-facing application language is Vietnamese.

## Capabilities and Constraints

- Listing CRUD, image import, folder-based image staging, caption generation,
  saved-group CRUD, metadata refresh, account posting plans, structured
  progress, and post results are core capabilities.
- Account management supports adding an isolated Chromium profile, completing
  Facebook login in that browser, reading the profile name/avatar, setting an
  optional local alias, re-syncing the profile, and deleting the account with
  its local session and cached avatar after confirmation.
- A newly added account receives a stable local ID (`account-NNN`). Syncing a
  Facebook name/avatar or changing the local alias never renames that ID or its
  Chromium profile directory.
- Facebook passwords and verification codes are entered only in Chromium and
  are never requested or persisted by the Qt form. The tool stores the browser
  session, a profile URL, display name, optional alias, and cached avatar.
- Existing session folders remain usable without migration: the account
  service merges them into the account list, retains the folder name as the
  stable legacy ID and temporary display identity, and lets the operator sync
  or add an alias later.
- Account identity is shown as alias, then synced Facebook name, then stable ID.
  Cached Facebook avatars appear where available; a readable first-letter
  fallback is used when no avatar has been cached.
- Account state is explicit in text. Management distinguishes “Chưa đăng nhập”,
  “Chưa đồng bộ”, and “Đã đồng bộ”; posting separately reports ready, running,
  waiting-to-stop, stopped, completed, and error states.
- The posting workspace uses a persistent vertical account rail. Selecting an
  account changes only the workspace on the right; account status remains
  visible in the rail and the page itself never gains a posting-content
  scrollbar at the 1120×720 minimum window size.
- A per-account plan dialog configures multiple rooms in one pass. The left
  column selects rooms and shows their local image and room facts; the right
  column stores an independent group/count map for the active room and can set
  one count across all checked groups.
- The user-facing content library is named “Phòng”; the persisted Python model
  remains `Listing` for backward compatibility. Room entry uses one required
  address field, while the legacy `location` value is synchronized from it.
- The room editor keeps a fixed footer, uses one vertical body scroll when
  content or display scale requires it, and switches to a live Facebook-style
  preview in a dedicated sibling tab.
- Creating or editing a room requires at least one remaining image. Saving an
  imageless room is blocked before metadata or assets are changed, and the
  editor returns to the image section with a specific recovery message.
- Different accounts may post concurrently; the same browser profile must never
  have two simultaneous workers.
- “Bắt đầu tất cả” starts every logged-in account that has a plan and is not
  already running. An account currently posting is skipped without preventing
  the remaining eligible accounts from starting; if none are eligible, the UI
  explains which prerequisites to check.
- One posting round spans every queued room in order. Each still-active group
  receives one post for its room in that round; `post_interval` separates
  consecutive posts, including the transition between rooms, and
  `round_interval` runs only after the last room in the round.
- A configured group count is a fixed attempt budget. A failed submission uses
  only that attempt, remains visible as a failed result, and does not disable
  the group's remaining attempts in later rounds.
- A stop request never interrupts an active Facebook submission. It takes
  effect at the next interval boundary, cancels an interval already in
  progress, preserves completed results, and closes the account browser safely.
- Every completed attempt is emitted to that account's result dialog
  immediately and appears newest-first. A row shows the room image and facts,
  posting time, destination group, and a factual state: “Thành công” when a
  permalink was captured, “Bị gián đoạn” when Facebook accepted the post but
  no link was captured, or “Thất bại”. It opens the post permalink when
  available or the Facebook group as a fallback.
- Playwright objects are created and used entirely inside their worker thread.
- Posting workers launch their persistent Chromium contexts headlessly. If the
  unchanged posting primitive times out while typing into the composer, the
  account orchestrator retries that primitive once before recording the
  configured attempt as failed; post-submit timeouts are never retried.
- Existing locators, persistent contexts, `press_sequentially()`, clipboard
  permissions, Copy Link behavior, intervals, `GroupTarget` failure handling,
  and `PostResult` success semantics must be preserved.
- The GUI calls Python services directly and never launches the CLI through a
  subprocess.
- No CAPTCHA bypass, restriction bypass, anti-detection, fingerprint spoofing,
  or spam-evasion behavior is allowed.
- The persistence layer remains file-based; a database is not part of this
  scope.

## Brand Commitments

- Product name: FB-Automated-Posting / concise in-app brand “FB POSTER”.
- The interface keeps a near-black foundation with restrained purple accents,
  muted red destructive actions, and clear success/warning states.
- The voice is concise, calm, operational, and naturally Vietnamese.

## Evidence on Hand

- Working Playwright posting implementation under `src/facebook/`.
- Existing PySide6 application under `src/gui/`.
- Existing local listing metadata in `data/listings.json` and sample rental
  images in `data/test/images/`.
- Existing browser-session directories under `browser_sessions/`.
- No approved logo, icon set, external marketing claims, or Facebook group
  imagery is supplied; the interface must not fabricate them.

## Product Principles

1. One profile, one active worker: protect account sessions before throughput.
2. Configure once, reuse often: listings, images, and groups are durable local
   resources rather than disposable form values.
3. Progress must be factual: execution events come from the posting plan, never
   from parsed console text or UI guesses.
4. Keep automation shared: CLI and GUI use the same posting primitives and
   permalink path.
5. Make operational state obvious: users should always know what is ready,
   running, next, failed, and completed.
6. Show people, not storage paths: use the synced Facebook name and avatar in
   operational account selectors while retaining a stable local ID underneath.

## Accessibility & Inclusion

- Support Qt 6 high-DPI behavior without manual whole-interface scaling.
- Remain usable on smaller laptop windows and large 3200×2000 displays.
- Avoid unintended horizontal scrolling and keep dialog actions visible.
- Use readable contrast, keyboard-focus states, meaningful labels, and status
  cues that do not rely on color alone.
