# Biên bản nghiệm thu — Nâng cấp Solo-Code-CLI theo kế hoạch đã chốt

> **Người thực hiện:** Kilo (model `deepseek/deepseek-v4.1-flash`).
> **Ngày:** 2026-09-26.
> **Kế hoạch nguồn:** [`deepseek-harness-upgrade-review-plan.md`](deepseek-harness-upgrade-review-plan.md), [`deepseek-harness-upgrade-review-followup.md`](deepseek-harness-upgrade-review-followup.md).
> **Phản biện:** [`deepseek-harness-upgrade-review-response.md`](deepseek-harness-upgrade-review-response.md), [`deepseek-harness-upgrade-review-response-round2.md`](deepseek-harness-upgrade-review-response-round2.md).
> **Phạm vi:** Sáu bước đã chốt (Bước 0–6). Không xoá DB/lock; mọi lệnh destructive đều không dùng.

---

## 1. Tóm tắt điều hành

- Toàn bộ 6 bước đã hoàn thành. Gate sau triển khai **xanh** (xem §2).
- Hai lỗi đã sửa và **tái hiện kiểm chứng**: (a) `checklist.py` từng PASS-im-lặng khi thiếu tool, giờ FAIL; (b) `codex_guard.py` từng rò rỉ lock, giờ release cả khi thành công lẫn khi lỗi.
- Mâu thuẫn feature state đã chốt theo **Phương án B**: SQLite chỉ giữ session/lock; feature/task dùng `git log` + `.kilo/memory/MEMORY.md`. `AGENTS.md` (phía lệch) đã được sửa cho khớp.
- Lock rò rỉ cũ trong `.solocode/shared-state.db` đã được release (có backup trước khi thao tác): `Active locks` 1 → 0.
- Không có dependency mới. Không commit (chưa được yêu cầu).

---

## 2. Gate: baseline vs sau triển khai

| Gate | Baseline (Bước 0) | Sau triển khai | Ghi chú |
|---|---|---|---|
| `security_scan.py` | exit 0 | exit 0 | 2518 file, 0 issue |
| `check_skips.py tools/` | exit 0 | exit 0 | No-skips policy: OK |
| `validate_schemas.py` | exit 0 (66 file, 0 lỗi) | exit 0 (0 lỗi) | |
| `garden.py` | exit 0 | exit 0 | Xem §7 xác nhận cuối |
| `pytest tools/ -q` | 535 passed, 3 skipped | **544 passed, 3 skipped** | +9 test mới |
| `test_integration.py` | exit 0 | exit 0 (194 pass, 0 fail) | |
| `checklist.py .` | **exit 1** (Ruff FAILED) | **exit 0** (6/6 PASS) | Xem §3.6 |
| shared_state `locks` | 1 (rò rỉ từ test) | 0 | Xem §3.3 |

Lệnh đã chạy thật được lưu tại `.solocode/review-artifacts/baseline/` và `.solocode/review-artifacts/final/` (thư mục này thuộc `.solocode/`, local-only, không commit).

---

## 3. Chi tiết từng bước

### 3.1 Bước 0 — Baseline

Chạy đủ danh sách trong kế hoạch. Phát hiện quan trọng: `checklist.py` fail **chỉ vì 2 lỗi `I001` nằm trong `learn-harness-engineering-main/`** (reference checkout chưa được `.gitignore` loại). Bằng chứng:

```text
ruff check . --output-format concise
learn-harness-engineering-main\docs\en\lectures\lecture-14-graph-engineering\code\maker_checker_graph.py:12:1: I001 ...
learn-harness-engineering-main\docs\zh\lectures\lecture-14-graph-engineering\code\maker_checker_graph.py:12:1: I001 ...
Found 2 errors.
```

Điều này xác nhận dự đoán ở vòng phản biện: thiếu ignore không chỉ là repository hygiene mà còn làm fail gate lint.

### 3.2 Bước 1 — Chốt feature state (Phương án B)

| File | Thay đổi |
|---|---|
| `AGENTS.md` | Bỏ yêu cầu bắt buộc `state.set_feature_status(...)` và luật "Pick exactly ONE `in-progress` feature"; ghi rõ feature/task tracking dùng `git log` + `.kilo/memory/MEMORY.md`; API `set_feature_status()` vẫn tồn tại nhưng không thuộc workflow hiện tại. Sửa cả phần mô tả `session_start.py`/`session_end.py` cho khớp hành vi thật. |
| `.kilo/instruction/shared-state.md` | Cập nhật số liệu snapshot (`session_log` 1000; `active_locks` mô tả cơ chế TTL 2h); sửa mô tả session start/end; thêm bảng "Hai SQLite store"; sửa đoạn lock đã cũ. |
| `.kilo/memory/MEMORY.md` | Thêm decision 2026-09-26 (feature state ngoài SQLite; hai store session tách vai trò). |
| `.claude/`, `.opencode/`, `.copilot/`, `.gemini/antigravity/` | Sinh lại mirror từ `.kilo/` bằng `python tools/generate_harness.py --harness all`. |

Bằng chứng: `AGENTS.md` không còn câu lệnh bắt buộc; mirror đồng bộ. Sau khi sửa, `garden.py` chỉ còn báo 5 drift do biên bản này chưa tồn tại (đã giải quyết khi tạo file này).

### 3.3 Bước 2 — Bản đồ hai session store

Đã kiểm chứng writer/reader và tài liệu hoá (đưa vào `shared-state.md`):

| Store | Bảng | Writer | Reader | Mục đích |
|---|---|---|---|---|
| `.solocode/shared-state.db` | `session_log`, `active_locks`, `shared_memory_*` | `pre_compact.py`, `codex_session.py`, `codex_guard.py` (lock) | `tools/shared_state.py` CLI, `garden.py`, `test_integration.py` | Nhật ký sự kiện đa engine + khoá file |
| `.solocode/sessions.db` | `sessions` | `.claude/hooks/session_start.py`, `session_end.py` (qua `session_persistence`) | `session_persistence.py`, `session_analytics.py`, `session_start.py` | Vòng đời phiên cho analytics |

Quyết định: **giữ song song**, không hợp nhất khi chưa chứng minh consumer trùng.

### 3.4 Bước 3 — Lock lifecycle của Codex

`tools/codex_guard.py`:
- Sinh `session_id` cho mỗi invocation; truyền vào **cả** `acquire_lock` và `release_lock` (tránh release nhầm owner mới hơn).
- Release trong `finally` — chạy cả khi ghi thành công, khi ghi lỗi, và không release khi lock thuộc engine khác (fail-closed).
- Thêm seam `CODEX_GUARD_STATE_DB` để test cô lập khỏi DB production.

`tools/test_codex_guard.py`: thêm 5 test (release khi thành công; lock engine khác vẫn chặn và được giữ; secret bị chặn trước khi acquire; ghi lỗi vẫn release; hai invocation dùng owner `session_id` khác nhau).

Mỗi invocation sinh `session_id = uuid.uuid4().hex`; guard không dùng `CODEX_SESSION_ID` làm owner. Release nằm trong `finally` và bắt `sqlite3.Error`, ghi `WARNING` ra stderr thay vì nuốt lỗi.

Kết quả: `pytest tools/test_codex_guard.py -q` → **19 passed**. Xử lý lock rò rỉ cũ: backup `.solocode/shared-state.db` → `.solocode/review-artifacts/shared-state.db.bak`, rồi release đúng path rò rỉ qua API. `python tools/shared_state.py locks` sau đó **rỗng**.

### 3.5 Bước 4 — checklist.py bắt buộc vs tùy chọn

`.github/scripts/checklist.py`: `run_check(..., required=True)`. Tool bắt buộc thiếu → `passed=False, skipped=False` (FAIL); tool tùy chọn thiếu → SKIP. ESLint/npm test/Build đánh dấu `required=False`.

`tools/test_checklist_gate.py`: 4 test (required thiếu → fail; optional thiếu → skip; lệnh chạy mà exit khác 0 → fail; exit 0 → pass).

### 3.6 Bước 5 — Drift docstring

`.claude/hooks/session_start.py`: docstring nói đọc "shared-state sessions"; sửa cho khớp code thật (đọc `.solocode/sessions.db` qua `tools/session_persistence.py`).

### 3.7 Bước 6 — `.gitignore`

Thêm `learn-harness-engineering-main/` vào mục "Reference checkouts". Đây là **repository hygiene**, không phải nâng cấp runtime.

Bằng chứng: `git check-ignore learn-harness-engineering-main/` → in ra path (exit 0); `ruff check .` → **All checks passed!**; `git status --short` không còn `?? learn-harness-engineering-main/`.

---

## 4. Mutation test

| Mutation | Cách làm | Kỳ vọng | Thực tế |
|---|---|---|---|
| Thiếu tool bắt buộc | Chạy `checklist.py` với PATH không có `ruff` | exit != 0 | **exit 1**, dòng `[FAIL] Ruff Linter: required tool not found on PATH` |
| Lint fail | `ruff check <temp>/bad.py` (unused import) | exit 1 | exit 1, `F401 os imported but unused` |
| Security fail | `security_scan.py <temp>/leak.py` (fake key) | exit 1 | exit 1, 2 finding `[SECRET: Hardcoded API key]`, `[SECRET: Anthropic API key]` |
| Required-thiếu (cô lập) | `run_check(..., required=True)` với binary không tồn tại | `passed=False` | pass test `test_missing_required_tool_fails` |
| Optional-thiếu (cô lập) | `run_check(..., required=False)` | `passed=True, skipped=True` | pass test `test_missing_optional_tool_is_skipped` |

Lưu ý: khi PATH bị rút gọn, `checklist.py` còn báo FAIL thêm `Harness Eval` và `Pytest` do các test đó shell-out tới binary khác — đây là collateral dự kiến của việc rút PATH, không phải lỗi mới. Kết luận cần khẳng định: Ruff (bắt buộc) **fail đúng** và tổng gate exit 1.

---

## 5. Danh sách file thay đổi

Sửa:
- `AGENTS.md`
- `.kilo/instruction/shared-state.md` (+ mirror `.claude/`, `.copilot/`, `.gemini/antigravity/`, `.opencode/`)
- `.kilo/memory/MEMORY.md` (+ mirror `.claude/`, `.copilot/`)
- `.claude/hooks/session_start.py`
- `.github/scripts/checklist.py`
- `tools/codex_guard.py`
- `tools/test_codex_guard.py`
- `.gitignore`

Tạo mới:
- `tools/test_checklist_gate.py`
- `docs/deepseek-harness-upgrade-acceptance.md` (file này)
- Các file review trong `docs/` (plan, followup, 2 response) — do vòng review tạo.

Không commit (chưa có yêu cầu).

---

## 6. Việc hoãn (theo kế hoạch)

Không triển khai: `feature_list.json`, `progress.md`, `session-handoff.md`, `testedAt`, SQLite adapter cho validator, tích hợp `audit-harness.sh` vào gate, `set -e` cho `verify.sh` (là aggregate reporter), refactor `subagent_seam.py`, hợp nhất hai SQLite store.

---

## 7. Xác nhận gate cuối

- `python tools/garden.py` → **PASS (Total drift issues: 0)** — xác nhận sau khi biên bản này tồn tại.
- `python .github/scripts/checklist.py .` → **exit 0 (6/6 PASS)**.
- `python -m pytest tools/ -q` → **544 passed, 3 skipped**.
- `python tools/shared_state.py show` → `Features: 0 | Sessions: 1000 | Active locks: 0`.

---

## 8. Uncertainty / chưa kiểm chứng

- `[Verified]` Ma trận lifecycle cross-engine đã đối chiếu với hook/config và adapter thực tế; artifact có bằng chứng ở [`lifecycle-matrix-verification.md`](lifecycle-matrix-verification.md).
- `[Partial]` Deploy đã kiểm tra bằng `--dry-run` trên repo hiện tại và chạy `tools/test_deploy.py` (30 passed); chưa deploy thật vào project đích độc lập.
- `[Verified]` `audit-harness.sh` chạy được qua Git Bash trên Windows. Nó exit 1 vì các tiêu chí generic yêu cầu `PROGRESS.md`, `feature_list.json` và lockfile; đây là kết quả dự kiến theo quyết định Phương án B, không phải regression của runtime harness.
- `[Inference]` `Harness Eval`/`Pytest` fail khi rút PATH là collateral, chưa truy nguyên từng nguyên nhân.
- `[Not verified]` Chưa chạy live Kilo SessionEnd/Codex lifecycle; ma trận chỉ xác minh tĩnh registration và code path.

## 9. Kiểm chứng bổ sung sau nghiệm thu

### 10.1 Ma trận lifecycle cross-engine

Bảng bằng chứng chính thức: [`lifecycle-matrix-verification.md`](lifecycle-matrix-verification.md).

| Engine | Session start/end mechanism | Store ghi | Trạng thái kiểm chứng |
|---|---|---|---|
| Kilo | `.kilo/hooks/hooks.json` đăng ký `session-start.js` và `session-end.js` | `.kilo/state/sessions/*.json`, token/tool state; không ghi SQLite session store | `[Verified]` bằng hook source |
| Claude Code | `.claude/settings.json` đăng ký `session_start.py` và `session_end.py` | `.solocode/sessions.db` qua `tools/session_persistence.py`; `pre_compact.py` ghi checkpoint vào shared-state DB | `[Verified]` bằng config + source |
| Codex | Không có native lifecycle hook; `tools/codex_session.py start/end` là adapter thủ công | `.solocode/shared-state.db` (`session_log`) | `[Verified]` bằng adapter source |
| OpenCode | Không có lifecycle hook tương đương trong repo | Không có writer lifecycle riêng được phát hiện | `[Verified]` bằng repo search |
| Copilot | Không có lifecycle hook tương đương trong repo | Không có writer lifecycle riêng được phát hiện | `[Verified]` bằng repo search |
| Gemini | Không có lifecycle hook tương đương trong repo; dùng handoff files khi cần | Không có writer lifecycle riêng được phát hiện | `[Verified]` bằng repo search |

Kết luận: các engine không chia sẻ một lifecycle implementation duy nhất. Tài liệu hiện tại mô tả đúng phạm vi này; không mở rộng thành tuyên bố rằng mọi engine đều tự động ghi session.

### 10.2 Deploy và audit tham khảo

- `python tools/deploy.py deploy . --dry-run` hoàn tất, không ghi file và báo kế hoạch 2.283 file.
- `python -m pytest tools/test_deploy.py -q` → **30 passed**.
- `bash learn-harness-engineering-main/tools/audit-harness.sh .` chạy được qua Git Bash, exit **1**. Các critical fail là mô hình generic của khóa học (`PROGRESS.md`, dependency lockfile, mô tả hệ thống trong 10 dòng đầu), không phản ánh lỗi trong các gate Solo-Code đã được chốt. Không đưa script này vào gate chính.

---

## 10. Cách tự kiểm chứng

```powershell
git status --short
python .github/scripts/security_scan.py .
python .github/scripts/check_skips.py tools/
python tools/validate_schemas.py
python tools/garden.py
python -m pytest tools/ -q
python tools/test_integration.py
python .github/scripts/checklist.py .
python tools/shared_state.py show
python tools/shared_state.py locks
```
