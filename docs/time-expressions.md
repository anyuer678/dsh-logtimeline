# Time Expression Support

This documents the **intended** Chinese natural-language time classes for
`dsh-logtimeline`. Golden tests in `tests/query.test.ts` and the vendored Python
parser are the source of truth; this table helps users and reviewers.

| ID | Class | Example input | Expected behavior | Verified |
|----|-------|---------------|-------------------|----------|
| T01 | Today | 今天下午 | Current local day + part-of-day | Yes (`T01a`) |
| T01b | Bare today | 今天 | Whole day — **unsupported** (no matcher) | Documented skip |
| T02 | Yesterday | 昨天 / 昨晚 | Previous calendar day (昨晚 = 18:00–24:00) | Yes (`T02a/b`) |
| T03 | Day before | 前天 | -2 days | Yes (`T03`) |
| T04 | Relative hours | 3 小时前 | now-3h .. now | Yes (`T04a`) |
| T04b | 半小时前 | 半小时前 | **unsupported** (半 not in relative numeral class) | Documented skip |
| T05 | Relative minutes | 30 分钟前 | now-30m .. now | Yes (`T05`) |
| T06 | Absolute date | 2026-07-03 | That day | Yes (`T06`) |
| T07 | Absolute datetime | 2026-07-03 14:30 | Point window (start=end=stamp) | Yes (`T07`) |
| T08 | Range | 昨天 9 点到 18 点 | Explicit start/end | Yes (`T08`) |
| T09 | This week | 本周 / 这周 | Mon–Sun (parser-defined) | Yes (`T09a/b`) |
| T10 | Last week | 上周 | Previous Mon–Sun window | Yes (`T10`) |
| T11 | This month | 本月 / 这个月 | **unsupported** (no month matcher) | Documented skip |
| T12 | Last month | 上个月 | **unsupported** (no month matcher) | Documented skip |
| T13 | This year / last year | 今年 / 去年 | **unsupported** (no year matcher) | Documented skip |
| T14 | Morning/afternoon/evening | 上午/下午/晚上 | Part-of-day clip | Yes (`T14a/b/c`) |
| T15 | Unsupported free text | 上周摸鱼那天 | No match → empty/error, **not** silent full-file scan | Yes (`T15`) |

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
