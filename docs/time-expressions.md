# Time Expression Support

This documents the **intended** Chinese natural-language time classes for
`dsh-logtimeline`. Golden tests in `tests/query.test.ts` and the vendored Python
parser are the source of truth; this table helps users and reviewers.

| ID | Class | Example input | Expected behavior | Verified |
|----|-------|---------------|-------------------|----------|
| T01 | Today | 今天下午 | Current local day + part-of-day | Yes (`T01a`) |
| T01b | Bare today | 今天 | Whole day | Yes (`T01b`, 2026-11-16) |
| T02 | Yesterday | 昨天 / 昨晚 | Previous calendar day (昨晚 = 18:00–24:00) | Yes (`T02a/b`) |
| T03 | Day before | 前天 | -2 days | Yes (`T03`) |
| T18 | Tomorrow | 明天 | Next calendar day (whole day) | Yes (`T18`, 2026-11-16) |
| T04 | Relative hours | 3 小时前 | now-3h .. now | Yes (`T04a`) |
| T04b | 半小时前 | 半小时前 | now-30m .. now | Yes (`T04b`, 2026-11-14) |
| T05 | Relative minutes | 30 分钟前 | now-30m .. now | Yes (`T05`) |
| T06 | Absolute date | 2026-07-03 | That day | Yes (`T06`) |
| T07 | Absolute datetime | 2026-07-03 14:30 | Point window (start=end=stamp) | Yes (`T07`) |
| T08 | Range | 昨天 9 点到 18 点 | Explicit start/end | Yes (`T08`) |
| T09 | This week | 本周 / 这周 | Mon–Sun (parser-defined) | Yes (`T09a/b`) |
| T10 | Last week | 上周 | Previous Mon–Sun window | Yes (`T10`) |
| T11 | This month | 本月 / 这个月 | First day of month → first of next | Yes (`T11a/b`, 2026-11-14) |
| T12 | Last month | 上个月 / 上月 | Previous calendar month window | Yes (`T12`, 2026-11-14) |
| T13 | This year / last year | 今年 / 去年 | Calendar year windows | Yes (`T13a/b`, 2026-11-14) |
| T14 | Morning/afternoon/evening | 上午/下午/晚上 | Part-of-day clip | Yes (`T14a/b/c`) |
| T15 | Unsupported free text | 上周摸鱼那天 | No match → empty/error, **not** silent full-file scan | Yes (`T15`) |
| T16 | Tomorrow night | 明晚 / 明晚8点 | Next day 18:00–23:00 / point+1h | Yes (`T16a/b`, 2026-11-14) |
| T17 | Cross-midnight range | 晚上11点到1点 | 23:00 → next-day 01:00（修复：终点不再被窗口词误换算为 13:00） | Yes (`T17`, 2026-11-14) |

Golden tests: `tests/compat_time.test.ts` (parser contract with frozen
`now=2026-07-03 20:00:00` + filter/host paths against `tests/fixtures/demo.log`).

## Failure semantics

- **Unknown expression** → should fail closed with a clear error, not dump all logs.
- **Ambiguous timezone** → treat timestamps as **local** unless config says otherwise.
- **Empty window** → return zero matches, not an error.

## Reviewer checklist

- [x] Each T01–T14 has at least one unit test or fixture line (unsupported rows documented)
- [x] T15 negative tests exist
- [ ] Windows `py` launcher path still covered
- [ ] max_lines / timeout / ANSI strip still enforced on every query path
