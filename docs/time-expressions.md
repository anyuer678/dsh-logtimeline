# Time Expression Support

This documents the **intended** Chinese natural-language time classes for
`dsh-logtimeline`. Golden tests in `tests/query.test.ts` and the vendored Python
parser are the source of truth; this table helps users and reviewers.

| ID | Class | Example input | Expected behavior |
|----|-------|---------------|-------------------|
| T01 | Today | 今天 / 今天下午 | Current local day, optional part-of-day filter |
| T02 | Yesterday | 昨天 / 昨晚 | Previous calendar day |
| T03 | Day before | 前天 | -2 days |
| T04 | Relative hours | 3 小时前 | now-3h .. now |
| T05 | Relative minutes | 30 分钟前 | now-30m .. now |
| T06 | Absolute date | 2026-09-20 | That day |
| T07 | Absolute datetime | 2026-09-20 14:30 | Point / window around stamp |
| T08 | Range | 昨天 9 点到 18 点 | Explicit start/end |
| T09 | This week | 本周 / 这周 | Mon–Sun or last 7 days (parser-defined; document in code) |
| T10 | Last week | 上周 | Previous week window |
| T11 | This month | 本月 / 这个月 | Month-to-date or full month (parser-defined) |
| T12 | Last month | 上个月 | Previous month window |
| T13 | This year / last year | 今年 / 去年 | Year windows |
| T14 | Morning/afternoon/evening | 上午/下午/晚上 | Part-of-day clip |
| T15 | Unsupported free text | 上周摸鱼那天 | No match → empty/error, **not** silent full-file scan |

## Failure semantics

- **Unknown expression** → should fail closed with a clear error, not dump all logs.
- **Ambiguous timezone** → treat timestamps as **local** unless config says otherwise.
- **Empty window** → return zero matches, not an error.

## Reviewer checklist

- [ ] Each T01–T14 has at least one unit test or fixture line
- [ ] T15 negative tests exist
- [ ] Windows `py` launcher path still covered
- [ ] max_lines / timeout / ANSI strip still enforced on every query path
