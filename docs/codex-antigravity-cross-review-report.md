# Báo cáo cross-review: Antigravity headless worker

> **Người nhận:** Codex (sửa lỗi theo danh sách F1–F11)
> **Nguồn yêu cầu:** `docs/deepseek-cross-review-antigravity.md`
> **Đối tượng review:** working tree chưa commit của tích hợp `agy.exe` headless worker
> **Mốc so sánh:** HEAD `ed6f5f3` + thay đổi chưa commit (21 file modified, 4 file untracked)
> **Ngày:** 2026-09-21
> **Nguyên tắc:** không kết luận nào dưới đây không có lệnh đã chạy hoặc đường code cụ thể.

---

## 1. Phương pháp và phạm vi

Đã đọc trực tiếp: `tools/antigravity_delegate.py`, `tools/shared_state.py`,
`tools/test_antigravity_delegate.py`, `tools/test_shared_state.py`, `tools/deploy.py`,
`tools/generate_harness.py`, `tools/opencode_engine.py`, `tools/claude_engine.py`,
`tools/garden.py`, `.claude/hooks/session_start.py`, `.harness.lock`, `opencode.json`,
`AGENTS.md`, `docs/antigravity-telemetry-hook.md`, và các mirror skill/memory.

Không sửa file nào trong repo. Mọi script kiểm chứng chạy ngoài repo tại
`C:\Users\Giang_PC\AppData\Local\Temp\kilo\`.

**Phân biệt bằng chứng:** mục 2 là lệnh đã chạy thật; các finding ghi rõ
`[đã chạy]` hay `[từ mã]`.

---

## 2. Trạng thái gate (đã chạy thật, 2026-09-21)

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tools/ -q --basetemp <Temp>\kilo\pytest-review-full` | **535 passed, 3 skipped** (44.9s) |
| `python -m pytest tools/test_antigravity_delegate.py tools/test_shared_state.py tools/test_deploy.py tools/test_garden.py tools/test_claude_hooks.py tools/test_claude_engine.py -q` | **174 passed** |
| `python tools/garden.py` | **0 drift issues** — "Garden is clean" |
| `opencode.json` vs `generate_opencode_json()` sinh vào temp | **parity = True** |
| `python .github/scripts/security_scan.py .` | **4 findings — KHÔNG sạch** (xem F11) |

Bằng chứng phụ:

```text
snapshot_workspace(repo root) = 12.053 file, 4.12s, có gồm .venv/.pytest_temp*
conflict dir:. vs file src/auth.py = False
conflict dir:. vs dir:src          = False
acquire_directory_lock(".") gemini -> True, rồi copilot vẫn lock được src/auth.py và dir:src
acquire_directory_lock("src") gemini chạy A -> True; chạy B cùng engine -> True; B release -> active_locks = []
parse_ndjson_events('{"event":"init","conversation_id":"c"}') -> error = None
parse_ndjson_events("not json") -> error = "Antigravity produced no NDJSON events"

scope demo (temp, junction):
  ghi file ngoài target_dir          -> changed = []            -> verdict []
  ghi xuyên junction trong allow-dir -> changed = ['src/link/keep.txt'] -> verdict []
  file thật ngoài cây                -> "OVERWRITTEN THROUGH"
```

---

## 3. Findings

| ID | Mức | File:line | Tóm tắt |
|---|---|---|---|
| F1 | **Critical** | `tools/antigravity_delegate.py:142-143` + `tools/shared_state.py:58-75` | `--allow-dir .` không khóa gì và không kiểm scope |
| F2 | **High** | `tools/antigravity_delegate.py:121-132, 171, 176` | Hậu kiểm chỉ trong `--target-dir`; ngoài cây và `.git` không phát hiện được |
| F3 | **High** | `tools/antigravity_delegate.py:29, 243-253` + `shared_state.py:333-335` | Lock cùng engine không chặn 2 worker song song |
| F4 | **Medium** | `tools/antigravity_delegate.py:263-273` | Scope check bị bỏ qua trên mọi nhánh lỗi; mã thoát 124 bị mất |
| F5 | **Medium** | `tools/antigravity_delegate.py:92-105` | Stream thiếu event `result` bị coi là thành công (exit 0) |
| F6 | **Medium** | `tools/antigravity_delegate.py:121-132` | Snapshot toàn workspace, không loại `.venv`/`node_modules`/`.pytest_temp*` → false positive |
| F7 | **Medium** | `tools/antigravity_delegate.py:108-118, 125` | Junction/symlink: ghi ra ngoài bị gán nhãn in-scope |
| F8 | **Medium** | `.copilot/skill/gemini-delegation/SKILL.md:3`, `.gemini/antigravity/skills/gemini-delegation/SKILL.md:3` | Frontmatter `description` mô tả sai cơ chế; không gate nào bắt |
| F9 | **Low** | `tools/test_antigravity_delegate.py` | Thiếu test cho `main`/`run_agy_cli`/`find_agy_binary` và mọi mã thoát |
| F10 | **Low** | `tools/opencode_engine.py:266` (sinh ra `opencode.json:21`) | Allowlist `"allow"` cho phép auto-chạy wrapper với mọi tham số |
| F11 | **Medium** | `.github/scripts/security_scan.py:67-83, 137-141` | Gate `security_scan` hiện đỏ do artifact local trong `.solocode/` |

---

### F1 — Critical: `--allow-dir .` vô hiệu hóa lock và scope check

**Đường code.** `paths_outside_directory()` trả `[]` khi `allowed_dir == "."`
(`antigravity_delegate.py:142-143`). `_lock_paths_conflict()` không có nhánh cho gốc
workspace: `dir:.` so với bất kỳ key nào đều không khớp prefix (`shared_state.py:58-75`).
`resolve_allowed_directory()` trả `"."` cho `--allow-dir .` (dòng 118).

**Bằng chứng `[đã chạy]`:**

```text
conflict dir:. vs file src/auth.py: False
conflict dir:. vs dir:src     : False
acquire_directory_lock('.') gemini: True
  then copilot locks src/auth.py: True
  then copilot dir-locks src   : True
locks: ['dir:.', 'src/auth.py', 'dir:src']
```

**Hệ quả.** `--auto-approve --allow-dir .` hợp lệ theo parser, vẫn gửi
`--dangerously-skip-permissions` cho `agy.exe`, nhưng **không lấy được lock độc quyền
và không có kiểm tra scope nào**. Đây là đường "tắt guardrail" âm thầm, trái với tuyên
bố trong `AGENTS.md`: "the wrapper takes a shared-state directory lock and checks the
post-run workspace scope".

**Fix tối thiểu (chọn 1, ghi rõ trade-off trong commit).**

- Phương án A (từ chối): trong `main()`, sau khi resolve, `parser.error("--allow-dir .
  grants the whole workspace; pass the narrowest directory")`. Trade-off: mất khả năng
  grant có chủ đích toàn workspace; nếu vẫn cần, thêm cờ riêng `--allow-workspace` để
  ý định là tường minh, không lẫn với `.`.
- Phương án B (sentinel): coi `dir:` (path rỗng) là khóa gốc, xung đột với **mọi** key
  khác trong `_lock_paths_conflict()`, và giữ `paths_outside_directory()` trả `[]` cho
  `.` (đúng ngữ nghĩa "toàn workspace"). Trade-off: `.` trở thành xung đột tuyệt đối,
  mọi engine khác không lock được file nào cho tới khi xong — đúng ý đồ nhưng chặn
  song song toàn repo.

Bắt buộc kèm test cho cả nhánh `dir:.` trong `tools/test_shared_state.py` và cho
`--allow-dir .` trong `tools/test_antigravity_delegate.py`.

---

### F2 — High: hậu kiểm chỉ có giá trị trong `--target-dir`

`snapshot_workspace()` chỉ đi trong `root`, và bỏ qua mọi path chứa `.git` hoặc
`.solocode` (`antigravity_delegate.py:125`). `--add-dir` nhận `target_dir` đầy đủ
(dòng 171); `--dangerously-skip-permissions` (dòng 176) không giới hạn thư mục.

**Bằng chứng `[đã chạy]`:**

```text
ghi file ngoài target_dir          -> changed = []  -> verdict []
ghi xuyên junction trong allow-dir -> changed = ['src/link/keep.txt'] -> verdict []
file thật ngoài cây                -> "OVERWRITTEN THROUGH"
```

**Hệ quả.** Thay đổi ngoài `target_dir`, và mọi thao tác git (commit, `git checkout -- .`,
reset index) đều vô hình với hậu kiểm. Guardrail chỉ là prompt — kiểm soát trước duy
nhất, và là khuyến nghị chứ không phải ràng buộc.

**Fix tối thiểu.** Không hứa quá mức trong tài liệu: đổi mô tả thành "phát hiện thay
đổi **trong `--target-dir`** ngoài `--allow-dir`". Nếu cần ràng buộc thật, phải là
kiểm soát trước (ví dụ từ chối chạy khi `--allow-dir` không bằng `--target-dir`, hoặc
chạy `agy` trong sandbox/không dùng `--dangerously-skip-permissions`). Không được coi
hậu kiểm là ranh giới an toàn.

---

### F3 — High: lock cùng engine không chặn hai worker Antigravity song song

`DIRECTORY_LOCK_ENGINE = "gemini"` là hằng số (`antigravity_delegate.py:29`), còn
`acquire_lock()` cho phép `owner == engine` ghi đè
(`shared_state.py:333-335`). Kết quả: mọi lần gọi wrapper đều cùng engine nên **không
bao giờ xung đột với nhau**.

**Bằng chứng `[đã chạy]`:**

```text
run A dir lock src: True
run B dir lock src: True
after B releases, active locks: []
```

**Hệ quả.** Hai delegation song song cùng scope đều chạy; cái nào xong trước xóa lock
của cái còn lại, nên engine thứ ba có thể chen vào giữa. Trả lời câu hỏi 4 của brief
("re-entry by same engine safe?"): an toàn cho một engine khóa nhiều file, **không** an
toàn cho nhiều worker cùng nhãn engine.

**Fix tối thiểu.** Truyền `session_id` duy nhất mỗi lần chạy
(`session_id=f"antigravity-{os.getpid()}"`), đồng thời cho xung đột khi trùng engine
nhưng khác `session_id` khác rỗng. Cần `SELECT path, engine, session_id` trong
`acquire_lock()` và test cho: hai session cùng engine → xung đột; cùng session → re-entry
vẫn cho phép.

---

### F4 — Medium: scope check bị bỏ qua trên nhánh lỗi; mã thoát timeout bị mất

`main()` trả `2` tại dòng 267 **trước** khối kiểm scope (dòng 268-273). Worker lỗi sau
khi đã ghi file chỉ báo lỗi, không kiểm scope. `run_agy_cli()` trả `124` khi timeout
(dòng 189) nhưng `main()` bỏ `exit_code` và luôn trả `2`, nên không phân biệt được
timeout với lỗi worker; trên timeout, tiến trình con của `agy` có thể còn sống và tiếp
tục ghi sau khi wrapper đã thoát.

**Fix tối thiểu.** Chạy khối kiểm scope khi `args.auto_approve` bất kể `result["error"]`;
ưu tiên trả `4` nếu có scope violation, và truyền tiếp `124` khi `exit_code == 124`.

---

### F5 — Medium: stream thiếu `result` bị coi là thành công

`parse_ndjson_events()` chỉ set `error` khi `not result["events"]` (dòng 103-104), không
kiểm tra có event `result` hay không.

**Bằng chứng `[đã chạy]`:**

```text
parse_ndjson_events('{"event":"init","conversation_id":"c"}')
-> {'text': '', 'status': None, 'usage': None, 'error': None}
```

**Hệ quả.** Stream cụt (agy thoát 0 sau `init`) → `main()` trả `0`, stdout rỗng, không
lỗi. Caller tin là thành công.

**Fix tối thiểu.** Thêm cờ `saw_result`; nếu không có event `result` thì
`error = "Antigravity stream ended without a result event"`.

---

### F6 — Medium: snapshot toàn workspace, dễ false positive

`snapshot_workspace()` chỉ loại `.git` và `.solocode`. Không loại `.venv`,
`node_modules`, `.pytest_temp*`, `__pycache__`, `.ruff_cache`, `.pytest_cache`.

**Bằng chứng `[đã chạy]`:** 12.053 file / 4,12s / 152MB ở repo này (chưa có
`node_modules`), có gồm `.venv` và `.pytest_temp*`. Brief ghi nhận `.pytest_temp` đang
tồn tại và pytest ghi vào đó.

**Hệ quả.** Với `--allow-dir src`, mọi churn đồng thời ở `.venv`/`.pytest_temp*` báo
"scope violation" và trả `4` dù worker không đụng tới. Tốn 2 lần snapshot mỗi lần ghi,
tăng theo kích thước cây.

**Fix tối thiểu.** Loại thêm `.venv`, `venv`, `node_modules`, `__pycache__`,
`.ruff_cache`, `.pytest_cache`, `dist`, `build`, và mọi tên khớp `.pytest_temp*`.

---

### F7 — Medium: junction/symlink làm sai nhãn scope

`snapshot_workspace()` dùng `path.is_file()` (đi theo link) và ghi khóa theo path tương
đối. Một junction nằm trong allowed dir trỏ ra ngoài khiến thay đổi **ngoài cây** được
ghi nhận là `src/link/keep.txt` — in-scope.

**Bằng chứng `[đã chạy]`:** junction tạo thật, `changed = ['src/link/keep.txt']`,
`verdict = []`, file ngoài cây bị `OVERWRITTEN THROUGH`.

**Fix tối thiểu.** Ghi nhận giới hạn này trong docstring + tài liệu (hậu kiểm không
phân biệt được ghi qua link); nếu muốn chặn, phải kiểm tra reparse point trước khi tin
snapshot.

---

### F8 — Medium: frontmatter mirror lệch, không gate nào bắt

Body đã đổi sang headless CLI ở cả hai mirror, nhưng `description:` giữ nguyên bản cũ
("...via the Antigravity IDE using the file-based inbox/outbox handoff"):

```
f318b394335d 7229 .copilot/skill/gemini-delegation/SKILL.md
f318b394335d 7229 .gemini/antigravity/skills/gemini-delegation/SKILL.md
cfcbdf610c88 7032 .kilo/skill/gemini-delegation/SKILL.md      (== .claude/skills/...)
```

`generate_harness.sync_skill_body_mirrors()` **cố ý** chỉ sync body
(`generate_harness.py:196-206`); `garden.check_skill_content()` **cố ý** bỏ qua
frontmatter (`garden.py:186-194`). Nên đây là lệch sẽ tồn tại vĩnh viễn nếu không sửa tay.

**Fix tối thiểu.** Sửa tay `description:` ở hai file trên cho khớp cơ chế mới, ví dụ:

```yaml
description: Routes read-heavy work, broad scoped changes, and independent review to Gemini through the Antigravity headless CLI (tools/antigravity_delegate.py). Use GUI inbox/outbox handoff only when a rendered UI needs human verification.
```

Không đổi sang cơ chế tự sinh frontmatter trong phạm vi fix này.

---

### F9 — Low: thiếu test cho hành vi và mã thoát

`tools/test_antigravity_delegate.py` có 8 test, chỉ phủ hàm thuần:
`parse_ndjson_events` (3), `resolve_allowed_directory` (1), `changed_workspace_paths` (1),
`paths_outside_directory` (1), `build_prompt` (2). **Không** test `main()`,
`run_agy_cli()`, `find_agy_binary()`, mã thoát `1/2/3/4/124`, lỗi parser
(`--auto-approve` thiếu `--allow-dir`, `--no-guardrail` + `--auto-approve`), hay NDJSON
cụt (F5).

**Fix tối thiểu.** Thêm test dùng `monkeypatch` cho `run_agy_cli`/`find_agy_binary` để
phủ: success → 0; lock bận → 3; scope violation → 4; lỗi worker → 2; timeout → 124;
thiếu `result` → lỗi; `pytest.raises(SystemExit)` cho các nhánh `parser.error`.

---

### F10 — Low: allowlist OpenCode mở quá rộng

`opencode.json:21` thêm `"python tools/antigravity_delegate.py *": "allow"`. Nguồn sinh
là `tools/opencode_engine.py:266` — **sửa generator, không sửa `opencode.json` trực tiếp**.
Với rule này, OpenCode auto-chạy wrapper ở mọi tham số, gồm `--auto-approve --allow-dir .`
(F1) và `--agy-bin <exe tuỳ ý>`.

**Fix tối thiểu.** Chuyển rule sang `"ask"`, hoặc giữ `"allow"` nhưng chỉ sau khi F1 đã
đóng. Ghi trade-off: read-only delegation là mục tiêu chính và `"ask"` làm chậm nhịp đó.

---

### F11 — Medium: gate `security_scan` hiện đỏ (không liên quan tích hợp Antigravity)

`python .github/scripts/security_scan.py .` trả **4 findings**:

```text
[SECRET: Hardcoded API key] .solocode\pytest-tools-default.out:358
[SECRET: Hardcoded API key] .solocode\pytest-tools-default.out:474
[SECRET: Hardcoded API key] .solocode\pytest-tools-default.out:28499
[SECRET: Hardcoded API key] .solocode\pytest-tools-default.out:28500
```

Nguyên nhân: `untracked_top_level_dirs()` chỉ bỏ qua thư mục không có file nào được git
theo dõi (`security_scan.py:137-141`). `.solocode/` có 2 file tracked
(`.solocode/executor-config.json`, `.solocode/executor-mode`) nên **không** nằm trong
danh sách bỏ qua; trong khi `.pytest_temp*`, `.venv` lại được bỏ qua. Artifact
`pytest-tools-default.out` (1.76MB, tạo 2026-09-21 14:41 local) là output test local
chứa fixture giả, nằm trong thư mục đã gitignore (`.gitignore:29`).

**Hệ quả.** Mâu thuẫn với bằng chứng trong brief ("No issues found"); pre-commit gate sẽ
đỏ. **Cảnh báo phạm vi:** không quy finding này cho thay đổi Antigravity — nó là artifact
local. Hai cách xử lý, chọn 1: (a) người dùng xóa artifact local (không phải fix code),
hoặc (b) thêm `.solocode` vào `SKIP_DIRS` của scanner vì đây là state dir chỉ tồn tại
local. Nếu chọn (b), phải chạy lại scan và chứng minh 0 findings, đồng thời thêm test cho
`should_skip()`.

---

## 4. Trả lời 10 câu hỏi của brief

| # | Câu hỏi | Kết luận |
|---|---|---|
| 1 | `resolve_allowed_directory()` chặn escape? | **Có** cho path tuyệt đối/tương đối và cho link ở tầng allowed-dir (`resolve()` + `relative_to`). **Không** cho link nằm trong allowed dir tạo lúc chạy (F7). |
| 2 | `snapshot_workspace()` có bị bypass/vô dụng/false positive? | Bỏ qua `.git`/`.solocode` (F2); file unreadable bị `except OSError: continue` bỏ im lặng (dòng 130-131); false positive do churn và chi phí (F6). |
| 3 | Hậu kiểm sau chạy đủ chưa? | **Chưa.** Kiểm soát trước duy nhất là prompt; không có ràng buộc nào cho thao tác ngoài `target_dir` (F2). |
| 4 | `dir:` xung đột đúng? Re-entry an toàn? | Đúng cho `src` vs `src/auth.py` (2 test mới pass) và cho biến thể `\`/`/`. **Trừ** gốc `.` (F1) và trừ chạy song song cùng engine (F3). |
| 5 | Release lock có thể fail/xóa lock người khác? | Không xóa lock engine khác (điều kiện `engine = ?`), nhưng **xóa lock của worker cùng nhãn engine đang chạy** (F3). Lock hết hạn sau 2h; nhánh thoát bất thường vẫn vào `finally`. |
| 6 | NDJSON lỗi, thiếu `result`, exit-code, timeout, Unicode? | Dòng JSON lỗi được bỏ qua (chấp nhận). **Thiếu `result` → false success** (F5). Timeout mất mã `124` và bỏ scope check (F4). Prompt Unicode/multiline truyền qua argv — chưa kiểm giới hạn ~32K ký tự của CreateProcess. |
| 7 | `--allow-dir .` nên chấp nhận hay từ chối? | Hiện tại là lỗ (F1). Chọn A (từ chối) nếu muốn đơn giản và an toàn; chọn B (sentinel khóa gốc) nếu muốn giữ grant toàn workspace tường minh. Ghi trade-off trong commit. |
| 8 | `opencode.json` giữ allowlist sau regenerate? | **Có** — parity = True, nguồn ở `tools/opencode_engine.py:266`. |
| 9 | Deploy copy wrapper, không ship test? | **Có** — `should_copy()` loại `test_*.py` theo rule (`deploy.py:741`); `.harness.lock` khai báo cả `tools/antigravity_delegate.py` và `tools/test_antigravity_delegate.py`. |
| 10 | Có file generated/mirror bị sửa sai nguồn? | Không file generated nào sai nguồn. `opencode.json` khớp generator. Nhưng frontmatter 2 mirror thủ công chưa cập nhật (F8). |

---

## 5. Chỉ dẫn fix cho Codex

**Thứ tự thực hiện:** F1 → F3 → F4 → F5 → F6/F7 → F8 → F9 → F10 → F11.
Lý do: F1/F3 là ranh giới an toàn; F4/F5 là tính đúng của mã thoát; phần còn lại là
chất lượng và gate.

**Được sửa (fence):**

```text
tools/antigravity_delegate.py
tools/shared_state.py
tools/test_antigravity_delegate.py
tools/test_shared_state.py
tools/opencode_engine.py          # chỉ dòng rule allowlist (F10)
opencode.json                     # chỉ được sửa qua generator, không sửa tay
.copilot/skill/gemini-delegation/SKILL.md        # chỉ dòng description (F8)
.gemini/antigravity/skills/gemini-delegation/SKILL.md   # chỉ dòng description (F8)
.github/scripts/security_scan.py  # chỉ khi chọn phương án (b) của F11
```

**Không được đụng trong nhiệm vụ này:**

- `docs/deepseek-cross-review-antigravity.md`, `docs/codex-antigravity-cross-review-report.md`
  (giữ `status`/nội dung; không viết lại báo cáo).
- `AGENTS.md`, `CLAUDE.md`, `.kilo/memory/MEMORY.md`, `.claude/memory/MEMORY.md`,
  `.copilot/memory/MEMORY.md` — trừ khi một fix ở trên làm chúng sai; nếu vậy báo lại
  trước, không tự sửa.
- `.harness.lock` — đã khai báo đúng cho thay đổi hiện tại.
- `tools/deploy.py`, `tools/generate_harness.py`, `tools/garden.py` — không phải nguyên
  nhân của finding nào ở đây.
- `docs/antigravity-telemetry-hook.md` — cấu hình local, không phải harness setting.

**Bắt buộc mỗi fix phải có bằng chứng, không viết "đã sửa" mà không chạy lệnh.**
Dùng bảng `| Claim | Command run | Output |`. Không viết kết luận nào bạn chưa chạy
lệnh để chứng minh.

**Sau khi sửa, chạy và dán output:**

```powershell
python -m pytest tools/test_antigravity_delegate.py tools/test_shared_state.py -q --basetemp ..\.pytest_temp_codex
python -m pytest tools/ -q --basetemp ..\.pytest_temp_codex_full
python tools/garden.py
python .github/scripts/security_scan.py .
python .github/scripts/checklist.py .
```

**Kỳ vọng đỏ hợp lệ.** Nếu F1 chọn phương án A (từ chối `.`), test cũ
`test_paths_outside_directory_uses_path_boundaries` vẫn xanh vì nó test hàm thuần, nhưng
một test mới cho `main` với `--allow-dir .` phải là `SystemExit`. Nếu F10 chuyển rule
sang `"ask"`, file `opencode.json` phải được sinh lại bằng
`python tools/generate_harness.py --harness all` — đừng sửa tay.

---

## 6. Việc chưa làm / độ tin cậy

- Chưa chạy `python .github/scripts/checklist.py .` trong phiên review này (chỉ chạy
  full pytest + garden + security_scan). Người nhận cần tự chạy để xác nhận.
- Chưa kiểm giới hạn độ dài command line của `agy.exe` với prompt lớn (câu 6).
- Chưa kiểm hành vi thật của `agy.exe` — mọi kết luận về `agy` dựa trên hợp đồng đã ghi
  trong brief (version 1.1.27, các trường NDJSON).
- Chưa đo lại `check_skips.py` và `ruff check .`.
- Kết luận tổng: cơ chế chính (parser, chuẩn hóa lock, READ-ONLY mặc định, deploy,
  parity `opencode.json`) đúng và các gate hiện có xanh (trừ F11). Rủi ro thật nằm ở
  **F1–F3** — ba đường khiến "lock + scope check" bị vô hiệu. Không nên coi wrapper là
  ranh giới an toàn cho ghi cho tới khi F1–F3 được xử lý.
