# Yêu cầu DeepSeek phản biện kế hoạch nâng cấp Solo-Code-CLI

## Vai trò

Bạn là reviewer độc lập. Hãy kiểm tra kế hoạch đánh giá và nâng cấp harness của repository:

`F:\Project\project_tools\Solo-Code-CLI`

Mục tiêu là tìm những điểm còn thiếu, giả định sai, false positive, rủi ro triển khai và thử nghiệm cần bổ sung. Không chỉnh sửa file trong repository.

## Bối cảnh

Repository là Solo-Code Harness đa engine, hỗ trợ Kilo, Claude Code, OpenCode, Copilot, Gemini và Codex.

Các thành phần chính:

- `AGENTS.md`, `CLAUDE.md`, `.harness.lock`
- `.kilo/`, `.claude/`, `.copilot/`, `.gemini/`, `.opencode/`
- `.solocode/shared-state.db`
- `tools/shared_state.py`, `tools/garden.py`, `tools/generate_harness.py`
- `tools/validate_schemas.py`, `tools/subagent_seam.py`
- `.github/scripts/checklist.py`, `.github/scripts/security_scan.py`
- `init.sh`, `Makefile`

Nguồn tham khảo mới:

`learn-harness-engineering-main/`

Đây là tài liệu và công cụ tham khảo, chưa được xem là code production.

## Kết quả đã biết

Đã chạy:

```powershell
node learn-harness-engineering-main/skills/harness-creator/scripts/validate-harness.mjs --target . --json
```

Kết quả:

```text
overall: 52
bottleneck: state
```

Các finding chính:

- Không tìm thấy `feature_list.json`.
- Không tìm thấy `progress.md`.
- Không tìm thấy session handoff template.
- Không phát hiện rõ one-feature-at-a-time rule.
- Không phát hiện feature dependencies.
- Không phát hiện completion gate đầy đủ.

Repository hiện đã có SQLite feature state, `evidence`, `last_updated`, session log, memory tables, lifecycle hooks, `init.sh`, verification gates, security scan và garden/drift checks. Vì vậy điểm 52 có thể phản ánh giới hạn của validator generic thay vì chất lượng harness thật.

Audit script tham khảo là `learn-harness-engineering-main/tools/audit-harness.sh`. File này có 438 dòng, không phải 543 dòng như một phân tích trước đó đã nêu.

Template feature list của khóa học dùng `not-started`, `in-progress`, `blocked`, `done`. Solo-Code-CLI hiện dùng `not-started`, `in-progress`, `completed`, `blocked`.

## Kế hoạch cần được phản biện

### Giai đoạn 1: Khóa baseline

Chạy và lưu kết quả:

```powershell
git status --short
git branch --show-current
python .github/scripts/security_scan.py .
python .github/scripts/check_skips.py tools/
python .github/scripts/checklist.py .
python tools/validate_schemas.py
python tools/garden.py
python -m pytest tools/ -q
python tools/test_integration.py
.\init.sh
python tools/shared_state.py show
python tools/shared_state.py features
```

Chạy riêng các công cụ tham khảo:

```powershell
node learn-harness-engineering-main/skills/harness-creator/scripts/validate-harness.mjs --target . --json
```

Nếu có Git Bash:

```bash
bash learn-harness-engineering-main/tools/audit-harness.sh .
```

Không đưa audit generic vào gate chính ngay.

### Giai đoạn 2: Phân loại finding

Với mỗi finding, lập bảng:

| Finding | Công cụ | Cơ chế hiện có | Gap thật? | Hành động |
|---|---|---|---|---|

Một finding chỉ được xem là gap thật khi có lỗi tái hiện được bằng command/test, session thực tế bị mất trạng thái, verification gate cho pass sai, engine xử lý khác nhau do thiếu tài liệu, hoặc state tồn tại nhưng không thể khôi phục.

### Giai đoạn 3: Thử nghiệm

#### 3.1 State adapter

So sánh fixture dùng SQLite hiện tại với fixture dùng `feature_list.json`. Kiểm tra validator có thể đọc SQLite hay cần adapter. Không tạo `feature_list.json` production nếu việc đó tạo hai nguồn sự thật.

#### 3.2 Audit script

Đánh giá thời gian chạy, false positive, overlap với `checklist.py`, `garden.py`, `boundary_audit.py`, khả năng chạy trên PowerShell/Git Bash/CI và tác động của exit code. Ban đầu chỉ dùng audit dưới dạng report.

#### 3.3 Mutation test verification

Tạm thời làm hỏng test, lint và security scan; kiểm tra gate có fail-fast và trả exit code đúng không.

#### 3.4 Session restart

Mô phỏng session A đặt feature thành `in-progress`, ghi evidence/blocker/files/next step, rồi khởi động session B. Kiểm tra có khôi phục đủ trạng thái không. Chỉ thêm progress/handoff artifact nếu thử nghiệm chứng minh state hiện tại chưa đủ.

### Giai đoạn 4: Nâng cấp theo ưu tiên

#### P0 — Tài liệu và routing

- Mô tả SQLite là nguồn feature state chính.
- Mô tả `evidence` và `last_updated`.
- Ghi rõ startup, restart và verification workflow.
- Ghi rõ one-feature-at-a-time nếu đây là quy tắc thực sự được áp dụng.

#### P1 — State/lifecycle

Chỉ thực hiện nếu có gap thật: session handoff template, blocker/next-step fields, stale feature check, feature dependencies hoặc adapter để validator hiểu SQLite. Không thêm `testedAt` nếu `last_updated` đã đủ.

#### P2 — Audit integration

Chỉ tích hợp audit sau khi false positive được phân loại, có wrapper phù hợp với Windows, exit code được hiệu chỉnh và không tạo gate trùng hoặc mâu thuẫn.

#### P3 — Đo hiệu quả

Chạy 3–5 task đại diện trước và sau nâng cấp. Đo số lần mất context, báo hoàn thành khi gate chưa pass, sửa ngoài scope, thời gian khôi phục session, số lần người dùng phải nhắc lại context và false positive của audit.

## Câu hỏi cần DeepSeek trả lời

1. Kế hoạch còn thiếu subsystem, failure mode hoặc thử nghiệm nào không?
2. Có nên duy trì SQLite làm nguồn sự thật duy nhất không? Vì sao?
3. Có rủi ro nào khi thêm `feature_list.json`, `progress.md` hoặc `testedAt` không?
4. Validator generic nên sửa để hiểu SQLite, bọc bằng adapter hay chỉ xem là công cụ tham khảo?
5. Audit shell có phù hợp với Windows và kiến trúc đa engine không?
6. Có cần kiểm tra thêm generated-file drift, concurrent engine access, lock expiration, compaction/restart, stale feature, cross-engine parity, security boundary hoặc subagent evidence không?
7. Acceptance criteria hiện tại có đủ chặt không?
8. Có chỉ số nào khó đo hoặc dễ bị đánh giá sai không?
9. Thứ tự P0/P1/P2/P3 có tối ưu không?
10. Có đề xuất nào đang dựa trên giả định chưa được kiểm chứng không?

## Định dạng báo cáo bắt buộc

### 1. Executive review

- Đánh giá: `đủ / còn thiếu / cần điều chỉnh lớn`.
- Ba rủi ro lớn nhất.
- Một đề xuất cần thay đổi ngay.

### 2. Missing checks

| Mục còn thiếu | Vì sao quan trọng | Command/test đề xuất | Mức độ |
|---|---|---|---|

### 3. False-positive risks

| Công cụ/finding | Vì sao có thể sai | Cách xác minh |
|---|---|---|

### 4. Architecture review

Đánh giá riêng SQLite state, lifecycle hooks, generated engine files, locks/concurrency, evidence model, session restart và subagent seam.

### 5. Revised experiment plan

Mỗi bước phải có mục tiêu, input, command, output cần lưu, tiêu chí pass/fail và rủi ro.

### 6. Revised upgrade roadmap

Phân loại thành: phải làm, nên làm, chỉ làm khi có evidence và không nên làm.

### 7. Acceptance criteria

Đưa ra tiêu chí định lượng hoặc command cụ thể để xác nhận từng nâng cấp.

### 8. Uncertainty

Liệt kê mọi nhận định chưa thể kết luận nếu chưa đọc hoặc chạy file cụ thể.

## Ràng buộc

- Không tự động sửa file.
- Không copy nguyên trạng toàn bộ khóa học vào production.
- Không coi structural benchmark là bằng chứng harness vận hành tốt hoặc kém.
- Không gọi một field là bắt buộc nếu schema hoặc code hiện tại chưa yêu cầu.
- Không đưa ra số liệu benchmark nếu chưa chạy command tương ứng.
- Phân biệt rõ evidence quan sát được, suy luận, giả thuyết và đề xuất.
- Khi nêu kết luận, phải kèm file, command hoặc output làm bằng chứng.
