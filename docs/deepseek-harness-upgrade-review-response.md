# Phản biện kế hoạch nâng cấp Solo-Code-CLI

> **Vai trò:** Reviewer phản biện (Kilo).
> **Đối tượng review:** [`deepseek-harness-upgrade-review-plan.md`](deepseek-harness-upgrade-review-plan.md).
> **Ngày:** 2026-09-26.
> **Phạm vi:** Chỉ phân tích và phản biện. Không sửa mã nguồn harness được review. File này là báo cáo trả lời, không phải thay đổi code.
> **Quy ước nhãn:** mỗi nhận định được gắn `[Bằng chứng]` (quan sát được, kèm command/output), `[Suy luận]`, `[Giả thuyết]` hoặc `[Đề xuất]`.

---

## 0. Phương pháp và bằng chứng nền

Các command đã chạy (Windows PowerShell 5.1, Node v22.23.2):

```text
git status --short ; git branch --show-current
node learn-harness-engineering-main/skills/harness-creator/scripts/validate-harness.mjs --target . --json
python tools/garden.py
python tools/validate_schemas.py
(Get-Content learn-harness-engineering-main/tools/audit-harness.sh | Measure-Object -Line).Lines
```

Kết quả thô:

- `[Bằng chứng]` Validator tái hiện **`overall=52, bottleneck=state`** — số liệu trong kế hoạch là đúng.
- `[Bằng chứng]` `audit-harness.sh` = **438 dòng** — khớp với đính chính trong kế hoạch.
- `[Bằng chứng]` `tools/garden.py` → exit 0, "Total drift issues: 0".
- `[Bằng chứng]` `tools/validate_schemas.py` → "Files checked: 66, Errors: 0".
- `[Bằng chứng]` `ruff 0.15.15` có trong PATH.
- `[Bằng chứng]` `git status --short` cho thấy `?? learn-harness-engineering-main/` và `?? docs/` đang untracked; nhánh `main`.

---

## 1. Executive review

**Đánh giá tổng thể: `cần điều chỉnh lớn`.**

Kế hoạch đúng về cấu trúc (4 giai đoạn, phân loại finding, không thần thánh hoá structural benchmark) và đúng về số liệu validator. Nhưng nó **thiếu nghiêm trọng ở đầu vào finding** và **sai ở tiền đề P0/P1**, nên nếu thực thi nguyên trạng sẽ dẫn tới hoặc tài liệu hoá một quy trình không chạy, hoặc tạo nguồn sự thật thứ hai.

**Ba rủi ro lớn nhất:**

1. **Tiền đề "SQLite là nguồn feature state chính" (P0) trái với tài liệu hiện hành của chính repo.** `[Bằng chứng]` `.opencode/instruction/shared-state.md` ghi bảng `features` = **0 rows, "Không ai — dùng git log + MEMORY.md thay thế"**, đồng thời ghi rõ một quy trình session "MANDATORY" 9 bước trước đây **đã bị gỡ vì 0/9 bước thực sự chạy**. `[Bằng chứng]` Ở chiều ngược lại, `AGENTS.md:179-181` lại ra lệnh "Pick exactly ONE `in-progress` feature … Do NOT work on multiple features in one session". **Hai tài liệu auto-loaded tự mâu thuẫn.** Kế hoạch không phát hiện mâu thuẫn này.

2. **Danh sách finding của kế hoạch thiếu 3/13 check thất bại, trong đó có một gap thật.** `[Bằng chứng]` Validator thực tế fail **13 check** (bảng đầy đủ ở mục 2), kế hoạch chỉ nêu 6. Hai check bị bỏ sót là false negative do khớp từ khoá; một check bị bỏ sót — **`Verification fails fast`** — là gap thật: `init.sh:14` chỉ có `set -u`, `verify.sh:3` cũng chỉ `set -u`, không có `set -e`.

3. **`learn-harness-engineering-main/` chưa được `.gitignore` loại trừ.** `[Bằng chứng]` `.gitignore` có mục "Reference checkouts of upstream projects … Never committed" liệt kê `deepseek-harness-master/`, `open-code-review-main/`, `antigravity-sdk-python-main/` — **thiếu** `learn-harness-engineering-main/` (2478 file, đang `??`). `[Suy luận]` Hiện `security_scan.py` tự loại nó nhờ `untracked_top_level_dirs()` (dòng 106-142), nhưng cơ chế đó chỉ đúng chừng nào thư mục còn untracked; một `git add -A` sẽ hút trọn nó vào history và vô hiệu hoá cơ chế loại trừ.

**Một đề xuất cần thay đổi ngay:** trước khi làm P0/P1, **chốt mô hình state** (SQLite-only hay file-based projection) và **thêm `learn-harness-engineering-main/` vào `.gitignore`**. Hai việc này rẻ, chặn rủi ro lớn, và quyết định toàn bộ hướng P0→P2.

---

## 2. Missing checks

`[Bằng chứng]` 13 check thất bại thực tế từ validator:

```text
FAIL instructions: Definition of done documented
FAIL instructions: State artifacts routed from instructions
FAIL state: Feature tracker exists
FAIL state: Feature tracker is valid and has feature fields
FAIL state: Progress log exists
FAIL state: Progress log supports restart
FAIL state: Handoff captures blockers/files/next step
FAIL verification: Verification fails fast
FAIL scope: One-feature-at-a-time rule exists
FAIL scope: Feature dependencies are tracked
FAIL scope: Completion gate limits scope closure
FAIL lifecycle: Session handoff template exists
FAIL lifecycle: Session restart markers exist
```

Kế hoạch bỏ sót 3 check: `Definition of done documented`, `State artifacts routed from instructions`, `Verification fails fast`.

| Mục còn thiếu | Vì sao quan trọng | Command/test đề xuất | Mức độ |
|---|---|---|---|
| Mâu thuẫn `AGENTS.md` ↔ `.opencode/instruction/shared-state.md` về feature state | Hai tài liệu auto-loaded mâu thuẫn; agent không biết tin cái nào; P0/P1 đang xây trên giả định sai | So khớp trực tiếp hai file; quyết định một nguồn | **Cao** |
| `Verification fails fast` (init.sh `set -e`) | Entrypoint bootstrap không fail-fast; gate có thể báo OK dù bước trước lỗi | `Select-String -Path init.sh -Pattern 'set -e'`; thêm dòng lỗi giả vào init.sh và xem exit | **Cao** |
| `learn-harness-engineering-main/` chưa ignore | `git add -A` hút 2478 file bên thứ ba; phá auto-exclude của security_scan; đúng failure mode 248 false positive đã có tiền lệ | `git check-ignore learn-harness-engineering-main/`; `git status --short` | **Cao** |
| Lock/concurrency cross-engine chưa có thí nghiệm | `AGENTS.md` nói lock là cơ chế chống ghi đè duy nhất giữa engine, nhưng Phase 3 không test | 2 tiến trình `acquire_lock` cùng path, khác engine → kỳ vọng cái thứ hai `False` | **Cao** |
| Lock expiration chưa test | `active_locks` có `expires_at` và `_expire_locks()` nhưng chưa có bằng chứng hết hạn đúng | Acquire với TTL ngắn, chờ quá hạn, `get_active_locks()` → kỳ vọng rỗng | Trung bình |
| Generator idempotency + garden re-run | P3 nói "generated drift" nhưng không có bước regenerate-rồi-diff | `python tools/generate_harness.py --harness all` rồi `python tools/garden.py` → kỳ vọng drifts=0 và `git diff` rỗng | Trung bình |
| Deploy-target validation | Sản phẩm của harness là deploy sang project đích; điểm 52 của repo này không đại diện target | `python tools/deploy.py deploy <tmp>` rồi chạy validator/garden trên target | **Cao** |
| `checklist.py` bỏ qua tool thiếu | `FileNotFoundError` → `passed=True, skipped=True`; gate có thể PASS khi thiếu `ruff` | `checklist.py` trên PATH không có ruff → soi dòng "Ruff Linter" | **Cao** |
| Cross-engine parity (OpenCode/Codex) | Kế hoạch nêu OpenCode và Codex nhưng Phase 3 không kiểm tra rulebook mirror | Chạy `opencode` / `codex` hook test; đối chiếu `.claude/` ↔ `.opencode/` | Trung bình |
| Subagent seam chưa được enforce | `SubagentResult` tách evidence/summary nhưng chưa có provider nào implement Protocol | Đọc `tools/subagent_seam.py`; kiểm tra `opencode_delegate` có trả evidence không | Trung bình |
| Session restart thực (đã liệt kê 3.4) | Cần thiết, nhưng phải chạy thật chứ không mô tả | Kịch bản A→B như kế hoạch, lưu output 2 phiên | Trung bình |

---

## 3. False-positive risks

| Công cụ/finding | Vì sao có thể sai | Cách xác minh |
|---|---|---|
| Validator `One-feature-at-a-time rule exists` | `[Bằng chứng]` `harness-utils.mjs:252` chỉ khớp literal `'One feature at a time'` / `'one-feature-at-a-time'`. `AGENTS.md:179-181` có quy tắc nhưng diễn đạt khác ("Pick exactly ONE … Do NOT work on multiple features"). → **False negative.** | Đọc `harness-utils.mjs:252`; so `AGENTS.md:179-181` |
| Validator `Definition of done documented` / `Completion gate limits scope closure` | `[Bằng chứng]` `:233` cần literal `'Definition of Done'` hoặc `'done only when'` trong dòng có cấu trúc. `AGENTS.md:375` có "Verification Gates / Before marking any task complete, verify:" — cùng ý, khác chữ. → **False negative.** | Đọc `harness-utils.mjs:233,256` |
| Validator `state` subsystem | `[Bằng chứng]` `loadHarnessFiles()` (`:336-354`) chỉ đọc **7 tên file ở thư mục gốc**; không có cơ chế adapter/plugin. SQLite không bao giờ được đọc. → "gap" ở đây là **giới hạn của công cụ**, không phải thiếu sót của harness. | Đọc `harness-utils.mjs:336-354`; thử đặt `feature_list.json` giả ở gốc rồi chạy lại |
| Validator `state` floor | `[Bằng chứng]` `score = Math.max(1, round(passed/total*5))` (`:269`) — subsystem 0/5 vẫn được 1 điểm. → Không phản ánh "một phần năm năng lực". | Đọc `harness-utils.mjs:269` |
| `audit-harness.sh` (công cụ tham khảo) | `[Suy luận]` Là shell generic, bash-only, không biết mô hình đa engine/`.kilo/` là source of truth. Nếu đưa vào gate sẽ tạo finding trùng với `garden.py`/`boundary_audit.py` và fail trên PowerShell. | `bash audit-harness.sh .` trên Git Bash; đối chiếu finding với `garden.py` |
| `checklist.py` Ruff check | `[Bằng chứng]` `checklist.py:95-97` bắt `FileNotFoundError` → coi như PASS. Máy thiếu `ruff` báo gate xanh. | Tạm ẩn ruff khỏi PATH rồi chạy `checklist.py` |
| `security_scan.py` trên reference repos | `[Bằng chứng]` Cơ chế loại trừ dựa trên "thư mục 0 file tracked" (`:106-142`). `[Suy luận]` Nếu reference repo được commit, cơ chế hết hiệu lực → quét 2478 file bên thứ ba → nhiễu. Docstring `:114` ghi tiền lệ "pushed the gate to 248 false positives". | `git add -A` trên bản nháp rồi chạy scan; hoặc thêm ignore rồi xác nhận |

---

## 4. Architecture review

### 4.1 SQLite state
`[Bằng chứng]` `tools/shared_state.py:102-156` có đủ bảng `features`, `session_log`, `active_locks`, `shared_memory_*`. `VALID_STATUSES` (`:42`) = `not-started/in-progress/completed/blocked`.
`[Bằng chứng]` `.opencode/instruction/shared-state.md` ghi `features` = 0 rows, `shared_memory_*` = 0 rows, chỉ `session_log` có dữ liệu (do hook tự ghi).
`[Suy luận]` Kết luận rủi ro số 1: SQLite mạnh về hạ tầng nhưng **feature state chưa từng hoạt động**. Trước khi tuyên bố nó là "nguồn sự thật chính", cần quyết định giữ hay gỡ; nếu giữ phải có cơ chế ghi thật sự (hook/CLI bắt buộc), nếu không thì rủi ro là tài liệu hoá điều không tồn tại — đúng điều mà `shared-state.md` vừa gỡ.

### 4.2 Lifecycle hooks
`[Bằng chứng]` Hook tự động ghi `session_log` cho Claude Code (`.claude/hooks/session_start.py`, `session_end.py`, `pre_compact.py`). Kilo có `.kilo/hooks/...`; Codex/OpenCode không có hook lifecycle tương đương trong mô tả.
`[Suy luận]` Đây là **điểm parity lệch giữa các engine**: cùng một repo nhưng Claude Code có observability tự động còn engine khác phải gọi tay. Kế hoạch Q6 hỏi "cross-engine parity" nhưng Phase 3 không có bước kiểm tra.

### 4.3 Generated engine files
`[Bằng chứng]` `tools/generate_harness.py` lấy `.kilo/` làm source of truth, sinh `.claude/`, `.opencode/`, và mirror sang `.copilot/`, `.gemini/antigravity/`. `tools/garden.py` kiểm tra parity `.kilo/ ↔ .copilot/` và drift `.claude/`.
`[Bằng chứng]` `garden.py` hiện sạch (drift = 0); `validate_schemas.py` 0 lỗi.
`[Đề xuất]` Vì `.kilo/` là nguồn cho instructions/skills, còn task state nằm nơi khác, tài liệu P0 phải phân biệt rõ **3 tầng nguồn sự thật**: (1) `.kilo/` cho instruction/skill/agent, (2) git log + `MEMORY.md` cho lịch sử/decision, (3) SQLite cho session/lock. Validator đang nhắm tầng thứ tư (`feature_list.json`), nên đừng trộn ba tầng kia vào lập luận.

### 4.4 Locks / concurrency
`[Bằng chứng]` `shared_state.py` dùng WAL + `BEGIN IMMEDIATE` (`_ImmediateTransaction`), có retry khi khởi tạo DB đồng thời (`_INIT_RETRY_ATTEMPTS = 10`, comment ghi đã tái hiện bug), lock có `expires_at`, hỗ trợ directory lock và release theo `session_id`.
`[Suy luận]` Hạ tầng lock **mạnh hơn mức kế hoạch giả định** (kế hoạch coi như cần làm P1/P2). Việc còn thiếu là **bằng chứng vận hành**, không phải code. Điều này củng cố đề xuất: chuyển lock từ "P1 phải làm" sang "thí nghiệm bắt buộc".

### 4.5 Evidence model
`[Bằng chứng]` `tools/subagent_seam.py:59-88` tách `evidence` (facts máy kiểm được) khỏi `summary` (prose không tin), kèm `stop_reason` union kín.
`[Suy luận]` Đây là contract đúng hướng. Nhưng `:24-27` ghi rõ provider hiện tại (`tools/opencode_delegate.py`) **chưa** implement Protocol; seam chỉ là Service Definition. Nghĩa là **chưa có enforcement**: không gì bắt consumer re-run evidence. Kế hoạch nên thêm bước kiểm chứng "delegate → đối chiếu evidence với `git status`/`git diff`".

### 4.6 Session restart
`[Bằng chứng]` `session_log` lưu `summary`, `features_touched`, `files_changed`, `commits`, `verification`.
`[Suy luận]` Mô hình hiện tại khôi phục được "phiên trước làm gì", nhưng **không khôi phục được "việc dở dang / blocker / next step"** — validator chỉ ra đúng: `Handoff captures blockers/files/next step` fail. Đây là gap thật có thể bảo vệ được bằng thí nghiệm A→B.

### 4.7 Subagent seam
`[Bằng chứng]` `subagent_seam.py` có `SubagentRequest`/`SubagentResult`/`SubagentRuntime` và `--self-test` pass logic (assert nội bộ).
`[Suy luận]` Seam đúng pattern nhưng chưa có provider thứ hai; theo `docs/dsh-port-plan.md` A2, chỉ refactor khi có provider thứ hai. Kế hoạch không nên đụng vào đây ở P0/P1.

---

## 5. Revised experiment plan

Mỗi bước: mục tiêu, input, command, output cần lưu, tiêu chí pass/fail, rủi ro.

| ID | Mục tiêu | Input | Command | Output lưu | Pass/Fail | Rủi ro |
|---|---|---|---|---|---|---|
| E0 | Khóa baseline + xác nhận 13 finding | repo sạch | `git status --short`; `python .github/scripts/security_scan.py .`; `python tools/garden.py`; `python tools/validate_schemas.py`; `python -m pytest tools/ -q` | `docs/review-artifacts/e0-baseline.txt` | Tất cả exit 0, trừ validator | pytest có thể >120s |
| E1 | Kiểm chứng validator root-only | copy `feature_list.json` mẫu vào gốc rồi xoá | `node ...validate-harness.mjs --target . --json` (2 lần) | before/after JSON | Điểm `state` đổi → xác nhận root-only | Vô tình commit file mẫu |
| E2 | Phân loại 13 finding | output E0 | Lập bảng Finding×Gap thật? | `e2-triage.md` | Mỗi finding gắn nhãn `thật`/`false-negative`/`giới hạn công cụ` | Trộn 3 loại |
| E3 | Fail-fast | bản sao `init.sh` | chèn lệnh `false` vào bản sao, chạy, soi exit | log exit code | Không `set -e` → các bước sau vẫn chạy | Sửa nhầm file gốc |
| E4 | Lock cross-engine | 2 tiến trình | `acquire_lock` cùng path, engine khác nhau | log `True/False` | Cái thứ hai phải `False` | SQLite busy |
| E5 | Lock expiration | TTL ngắn | acquire → sleep > TTL → `get_active_locks()` | output JSON | Danh sách rỗng | Đồng hồ hệ thống lệch |
| E6 | Generator idempotency | repo sạch | `python tools/generate_harness.py --harness all`; `python tools/garden.py`; `git diff --stat` | log + diff | drift=0, diff rỗng | Generator ghi file do môi trường |
| E7 | Session restart A→B | 2 phiên | A ghi summary/blocker/next; B đọc | transcript 2 phiên | B khôi phục được blocker+next | Cần thao tác thủ công |
| E8 | Gate skip tool | PATH thiếu `ruff` | chạy `checklist.py` | log 2 lần | Ghi nhận PASS-giả | Ẩnh hưởng PATH máy |
| E9 | Deploy target | thư mục tạm | `python tools/deploy.py deploy <tmp>`; chạy validator/garden trên target | log target | Target dùng được | Ghi ngoài workspace |

---

## 6. Revised upgrade roadmap

### Phải làm (chặn rủi ro, không phụ thuộc evidence)
- Giải quyết mâu thuẫn `AGENTS.md:179-181` ↔ `.opencode/instruction/shared-state.md`; chốt một quy tắc state. **Quyết định này phải ghi vào `.kilo/memory/MEMORY.md` `## Decisions`.**
- Thêm `learn-harness-engineering-main/` vào `.gitignore` (mục "Reference checkouts").
- Sửa baseline kế hoạch: `.\init.sh` → `bash ./init.sh` (có điều kiện Git Bash) hoặc thay bằng `python tools/shared_state.py show`.

### Nên làm (khi evidence xác nhận)
- Bổ sung "Definition of Done" theo đúng literal validator nếu muốn điểm phản ánh thật — hoặc ghi nhận đây là false negative.
- Thêm `set -e` (hoặc kiểm soát lỗi tương đương) vào `init.sh` nếu chấp nhận fail-fast.
- Thí nghiệm lock/concurrency + expiration (E4, E5).
- Thí nghiệm deploy target (E9).

### Chỉ làm khi có evidence
- Bổ sung `session-handoff` / blocker-next-step: chỉ sau khi E7 chứng minh `session_log` không đủ.
- `progress.md` / `feature_list.json`: chỉ nếu chấp nhận projection một chiều từ SQLite, và phải ghi rõ chống hai nguồn sự thật.
- Tích hợp `audit-harness.sh`: chỉ sau khi phân loại false positive và có wrapper Windows.
- Adapter SQLite cho validator: **không khả thi** về mặt kỹ thuật (xem 4.3 / mục 7), nên đây cũng thuộc nhóm "không nên làm".

### Không nên làm
- Không thêm `feature_list.json` ở gốc như nguồn sự thật thứ hai.
- Không đưa `audit-harness.sh` vào gate chính.
- Không copy nguyên khóa học vào production.
- Không thêm `testedAt` khi `last_updated` đã đủ (đồng ý với kế hoạch).
- Không refactor `subagent_seam.py` khi chưa có provider thứ hai.

---

## 7. Acceptance criteria

| Nâng cấp | Tiêu chí xác nhận (command) |
|---|---|
| Chốt state | `Select-String AGENTS.md, .opencode/instruction/shared-state.md` không còn mô tả trái nhau về feature workflow |
| Ignore reference dir | `git check-ignore learn-harness-engineering-main/` trả về đường dẫn (exit 0); `git status --short` không còn `?? learn-harness-engineering-main/` |
| Fail-fast | `init.sh` chứa `set -e`; bản sao có lệnh lỗi → exit != 0 |
| Lock cross-engine | E4: lock thứ hai trả `False`; `python tools/shared_state.py locks` chỉ 1 chủ |
| Lock expiration | E5: sau TTL, `python tools/shared_state.py locks` rỗng |
| Generator idempotency | `generate_harness.py --harness all` rồi `garden.py` → "Total drift issues: 0"; `git diff --stat` rỗng |
| Session restart | E7: phiên B in ra được blocker + next step + files của A mà không hỏi lại |
| Gate fail-fast | Mutation test (trên nhánh tạm) làm hỏng test/lint/security → `checklist.py` exit 1, có và không có `ruff` |
| Deploy target | E9: validator/garden trên target chạy được, không crash |
| Validator (nếu theo đuổi điểm) | `node ...validate-harness.mjs --target . --json` → `overall >= 70` **hoặc** có văn bản chấp nhận 52 là giới hạn công cụ generic |

---

## 8. Uncertainty

Các điểm **chưa thể kết luận** nếu chưa đọc/chạy cụ thể:

- `[Chưa chạy]` Toàn bộ `python -m pytest tools/ -q` và `python .github/scripts/checklist.py .` (chỉ mới chạy garden/validate_schemas/validator). Số test pass/fail chưa xác nhận.
- `[Chưa chạy]` `python tools/test_integration.py`, `python .github/scripts/check_skips.py tools/`, `python .github/scripts/security_scan.py .` end-to-end.
- `[Chưa chạy]` `audit-harness.sh` (cần Git Bash) — chưa đo thời gian chạy, false positive, exit code.
- `[Chưa kiểm chứng]` Hành vi `deploy.py` sang target và parity sau deploy.
- `[Chưa kiểm chứng]` Test Codex/OpenCode hook thực tế; chỉ suy từ cấu trúc file.
- `[Giả thuyết]` Việc `features` = 0 rows dựa trên tài liệu `shared-state.md`, chưa query trực tiếp `.solocode/shared-state.db` trong phiên này. Khuyến nghị chạy `python tools/shared_state.py features` để xác nhận số dòng.
- `[Chưa đọc hết]` `tools/generate_harness.py` (~dài) và `tools/garden.py` chỉ đọc phần đầu; kết luận parity dựa trên output chạy, không dựa trên đọc toàn bộ logic.
- `[Không xác định]` `score` của validator trên project đích sau deploy (validator chạy trên cây target chứ không phải cây nguồn).

---

## Phụ lục A — Ba dòng cần sửa/tìm trong code (để đối chiếu)

```text
learn-harness-engineering-main/skills/harness-creator/scripts/lib/harness-utils.mjs:233,252,256  # keyword matching
learn-harness-engineering-main/skills/harness-creator/scripts/lib/harness-utils.mjs:336-354      # root-only file load
.github/scripts/checklist.py:95-97                                                              # FileNotFoundError => pass+skip
.github/scripts/security_scan.py:106-142, 145-156                                               # untracked-top-level auto-exclude
tools/shared_state.py:42; 102-156; 218-221; 360-414                                              # statuses, schema, locks
init.sh:14 ; verify.sh:3                                                                          # set -u (thiếu set -e)
AGENTS.md:179-181 ; .opencode/instruction/shared-state.md                                         # mâu thuẫn feature state
.gitignore                                                                                        # thiếu learn-harness-engineering-main/
```
