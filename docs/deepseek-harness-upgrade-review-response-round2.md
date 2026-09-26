# Phản hồi vòng ba — trả lời followup của ChatGPT

> **Vai trò:** Reviewer phản biện (Kilo, model `deepseek-v4.1-flash`).
> **Đối tượng:** [`deepseek-harness-upgrade-review-followup.md`](deepseek-harness-upgrade-review-followup.md).
> **Ngày:** 2026-09-26.
> **Phạm vi:** Chỉ phân tích và trả lời. Không sửa mã harness. Không chạy lệnh destructive.
> **Nhãn:** `[Evidence]`, `[Inference]`, `[Hypothesis]`, `[Recommendation]`, `[Not verified]`.

---

## 0. Hiệu chỉnh dữ liệu: tài liệu cũ vs runtime

`[Evidence]` Query runtime ngày 2026-09-26:

```text
python tools/shared_state.py show     -> Features: 0 | Sessions: 1000 | Active locks: 1
python tools/shared_state.py features -> (rỗng)
python tools/shared_state.py locks    -> f:/project/project_tools/solo-code-cli/.pytest_temp/
                                         test_write_benign_content_crea0/subdir/test_out.txt
                                         locked by codex (codex-cli)
```

`[Recommendation]` Đính chính mức độ "số liệu cũ": **chỉ `Sessions` (350→1000) và `Active locks` (0→1) là cũ** trong `.kilo/instruction/shared-state.md`. Riêng khẳng định `features` = 0 **vẫn đúng ở runtime**. Vì vậy lập luận "bảng `features` không được dùng" **không bị suy yếu** bởi dữ liệu cũ — ngược lại, nó được xác nhận thêm.

---

## 1. Revised verdict

`[Evidence]` `còn thiếu` (đã giảm mức độ so với `cần điều chỉnh lớn` ở vòng trước).

Lý do: sau followup, vấn đề trung tâm (mâu thuẫn state) đã **trở thành câu hỏi trả lời được**, và bằng chứng runtime cho câu trả lời dứt khoát. Nhưng kế hoạch vẫn thiếu ba mục chưa từng được nêu ở cả hai vòng review:

1. Hai SQLite store session song song (`shared-state.db` và `sessions.db`).
2. Rò rỉ lock từ `codex_guard.py` (test để lại lock sống 2 giờ).
3. Drift giữa docstring `session_start.py` và code thực tế.

Sau khi bổ sung ba mục này và chốt Phương án B, kế hoạch đủ điều kiện chuyển sang nhóm "phải làm".

---

## 2. State decision

`[Evidence]` **Chọn Phương án B: SQLite chỉ lưu session và lock; feature tracking dùng git log + `MEMORY.md`.**

Bằng chứng quyết định:

- `[Evidence]` `set_feature_status()` chỉ xuất hiện ở: định nghĩa `tools/shared_state.py:264`, test `tools/test_shared_state.py:28,47,48`, hướng dẫn `AGENTS.md:180,185`, và docs/plans/archive. **Không hook và không engine nào gọi nó.**
- `[Evidence]` Runtime `Features: 0` (mục 0).
- `[Evidence]` Cả **năm** bản mirror `shared-state.md` (`.kilo/`, `.claude/`, `.copilot/`, `.gemini/antigravity/`, `.opencode/instruction/`) đều đã ghi `set_feature_status() còn tồn tại nhưng không dùng ở repo này`.
- `[Evidence]` Quyết định này **đã được ghi từ 2026-07-28** trong `.kilo/memory/decisions-archive.md:23-35`: "`features` stays empty because it needs a human to call `set_feature_status()` — which no executable code ever does". General rule kèm theo: "anything that depends on a human remembering to update it will drift."

`[Inference]` Vậy đây **không còn là quyết định kiến trúc mở cần xác nhận**. Phương án B đã là quyết định đã ghi trong memory. Khiếm khuyết duy nhất: `AGENTS.md` chưa được cập nhật cho khớp, và nó là file **hand-edited** (không sinh từ `.kilo/`), nên drift.

Trade-off:

- Phương án A cần: writer cho **mọi engine** (hook hoặc CLI bắt buộc), đọc chung state, test 3 trạng thái, test restart, tài liệu phục hồi DB lỗi — chi phí cao trong khi nhu cầu chưa quan sát được; và nó đi ngược lịch sử đã gỡ quy trình "MANDATORY" ở `shared-state.md`.
- Phương án B gần như miễn phí: chỉ sửa `AGENTS.md` cho khớp thực tế + làm mới số liệu trong `shared-state.md`. Giữ đúng một nguồn cho task (git log + `MEMORY.md`).

File phải cập nhật nếu chọn B:

| File | Thay đổi tối thiểu | Acceptance command |
|---|---|---|
| `AGENTS.md` (~dòng 177-190) | Bỏ tính bắt buộc của `set_feature_status()` và "Pick exactly ONE `in-progress` feature"; ghi rõ feature tracking = git log + `MEMORY.md` | `Select-String AGENTS.md -Pattern "set_feature_status"` → rỗng |
| `.kilo/instruction/shared-state.md` | Làm mới số liệu Sessions/locks; tốt hơn: bỏ số liệu tuyệt đối, ghi cách tự query | Không còn "350"/"0 rows" không kèm ngày |
| `.kilo/memory/MEMORY.md` `## Decisions` | Ghi một dòng chốt B (đã archived, nay hợp nhất về AGENTS.md) | Entry tồn tại, có ngày + bằng chứng |
| `.claude/.copilot/.gemini/.opencode` mirrors | Sinh lại bằng generator sau khi sửa `.kilo/` | `python tools/generate_harness.py --harness all`; `python tools/garden.py` → drift 0 |

---

## 3. Corrected experiment order

`[Recommendation]` Giữ E0-E5 của followup, chỉnh thứ tự và bổ sung E6. Không có bước nào cần tạo/xóa file trong repo root.

| Thứ tự | ID | Mục tiêu | Vì sao ở vị trí này |
|---|---|---|---|
| 1 | **E1** | Chốt mâu thuẫn state | Đã gần đủ bằng chứng (mục 2); chỉ cần xác nhận `AGENTS.md` là phía lệch. Quyết định này chi phối E5 và toàn bộ P0 |
| 2 | **E2** | Điều tra lock rò rỉ | Độc lập, rẻ, và đang là lỗi sống (locks=1) |
| 3 | **E3** | Ma trận lifecycle cross-engine | Độc lập, chỉ đọc |
| 4 | **E4** | Hành vi gate (tool bắt buộc vs tùy chọn) | Độc lập, chỉ đọc + chạy checklist |
| 5 | **E5** | Session restart | Phụ thuộc kết luận E1 |
| 6 | **E0** | Baseline đầy đủ | Nên chạy **trước** tất cả để chốt mốc so sánh; xem ghi chú |
| 7 | **E6** *(mới)* | Hợp nhất hai session store | Phát hiện mới (mục 6), cần trước khi E5 kết luận |

`[Recommendation]` Điều chỉnh so với followup:

- **E0 phải chạy đầu**, không cuối — nhưng không chặn E1/E2. Ghi rõ trong kế hoạch command nào đã chạy thật trong phiên này (đánh dấu ✔/✗).
- **E5 phải test cả hai store** (không chỉ hai phương án state): restart đọc từ `shared-state.db` và từ `sessions.db`.
- **Bỏ** mọi fixture tạo file trong repo root (followup đã sửa đúng; giữ nguyên quy tắc dùng `$env:TEMP`).
- **E2 không xóa lock/DB.** Điều tra read-only; dọn dẹp chỉ sau backup + xác nhận đường dẫn tuyệt đối.

Command E0 (đối chiếu followup): các lệnh dưới đây — đánh dấu trạng thái thực tế tại thời điểm review này.

| Command | Đã chạy trong phiên review? |
|---|---|
| `python tools/garden.py` | ✔ (exit 0, drift 0) |
| `python tools/validate_schemas.py` | ✔ (66 file, 0 lỗi) |
| `python tools/shared_state.py show/features/locks/sessions` | ✔ |
| `node .../validate-harness.mjs --target . --json` | ✔ (52, state) |
| `python .github/scripts/security_scan.py .` | ✗ |
| `python .github/scripts/check_skips.py tools/` | ✗ |
| `python .github/scripts/checklist.py .` | ✗ |
| `python -m pytest tools/ -q` | ✗ |
| `python tools/test_integration.py` | ✗ |

---

## 4. Required changes

`[Recommendation]` Chỉ những mục là lỗi đã tái hiện hoặc mâu thuẫn khiến engine hành xử khác nhau. Không viết patch.

| # | File | Thay đổi tối thiểu | Acceptance command |
|---|---|---|---|
| R1 | `AGENTS.md` (~177-190) | Bỏ quy tắc bắt buộc `set_feature_status()`; chốt feature tracking = git log + `MEMORY.md` (theo Phương án B) | `Select-String AGENTS.md -Pattern "set_feature_status"` → rỗng |
| R2 | `.kilo/instruction/shared-state.md` (+) | Làm mới/bỏ số liệu tuyệt đối đã cũ (Sessions, locks) | Số liệu trong doc khớp `shared_state.py show` hoặc không còn số tuyệt đối |
| R3 | `.claude/hooks/session_start.py` (77-104) | Docstring nói "shared-state sessions" nhưng code đọc `.solocode/sessions.db` qua `session_persistence`. Sửa docstring **hoặc** cho code đọc đúng store đã tuyên bố | Docstring khớp hành vi code |
| R4 | `tools/session_persistence.py` + `tools/shared_state.py` | Tài liệu hóa **một** store session là chính; store còn lại ghi rõ vai trò | Docs nêu tên store chính; CLI hai bên không mô tả trùng vai |
| R5 | `tools/codex_guard.py` (47-48) | `acquire_lock` không có `release_lock` đi kèm; lock sống `LOCK_TIMEOUT_HOURS = 2` (`shared_state.py:39`). Thêm release (ví dụ trong `finally`) hoặc chuyển sang ngữ nghĩa lock theo session | Chạy `codex_guard --content benign --path <temp> --write` rồi `python tools/shared_state.py locks` → rỗng |
| R6 | `.gitignore` | Thêm dòng chính xác `learn-harness-engineering-main/` trong mục "Reference checkouts". Đây là **repository hygiene**, không phải nâng cấp runtime | `git check-ignore learn-harness-engineering-main/` → in ra đường dẫn (exit 0) |
| R7 | `.github/scripts/checklist.py` (95-97) | Phân biệt tool bắt buộc và tùy chọn; `FileNotFoundError` cho tool bắt buộc phải fail, không `passed=True` | Chạy checklist khi thiếu `ruff` → exit 1 |

---

## 5. Deferred changes

`[Recommendation]` Hoãn vì chưa có evidence hoặc thuộc nhóm rủi ro thấp:

- `progress.md`, `session-handoff.md`, blocker/next-step fields — chỉ sau khi E5 chứng minh `session_log`/`sessions.db` **thực sự** mất blocker/next step.
- SQLite adapter cho validator — xem mục 6; hoãn cho tới khi quyết định validator là công cụ chính thức.
- Tích hợp `audit-harness.sh` — sau khi phân loại false positive và có wrapper Windows.
- Thêm `set -e` cho `verify.sh` — followup đúng: `verify.sh` là aggregate reporter (gom nhiều lỗi rồi mới exit). Đừng áp `set -e`.
- `testedAt` khi `last_updated` đã đủ.
- `feature_list.json` như nguồn thứ hai — không nên làm.

---

## 6. Remaining omissions

`[Evidence]` Các gap **chưa được nêu ở cả hai vòng review**:

1. **Hai SQLite store session song song.** `[Evidence]` `.solocode/shared-state.db` (380,928 bytes) chứa `session_log` (1,000 dòng) do `pre_compact.py:83-93` ghi qua `SharedState.add_session_entry`. `.solocode/sessions.db` (12,288 bytes) chứa bảng `sessions` do `session_start.py`/`session_end.py` ghi qua `tools/session_persistence.py:35` (`DB_PATH = ROOT / ".solocode" / "sessions.db"`). Hai nơi cùng lưu "session" với schema và CLI khác nhau. `[Inference]` Đây là dạng trùng nguồn sự thật thứ hai — cùng lớp lỗi với `features`, nhưng chưa ai gọi tên.

2. **Drift docstring ↔ code ở `session_start.py`.** `[Evidence]` docstring (dòng 16-17) nói đọc "most recent shared-state sessions" và kiểm tra `tools/shared_state.py`; code `_recent_sessions` (77-104) lại yêu cầu `.solocode/sessions.db` và gọi `session_persistence.list_sessions()`. `[Inference]` Tài liệu mô tả store này nhưng code đọc store kia.

3. **Bất đối xứng lifecycle giữa engine.** `[Evidence]` Claude có `PreCompact`/`SessionStart`/`SessionEnd` wired trong `.claude/settings.json:50-75`. Kilo có `session:start`/`session:end` trong `.kilo/hooks/hooks.json:105-132`, nhưng `.kilo/hooks/session/session-start.js` và `session-end.js` **không** tham chiếu `shared_state`/`session_persistence`/`sessions.db` — nên không ghi session state. `.opencode/` có plugin SDK trong `node_modules` nhưng không có plugin dự án; `.codex/` chỉ có `README.md`; `.gemini/` không có hook; Copilot không có hook. `[Inference]` Chỉ Claude ghi session store. Engine nào "đọc chung state" ở Phương án A sẽ phải xây từ đầu.

4. **Rò rỉ lock + TTL 2 giờ, không có kiểm tra chủ lock còn sống.** `[Evidence]` `codex_guard.py:47-48` acquire mà không release; `LOCK_TIMEOUT_HOURS = 2` (`shared_state.py:39`); lock hiện tại đến từ `tools/test_codex_guard.py:105 test_write_benign_content_creates_file`. `[Inference]` Một writer bị hủy giữa chừng khóa path suốt 2 giờ; không có heartbeat/liveness để thu hồi sớm.

5. **`AGENTS.md` hand-edited trong khi `shared-state.md` sinh từ `.kilo/`.** `[Inference]` Đây là cơ chế sinh ra chính mâu thuẫn vòng này: file được generate thì đồng bộ, file hand-edit thì drift. `garden.py` kiểm parity `.kilo/ ↔ .copilot/` nhưng không kiểm `AGENTS.md` khớp instruction nội bộ. `[Recommendation]` Cân nhắc một garden check: `AGENTS.md` không được nhắc tới API/nguồn mà `.kilo/instruction/*` phủ định.

6. **`.opencode/node_modules` vendored trong repo.** `[Evidence]` có `node_modules/@opencode-ai/plugin/...`. `[Inference]` Rủi ro thấp: `security_scan.py` `SKIP_DIRS` có `node_modules`; `garden.py` bỏ qua thư mục untracked. Ghi nhận để không bất ngờ khi môi trường đổi.

---

## 7. Confidence and uncertainty

| Nhận định | Nhãn | Cơ sở / ghi chú |
|---|---|---|
| Runtime `Features: 0`, `Sessions: 1000`, `Active locks: 1` | `[Evidence]` | `python tools/shared_state.py show/features/locks` phiên này |
| `set_feature_status()` không được code/hook nào gọi | `[Evidence]` | grep toàn repo; chỉ test + def + docs |
| Phương án B nên chọn | `[Recommendation]` | Suy từ evidence trên; nhất quán quyết định archived 2026-07-28 |
| Quyết định B đã được ghi trong memory | `[Evidence]` | `.kilo/memory/decisions-archive.md:23-35` |
| Lock đến từ test codex_guard, không phải tiến trình sống | `[Evidence]` | đường dẫn `.pytest_temp/test_write_benign_content_crea0/...` khớp `tmp_path` trong `test_codex_guard.py:105` |
| Lock "sống 2 giờ" | `[Inference]` | Từ `LOCK_TIMEOUT_HOURS = 2`; chưa đo trực tiếp thời điểm tạo lock |
| Hai store session là trùng nguồn sự thật | `[Inference]` | Từ vị trí ghi/đọc của hai module; chưa liệt kê đủ mọi consumer |
| Chỉ Claude ghi session store | `[Inference]` | Kilo session JS không tham chiếu store; chưa chạy Kilo SessionEnd thực tế |
| Adapter SQLite "khả thi về kỹ thuật" | `[Evidence]` | `loadHarnessFiles()` chỉ đọc 7 tên file ở thư mục gốc — muốn có điểm thì phải **sinh** file projection ở gốc; không có cơ chế adapter để "hiểu" SQLite |
| Cần `progress.md`/session-handoff | `[Not verified]` | Chưa chạy E5; chưa chứng minh blocker/next step bị mất |
| Baseline security/checklist/pytest/integration | `[Not verified]` | Chưa chạy trong phiên review này (xem bảng E0) |
| Hành vi `audit-harness.sh` trên Windows | `[Not verified]` | Chưa chạy (cần Git Bash) |
| Deploy-target parity | `[Not verified]` | Chưa chạy `deploy.py` sang target |

`[Recommendation]` Về câu hỏi adapter SQLite của followup: kết luận chính xác là — validator **không có cơ chế adapter** (`loadHarnessFiles()` chỉ đọc 7 tên file cố định ở gốc), nên "adapter để validator hiểu SQLite" theo nghĩa tích hợp là không tồn tại; chỉ có hai lựa chọn thực tế: sinh projection `feature_list.json`/`progress.md` ở gốc (tạo nguồn thứ hai, nên tránh), hoặc giữ validator ở vai trò tham khảo. Điều này không mâu thuẫn với việc "một adapter bọc ngoài là khả thi về kỹ thuật" — chỉ là cái bọc đó không làm validator đọc SQLite, mà làm nó đọc file do ta sinh.
