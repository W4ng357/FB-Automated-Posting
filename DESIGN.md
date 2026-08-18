---
name: FB Poster Desktop
description: Bảng điều phối Qt tiếng Việt cho phòng, nhóm, hàng chờ và kết quả đăng Facebook cục bộ.
colors:
  surface-canvas: "#09090B"
  surface-terminal: "#0D0D11"
  surface-sidebar: "#0F0F13"
  surface-empty: "#111116"
  surface-panel: "#121217"
  surface-card: "#141419"
  surface-workspace-header: "#15151B"
  surface-success: "#15251B"
  surface-control-disabled: "#16161B"
  surface-read-only: "#16161C"
  surface-progress: "#17131F"
  surface-indicator-disabled: "#17171C"
  surface-control-pressed: "#17171D"
  surface-card-raised: "#18181F"
  surface-nav-hover: "#18181E"
  surface-image-preview: "#18181F"
  surface-field: "#1B1B22"
  surface-tab-hover: "#1C1C23"
  surface-control: "#1C1C24"
  surface-primary-disabled: "#1D1925"
  surface-idle-track: "#202027"
  surface-thumbnail: "#202029"
  surface-accent-soft: "#241A38"
  surface-tooltip: "#25252D"
  surface-control-hover: "#26262F"
  surface-running: "#281C45"
  surface-warning: "#292114"
  surface-stepper: "#292931"
  surface-danger: "#2B181D"
  surface-error: "#301B21"
  surface-danger-hover: "#3A1F25"
  border-sidebar: "#24242B"
  border-form-section: "#24242C"
  border-control-disabled: "#25252C"
  border-empty: "#25252D"
  border-workspace-header: "#272730"
  border-terminal: "#282831"
  border-surface: "#292933"
  border-ghost: "#303038"
  border-idle: "#303039"
  border-image-preview: "#2B2B35"
  border-thumbnail: "#30303A"
  border-control: "#383842"
  border-field: "#383842"
  border-progress: "#392851"
  border-popup: "#44444F"
  border-tooltip: "#4A4A55"
  border-accent-soft: "#4D3475"
  border-tab-selected: "#54367F"
  border-checkbox: "#555560"
  border-control-hover: "#50505C"
  border-running: "#57388C"
  border-warning: "#59471F"
  border-account-tab-selected: "#5A3A88"
  border-danger: "#603039"
  border-primary-disabled: "#30283E"
  border-success: "#285239"
  border-error: "#69343D"
  border-danger-hover: "#84404A"
  scrollbar-handle: "#393943"
  scrollbar-handle-hover: "#52525E"
  accent: "#6D42C6"
  accent-progress: "#7650C8"
  accent-hover: "#7A4FD0"
  accent-border: "#815DCE"
  accent-hover-border: "#916DDB"
  accent-pressed: "#5D37AE"
  accent-focus-field: "#8E6BDD"
  accent-focus-control: "#9B7AE8"
  text-primary: "#F4F4F5"
  text-strong: "#FAFAFA"
  text-control: "#E7E7EB"
  text-on-accent: "#FFFFFF"
  text-muted: "#A1A1AC"
  text-navigation: "#A9A9B3"
  text-idle: "#C7C7CF"
  text-terminal: "#D3D3DA"
  text-accent: "#D9CCFF"
  text-running: "#DDD1FF"
  text-tab-selected: "#E6DEFF"
  text-meta: "#7E7E89"
  text-placeholder: "#92929D"
  text-disabled-widget: "#686873"
  text-disabled-control: "#70707A"
  text-primary-disabled: "#716B7C"
  text-success: "#9DE8BA"
  text-warning: "#EACB82"
  text-error: "#F3A9B1"
  text-danger: "#F1B3BA"
typography:
  brand:
    fontFamily: "Noto Sans"
    fontSize: "20px"
    fontWeight: 800
    letterSpacing: "1px"
  page-title:
    fontFamily: "Noto Sans"
    fontSize: "28px"
    fontWeight: 750
  section-title:
    fontFamily: "Noto Sans"
    fontSize: "17px"
    fontWeight: 700
  empty-state-title:
    fontFamily: "Noto Sans"
    fontSize: "16px"
    fontWeight: 700
  card-title:
    fontFamily: "Noto Sans"
    fontSize: "15px"
    fontWeight: 700
  body:
    fontFamily: "Noto Sans"
    fontSize: "14px"
  control-label:
    fontFamily: "Noto Sans"
    fontSize: "14px"
    fontWeight: 600
  status-label:
    fontFamily: "Noto Sans"
    fontSize: "13px"
    fontWeight: 700
  metadata:
    fontFamily: "Noto Sans"
    fontSize: "13px"
  terminal:
    fontFamily: "JetBrains Mono, Noto Sans Mono, monospace"
    fontSize: "13px"
rounded:
  indicator: "5px"
  status: "7px"
  control: "8px"
  media: "10px"
  panel: "12px"
  dialog: "14px"
spacing:
  xxs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  xxl: "32px"
  dialog-edge: "24px"
  page-block: "28px"
  page-inline: "32px"
components:
  button-default:
    backgroundColor: "{colors.surface-control}"
    textColor: "{colors.text-control}"
    typography: "{typography.control-label}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.text-on-accent}"
    typography: "{typography.control-label}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.text-on-accent}"
    typography: "{typography.control-label}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-primary-disabled:
    backgroundColor: "{colors.surface-primary-disabled}"
    textColor: "{colors.text-primary-disabled}"
    typography: "{typography.control-label}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-danger:
    backgroundColor: "{colors.surface-danger}"
    textColor: "{colors.text-danger}"
    typography: "{typography.control-label}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  nav-selected:
    backgroundColor: "{colors.surface-accent-soft}"
    textColor: "{colors.text-accent}"
    typography: "{typography.control-label}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
    height: "44px"
  search-field:
    backgroundColor: "{colors.surface-field}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "8px 13px"
  card:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.panel}"
    padding: "16px 18px"
  status-enabled:
    backgroundColor: "{colors.surface-success}"
    textColor: "{colors.text-success}"
    typography: "{typography.status-label}"
    rounded: "{rounded.status}"
    padding: "4px 9px"
  status-running:
    backgroundColor: "{colors.surface-running}"
    textColor: "{colors.text-running}"
    typography: "{typography.status-label}"
    rounded: "{rounded.status}"
    padding: "6px 10px"
  image-preview:
    backgroundColor: "{colors.surface-image-preview}"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.media}"
    padding: "10px"
    width: "150px"
---

# Design System: FB Poster Desktop

## Overview

**Creative North Star: "Bàn điều phối yên tĩnh"**

FB Poster is an operate-first desktop interface: quiet enough for repeated daily use, dense enough to keep listings, groups, account queues, progress, logs, and results visible without decorative distraction. Near-black layers establish hierarchy; a restrained purple marks the next primary action, current selection, keyboard focus, and active posting state.

The interface behaves like one local operations desk rather than a social-media dashboard. It uses text, counts, stable cards, and explicit state labels instead of promotional imagery or inferred activity. The visual system is shared across the resizable PySide6 / Qt Widgets application and remains intentionally dark-only in the current implementation.

**Key Characteristics:**

- A fixed navigation rail beside a spacious, vertically scrolling work canvas.
- Tonal surface layering with fine borders and no ornamental shadows.
- Purple reserved for primary action, selection, focus, progress, and the running state.
- Compact list cards with content on the left and explicit actions on the right.
- Factual, text-backed status communication; color is reinforcement, never the only cue.
- Vietnamese labels and operational counts written for a single local operator.

## Colors

The canonical values are the YAML tokens above, extracted directly from `src/gui/styles/dark.qss`. Those names are documentation aliases: the QSS selectors remain the runtime source of truth.

### Primary

- **Operational Purple** (`accent`): the primary button and text-selection fill. Use it for the single strongest action in a local context.
- **Purple Hover** (`accent-hover`) and **Purple Border** (`accent-border`): the existing primary-button hover and edge treatments.
- **Focus Purples** (`accent-focus-control`, `accent-focus-field`): visible focus outlines for buttons and form controls. They are deliberately lighter than the fill.
- **Progress Purple** (`accent-progress`): progress-bar chunks only.
- **Soft Purple Selection** (`surface-accent-soft`, `border-accent-soft`, `text-accent`): selected sidebar items and related selected treatments.
- **Running Purple** (`surface-running`, `border-running`, `text-accent`): an account worker that is actively posting.

### Neutral

- **Canvas and shell** (`surface-canvas`, `surface-sidebar`, `border-sidebar`): the application field and the fixed navigation rail.
- **Panels and rows** (`surface-panel`, `surface-card-raised`, `border-surface`): primary containers use the lower panel tone; nested task, result, and group-selection rows use the raised tone.
- **Inputs and controls** (`surface-field`, `surface-control`, `border-field`, `border-control`): fields and buttons are distinguishable from panels without becoming bright.
- **Primary and supporting text** (`text-primary`, `text-strong`, `text-control`, `text-muted`, `text-navigation`): high-contrast labels lead; metadata, URLs, help, and summaries recede consistently.
- **Terminal** (`surface-terminal`, `border-terminal`, `text-terminal`): the posting log is the darkest inset surface and uses a mono stack.
- **Scrollbars** (`scrollbar-handle`, `scrollbar-handle-hover`): compact ten-pixel vertical scrollbars remain visible without pulling focus.

### Semantic states

| Meaning | Text | Fill | Border | Implemented label |
| --- | --- | --- | --- | --- |
| Available / enabled | `text-success` | `surface-success` | `border-success` | “Đang dùng” |
| Hidden / unavailable | `text-warning` | `surface-warning` | `border-warning` | “Đã ẩn” |
| Idle | `text-idle` | `surface-idle-track` | `border-idle` | “Sẵn sàng”, “Chưa mở Chromium”, “Đã đóng Chromium” |
| Account needs login | `text-warning` | `surface-warning` | `border-warning` | “Chưa đăng nhập” |
| Account has session but no profile | `text-warning` | `surface-warning` | `border-warning` | “Chưa đồng bộ” |
| Account synced | `text-success` | `surface-success` | `border-success` | “Đã đồng bộ” |
| Running / in progress | `text-running` | `surface-running` | `border-running` | “Đang chạy”, “Đang mở”, “Chờ đăng nhập”, “Đang đọc hồ sơ” |
| Stop requested / stopped | `text-warning` | `surface-warning` | `border-warning` | “Đang chờ dừng”, “Đã dừng” |
| Completed run | `text-success` | `surface-success` | `border-success` | “Hoàn tất” |
| Successful result | `text-success` | transparent | none | “Đăng thành công” |
| Error run / login | `text-error` | `surface-error` | `border-error` | “Lỗi”, “Có lỗi” |
| Failed result | `text-error` | transparent | none | “Đăng thất bại” |
| Destructive action | `text-danger` | `surface-danger` | `border-danger` | “Xóa”, “Gỡ ảnh”, “Gỡ khỏi hàng chờ” |

**The Rare Accent Rule.** Purple identifies agency or current state. Do not spend it on decoration, neutral metadata, or every available action.

**The Text Before Color Rule.** Every state keeps a meaningful Vietnamese label or numeric result; the hue never has to carry the meaning alone.

## Typography

**UI Font:** Noto Sans, requested by `src/gui/app.py` through `QFont("Noto Sans", 10)`; normal system font fallback applies when it is unavailable. The QSS sets the rendered interface base size to 14px.

**Log Font:** JetBrains Mono, then Noto Sans Mono, then the platform monospace fallback.

**Character:** The hierarchy is compact, plainspoken, and weight-led. There is no display face: the same sans family keeps Vietnamese diacritics, account names, IDs, URLs, and action labels visually coherent.

### Hierarchy

- **Brand** (800, 20px, 1px tracking): the uppercase “FB POSTER” wordmark in the sidebar only.
- **Page title** (750, 28px): one title at the top of each page or dialog.
- **Section title** (700, 17px): room details, queue, progress, image, preview, and account-section headings.
- **Empty-state title** (700, 16px): the intentionally quieter title inside bounded empty-state panels.
- **Card title** (700, 15px): room names, group names, task titles, and result destinations.
- **Body** (14px): forms, metadata, descriptions, summaries, URLs, tabs, and ordinary labels.
- **Control label** (600, 14px): buttons and navigation actions.
- **Status label** (700, 13px): compact badges whose words carry operational state.
- **Metadata** (13px): session IDs, update dates, captions, and secondary machine-facing details.
- **Terminal** (13px): timestamped per-account activity only.

No explicit line-height scale is implemented. Preserve Qt's native text metrics rather than introducing arbitrary fixed line heights into isolated widgets.

**The One-Family Rule.** Use Noto Sans throughout the operational UI; reserve the mono stack for machine-like posting logs.

**The Weight Builds Hierarchy Rule.** Distinguish heading levels with the implemented size-and-weight steps, not uppercase body text or extra accent colors.

## Layout

The main window has a 1120×720 minimum and opens at 1480×920. A fixed 228px sidebar sits on the left; there is no collapsed, overlay, bottom-navigation, or mobile layout in the current build. Page content receives 32px inline and 28px block margins, usually with 16px between major regions. Page changes use one subtle 180ms opacity transition from an already-visible state.

The recurring page structure is header, search or overview strip, then a vertically scrolling list. Page headers keep the title/subtitle stack left and the main actions right. Listing and group cards fill the available width; their content expands while the action row remains content-sized.

### Density and spacing

- Page edge: 32px horizontally and 28px vertically.
- Sidebar edge: 20px horizontally, 28px above, 24px below; navigation buttons are at least 44px tall.
- Dialog edge: 24px horizontally, 22px above, 20px below.
- Panel content: generally 15–20px, with 8–14px internal gaps.
- Repeating list gap: 12px for page cards and 9px for compact queue/result/selector rows.
- Major page action buttons use a 42px minimum height where explicitly set.

### Dialog and scrolling rules

- Room dialogs have a 780×660 minimum and open at 1000×880; group-selection dialogs have a 760×580 minimum and open at 880×680; group dialogs have a 640px minimum width and open at 700×430.
- Room editing uses a single vertically scrolling body beneath a fixed title and above a fixed Save/Cancel footer. Basic fields remain in a compact two-column grid where width allows. The image grid wraps inside that body and does not own another scrollbar. The workspace uses sibling tabs for “Thông tin phòng” and “Xem trước bài viết”, avoiding width-dependent side-by-side compression at high desktop scale; long preview content scrolls only inside its tab.
- Group-selection content scrolls vertically between a fixed heading and a fixed `QDialogButtonBox` footer. Save/confirm stays primary and is followed by “Hủy”.
- Account management has a 780×580 minimum and opens at 900×680, with a
  vertically scrolling list and fixed Close footer. Login has a 700×520
  minimum and opens at 760×570, keeping identity, guidance, factual status,
  and its three actions visible without an inner scrollbar. The alias editor
  has a 600px minimum width and opens at 660×360.
- Account posting content scrolls inside each account tab. The activity tabs maintain a 250px minimum height.
- Page, dialog, account, results, and log scroll areas explicitly suppress horizontal scrollbars. Inner scroll content keeps an 8–10px right gutter for the vertical scrollbar.
- Room image previews use `FlowLayout`: compact 136px vertical cards with cached 116×72 thumbnails and 10px gaps wrap to the next row as width changes. The dialog body owns vertical overflow; the grid never produces horizontal scrolling.
- High-DPI behavior is delegated to Qt 6. Do not add whole-interface scale transforms or hard-coded pixel multiplication.

**The Bounded Overflow Rule.** Dialog actions never move behind a scrollbar. A room dialog has one body scrollbar for fields and unbounded media, while preview content, logs, results, and long repeating lists own their clearly bounded local scrolling; horizontal application scrolling is not part of this system.

**The Footer Stays Put Rule.** Long dialog content may scroll, but Save/Confirm and Cancel remain outside the scrolling body.

## Elevation & Depth

The implemented system has no drop shadows. Depth comes from ordered near-black fills, selective one-pixel borders, and tonal contrast: canvas → section → raised row or field. Purple, green, amber, and red fills appear only when a control or state needs semantic emphasis.

Tooltips are the only small floating surface styled explicitly, using `surface-tooltip`, `border-tooltip`, and `text-strong`. Dialog modality and native window elevation are supplied by Qt and the operating system, not a custom shadow token.

**The Tonal Layering Rule.** Add hierarchy with an existing surface and border pair before considering a new elevation effect.

**The No Decorative Shadow Rule.** Cards, panels, previews, and controls remain flat; do not add glows or card shadows that are absent from the desktop shell.

## Shapes

The form language is gently rounded and compact rather than pill-shaped.

- **Panels and list cards** use the 12px panel radius with a one-pixel surface border.
- **Image previews and tab panes** use the 10px media radius.
- **Buttons and fields** use the 8px control radius.
- **Status badges** use the 7px status radius.
- **Checkboxes, progress bars, and scrollbar handles** use the 5px indicator radius.

Borders are structural. Standard controls, fields, cards, previews, selected tabs, and semantic badges each keep their implemented one-pixel edge. Focus replaces the normal control edge with a two-pixel purple border and compensates padding by one pixel, avoiding a visible size jump.

**The Soft Rectangle Rule.** Keep components rectangular with moderate corners; full pills and circular icon buttons are not part of the shipped vocabulary.

## Components

### Motion

Motion is functional and bounded. Top-level page changes fade from 84% to full opacity over 180ms with an ease-out curve. Posting progress interpolates to the next worker-provided value over 320ms and can be interrupted by a newer value. Hover and pressed feedback remain native QSS state changes. There are no continuous loops, entrance cascades, dialog zooms, decorative glows, or motion that invents progress.

**The Factual Motion Rule.** Animation may smooth a real state change but must never create, delay, or imply backend work.

### Application shell and navigation

The sidebar anchors the brand, subtitle, three top-level destinations, and a two-line local-data footer. Navigation labels are “Phòng”, “Nhóm”, and “Đăng bài”. Items are left-aligned, transparent by default, use `surface-nav-hover` on hover, and switch to the soft-purple surface/border/text trio when checked. The selected destination is persistent text-backed state, not an icon cue.

### Page header, overview, and search

Every top-level page begins with a page title, a muted explanatory sentence, and one or two right-aligned actions. Room and group pages place a full-width search field below the header. The posting page replaces search with a compact overview strip showing account count, queued rooms and predicted attempts, then running/idle counts.

Search fields use a darker field treatment with 8×13px padding, a clear button, and a specific Vietnamese placeholder. Filtering occurs as text changes; no separate submit button exists.

### Buttons

- **Default:** neutral control surface, one-pixel control border, control text, 8×14px padding, 8px corners.
- **Primary:** purple fill and border with white text; use for Add, Start, Save, Confirm, metadata fetch, or opening a successful post. A local region should have one clearly strongest next action.
- **Ghost:** transparent fill with a muted border; currently used for “Ẩn tin”.
- **Danger:** muted red fill, border, and text; hover strengthens both fill and border without becoming bright red.
- **Hover:** default controls move to `surface-control-hover` / `border-control-hover`; primary moves to `accent-hover`.
- **Pressed:** standard controls move to `surface-control-pressed`.
- **Focus:** standard buttons receive a two-pixel `accent-focus-control` border and reduce padding to 7×13px so geometry stays stable.
- **Disabled:** standard controls use `surface-control-disabled`, `text-disabled-control`, and `border-control-disabled`; primary buttons use the darker `surface-primary-disabled` treatment so an unavailable purple action cannot look active. Disabled widgets fall back to `text-disabled-widget`.

### Fields, checks, and selectors

Line edits, plain-text edits, combo boxes, and numeric inputs share the field surface, one-pixel border, 8px corners, and 8×10px padding. Focus uses a two-pixel `accent-focus-field` border and 7×9px padding. Selected text uses the main accent with white text.

Checkbox indicators are 18×18px with 5px corners. Checked state fills with the main accent and uses the lighter focus-color border. In group-selection rows, the numeric attempt input is enabled only when its checkbox is checked; the disabled treatment makes that dependency visible.

### Cards and media

Room and group cards use the panel surface and 12px corner radius. Room cards show the first locally stored photo, while rooms without media and all groups use a restrained first-letter fallback. Titles, metadata, address/URL, and status form a scan path from left to right. “Chỉnh sửa” stays visible; less frequent toggle/refresh/delete actions live under a text-labelled “Tùy chọn” menu. Group metadata retrieval remains name-only and never downloads Facebook imagery.

### Facebook account identity and login

“Quản lý tài khoản” is the single entry point for add, login, re-sync, alias
edit, and delete. Each fixed-height card shows a circular cached avatar or
first-letter fallback, display name, Facebook synchronization detail, stable
session ID, update date when known, and a text-backed status. Display priority
is local alias → synced Facebook name → stable ID; when an alias is present,
the underlying Facebook name stays visible as identity detail.

New accounts receive a stable `account-NNN` ID. A synced name, avatar, or alias
changes presentation only and never renames that ID or its Chromium directory.
Legacy directories already present under `browser_sessions/` are surfaced as
accounts without migration, use the directory name as their stable ID and
fallback label, and can be synchronized later. Manager cards show “Đăng nhập”
when no session directory exists and “Đồng bộ lại” when it does; “Chỉnh sửa”
opens the alias editor. Destructive deletion stays under the text-labelled
“Tùy chọn” menu, requires confirmation, removes account metadata, cached avatar,
and the Chromium profile, and is rejected while that account is in use.

The manager states are exact and mutually legible: “Chưa đăng nhập” means no
session directory; “Chưa đồng bộ” means a session exists but no Facebook name
has been captured; “Đã đồng bộ” means both the session and synchronized profile
are available. Posting adds its own explicit “Sẵn sàng”, “Đang chạy”, “Hoàn
tất”, and “Lỗi” states, while a pending tab stays visible as “Chưa đăng nhập”
with its primary Start action disabled.

The login dialog never asks for a password, verification code, or checkpoint
answer. “Mở Facebook” launches the account's isolated persistent Chromium
profile; the operator enters credentials there, returns to the dialog, and uses
“Đã đăng nhập, lấy thông tin”. Its badge sequence is explicit: “Chưa mở
Chromium” → “Đang mở” → “Chờ đăng nhập” → “Đang đọc hồ sơ” → “Đã đồng bộ”,
with “Có lỗi” on worker failure and “Đã đóng Chromium” after an unsaved browser
closure. The disabled capture action uses the dedicated disabled-primary
surface, text, and border tokens instead of a faded active purple. The browser
worker owns all Playwright objects, and the dialog waits for safe browser
closure before it accepts or rejects.

`RoundedThumbnail` displays ordinary cached media with an 11px mask radius;
its account-avatar mode uses a true elliptical painter path so both cached
images and first-letter fallbacks are clipped to a circle. Account-manager
cards use 64×64px avatars, login identity uses 76×76px, and posting account
headers use 54×54px. The fallback keeps the same border and accessible “Ký
hiệu nhận diện” label; it does not fabricate a social profile image.

### Room editor and post preview

The room editor is a two-face workbench. The left pane is the primary task path: name, required address, price/area pair, description, contact/status pair, then a bounded image gallery. “Khu vực” is not a user-facing field; new and edited rooms synchronize the legacy internal location value from the address.

Room images are required for both create and edit flows. The section title uses
an asterisk and its helper sentence states the one-image minimum before an
error occurs. Saving with no remaining image keeps all entered values intact,
switches back to the editor, reveals the image section, focuses “Thêm ảnh”, and
shows the corrective warning “Hãy thêm ít nhất 1 ảnh phòng trước khi lưu.”

The secondary “Preview bài viết” control switches to the sibling Preview tab rather than resizing the window or adding another block below the form. The tab simulates a dark Facebook group post with author context, the exact generated caption, a one-to-four-image media grid, image count, and interaction labels. It updates live as fields or images change. This is an approximation, so its helper copy never claims pixel-identical output.

Task cards, result cards, and group-selection rows use the raised card surface to remain legible when nested inside another panel. Room image previews use a compact horizontal card with a contained thumbnail, filename, and danger action so a complete image item remains visible inside the bounded gallery.

### Tabs, queue, progress, log, and results

Account tabs use a dark panel pane. Tabs show the cached Facebook avatar when
available through the same circular crop as account headers, the synced name
or optional alias, and an explicit “· trạng thái”.
The stable local account ID remains the worker/session key and appears in the
tooltip and account header metadata. Selected tabs use the soft-purple surface
and `text-tab-selected`; pending accounts remain visible as “Chưa đăng nhập” but
cannot start until a session exists.

Each account owns a header, prominent progress region, queue, activity log, and result list in that order. Starting a plan disables the start button, listing selector, task addition, and each task card while enabling the muted-red “Dừng đăng bài” action. A stop request changes that action and the account state to “Đang chờ dừng”; it disables repeat requests and becomes “Đã dừng” only after the worker reaches a safe interval boundary. The disabled danger action uses the neutral disabled treatment instead of appearing active. The progress bar value is driven by attempted operations and interpolated for 320ms; adjacent text reports completed, total, failed, skipped or remaining counts plus current and next listing/group. Do not derive those facts from the log.

One round traverses every queued room and each currently active group once.
`post_interval` separates consecutive posts, including the transition to the
next room; `round_interval` appears only after the final room in that round.
Each configured count is an attempt budget: a failure consumes the current
attempt but the target remains eligible in later rounds until that budget is
exhausted. The total shown at start remains the denominator for the full run,
including a safely stopped run.
The log uses the terminal treatment and prepends `HH:mm:ss`. Each attempt adds
a result card immediately and increments the “Kết quả (n)” tab label. Cards use
explicit success/failure sentences, show a selectable destination URL, open the
post when a permalink exists, and otherwise offer “Mở nhóm” for direct checking.

### Dialogs and feedback

Dialogs use a page-scale title, muted explanation, task content, and a bottom action box. Save/Confirm is primary; Cancel is neutral. Validation and service failures use native `QMessageBox` warning/critical/information dialogs with a specific title and a corrective Vietnamese sentence. Destructive deletion asks for confirmation before changing persisted data.

### Vietnamese copy voice

- Use concise nouns for destinations and sections: “Phòng”, “Nhóm”, “Đăng bài”, “Tiến trình”, “Kết quả”.
- Start actions with a direct verb and name the object: “Thêm phòng”, “Chọn nhóm”, “Gỡ khỏi hàng chờ”, “Lưu phòng”.
- State facts with quantities and units: “2 phòng · 5 lượt”, “0/0 lượt thành công”, “1 ảnh đã lưu”.
- Use a calm recovery instruction after a problem: say what failed, then what the operator can check or do next.
- Preserve IDs, account names, URLs, timestamps, prices, square metres, and the middle-dot separator exactly where they carry operational meaning.
- Never imply success from elapsed time or generic activity. Use “Đăng thành công”, “Đăng thất bại”, “Chưa lấy được liên kết bài viết”, and other backend-supported facts.

### Accessibility contract

- Keep body text at the implemented 14px base and log text at 13px; do not shrink muted metadata below the log size.
- Keep standard button and form focus borders visible. If navigation or checkbox styling changes, preserve a distinct keyboard-focus cue in addition to checked state.
- Pair semantic color with words or counts. “Đang dùng”, “Đã ẩn”, “Đang chạy”, “Hoàn tất”, and “Lỗi” must remain readable without color perception.
- Preserve the 44px navigation minimum and the explicitly implemented 42px minimum on major page/start actions.
- Keep long help and result text wrapped where the widgets already enable word wrapping. Keep group URLs mouse-selectable in cards and selection rows.
- Maintain text labels on actions; the current interface does not depend on unlabeled icons.
- Respect Qt 6 high-DPI rendering and platform font fallback. Validate future changes at the 1120×720 minimum and on a large high-DPI desktop.

### Implementation map

| System area | Source |
| --- | --- |
| Application font, Fusion style, QSS loading | `src/gui/app.py` |
| Canonical colors, type sizes, radii, and control states | `src/gui/styles/dark.qss` |
| Shared badge, empty state, thumbnail, and progress primitives | `src/gui/widgets/design_components.py` |
| Main-window sizing, fixed sidebar, page navigation | `src/gui/main_window.py` |
| Page headers, search, list scrolling, posting overview, account-tab identity, manager entry | `src/gui/pages/listings_page.py`, `groups_page.py`, `posting_page.py` |
| Fixed dialog footers, room form, group metadata, group selection | `src/gui/dialogs/listing_dialog.py`, `group_dialog.py`, `group_selector_dialog.py` |
| Facebook-style room post preview | `src/gui/widgets/facebook_post_preview.py` |
| Per-account queue, factual progress, logs, result presentation | `src/gui/widgets/account_posting_tab.py` |
| Account manager, add/login/re-sync flow, alias edit, destructive confirmation | `src/gui/dialogs/account_manager_dialog.py`, `account_login_dialog.py` |
| Stable account identity and display-name priority | `src/models/facebook_account.py` |
| Legacy-session merge, account CRUD, and synchronization | `src/services/facebook_account_service.py`, `src/session_manager.py` |
| Account JSON persistence and avatar cache | `src/services/facebook_account_repository.py`, `src/services/facebook_account_asset_manager.py` |
| One-active-worker session guard used by login, posting, and deletion | `src/services/account_session_registry.py` |
| Browser-thread profile capture | `src/facebook/account_profile.py`, `src/gui/workers/account_login_worker.py` |
| Reusable list and result card patterns | `src/gui/widgets/listing_card.py`, `group_card.py`, `posting_task_card.py`, `result_card.py` |
| Wrapping image previews | `src/gui/widgets/flow_layout.py`, `image_preview.py` |
| Thread-safe progress and metadata signals feeding the UI | `src/gui/workers/posting_worker.py`, `group_metadata_worker.py` |

## Do's and Don'ts

### Do:

- **Do** use the existing dark surface ladder and one-pixel borders to separate nested information.
- **Do** reserve the main purple for the current selection, focus, progress, running status, or a clearly primary action.
- **Do** keep posting progress factual and sourced from structured progress/results emitted by the worker path.
- **Do** keep dialog actions outside long scrolling content and maintain Save/Confirm before Cancel.
- **Do** allow image cards to wrap through `FlowLayout` and keep horizontal scrollbars off.
- **Do** use Vietnamese action-first labels, explicit objects, concrete counts, and calm corrective errors.
- **Do** test layouts at 1120×720 and at high DPI, including long Vietnamese text, account names, URLs, and multi-digit counts.
- **Do** keep passwords and verification steps inside the launched Facebook
  browser, and use a readable initial whenever no avatar could be cached.
- **Do** preserve the stable account ID beneath aliases and synced names, and
  keep the account/login status words aligned with the implemented state.

### Don't:

- **Don't** introduce gradients, decorative glows, drop shadows, glass effects, or bright social-media color blocks into the current flat tonal system.
- **Don't** use purple as general decoration or make every button primary.
- **Don't** communicate enabled, hidden, running, success, warning, or error state by color alone.
- **Don't** add horizontal application scrolling or a second independent scroll region where the current vertical hierarchy already works.
- **Don't** move dialog Save/Confirm controls into the scroll body.
- **Don't** invent posting state by parsing console text, elapsed time, or browser appearance.
- **Don't** add a collapsible sidebar, mobile layout, light theme, icon language, continuous motion, or decorative animation; these are outside the current interface.
- **Don't** display a session folder name as the primary identity after a
  Facebook profile has been synchronized.
- **Don't** rename a Chromium session directory when an alias or Facebook name
  changes, or render a disabled primary action with the active purple fill.
