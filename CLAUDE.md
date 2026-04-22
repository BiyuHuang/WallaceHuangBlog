# Project Conventions

## Timezone

Working timezone is **UTC+8 (Asia/Shanghai / Asia/Singapore)**. All dates, times, and deadlines discussed in this repo default to UTC+8 unless explicitly stated otherwise.

When writing Jekyll post front matter:

- Use date-only format (`date: YYYY-MM-DD`) to avoid timezone-boundary issues where a `+0800` timestamp appears in the future relative to the UTC build runner, which causes Jekyll to silently skip the post.
- If a precise timestamp is required, make sure the UTC equivalent is already in the past at build time.
