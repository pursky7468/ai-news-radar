# Weekly Briefing 規格

> 狀態：v2 Phase B — 待實作
> 設計決策：`design.md` § 11, § 12, § 13
> 任務清單：`tasks.md` § 18

---

## ADDED Requirements

### Requirement: Weekly trend briefing generation

The system SHALL generate a weekly AI trend summary every Monday, aggregating signals from the past 7 days. The weekly briefing SHALL re-use the existing `BriefingGenerator` infrastructure with a 7-day aggregation query and a trend-focused system prompt.

**Controlled by feature flag**: `FEATURES["weekly_briefing"]`. When `False`, the weekly scheduler job is not registered.

**Output path**: `briefings/weekly/YYYY-WNN.md` where `WNN` is the ISO week number (e.g., `2026-W15.md`).

#### Scenario: Scheduled weekly generation
- **WHEN** APScheduler triggers the weekly job (every Monday 08:00 UTC)
- **AND** `FEATURES["weekly_briefing"]` is `True`
- **THEN** `WeeklyBriefingGenerator` queries the last 7 days of relevant posts
- **AND** calls the Groq LLM with a trend-comparison system prompt
- **AND** writes output to `briefings/weekly/YYYY-WNN.md`

#### Scenario: Weekly briefing system prompt emphasis
- **WHEN** the LLM is invoked for weekly briefing
- **THEN** the system prompt instructs it to:
  - Identify the top 3 trend directions of the week
  - Note any topics that emerged or declined compared to the prior week
  - Highlight the most significant tool releases or paper publications
  - Provide developer action items for the coming week

#### Scenario: No posts in the 7-day window
- **WHEN** there are fewer than 3 relevant posts in the past 7 days
- **THEN** the generator logs a warning and skips generation without writing a file

#### Scenario: Manual execution
- **WHEN** `python scripts/generate_weekly_briefing.py` is run
- **THEN** the weekly briefing for the current ISO week is generated immediately
- **AND** overwrites any existing file for the same week

---

### Requirement: MCP `get_weekly_summary` tool

The system SHALL expose a `get_weekly_summary(week_offset=0)` MCP tool that returns the content of the corresponding weekly briefing Markdown file.

#### Scenario: Get current week summary
- **WHEN** an agent calls `get_weekly_summary()`
- **THEN** the content of `briefings/weekly/YYYY-WNN.md` for the current ISO week is returned

#### Scenario: Get prior week summary
- **WHEN** an agent calls `get_weekly_summary(week_offset=-1)`
- **THEN** the content of the previous week's briefing file is returned

#### Scenario: Weekly file not yet generated
- **WHEN** the requested weekly briefing file does not exist
- **THEN** the tool returns a message: `"週報尚未生成。請執行 generate_weekly_briefing.py 或等待本週一排程執行。"`

---

### Requirement: Top 3 algorithmic highlight in daily briefing

The system SHALL compute a composite highlight score for each article and surface the Top 3 in the daily briefing as a "⭐ 今日精選" section.

**Controlled by feature flag**: `FEATURES["highlight_scorer"]`. When `False`, the daily briefing output is unchanged.

**Highlight score formula**:
```
highlight_score = relevance_score * weight_relevance
               + source_weight * weight_source
               + recency_decay * weight_recency
```

Default weights (configurable via `config.py`):
```python
highlight_weights = {
    "relevance": 0.5,
    "source": 0.3,
    "recency": 0.2,
}
```

Source weights: `arxiv=4, github=3, hackernews=2, reddit=1`
Recency decay: `< 24h → 1.0`, `< 48h → 0.5`, `else → 0.0`

#### Scenario: Top 3 inserted at briefing top
- **WHEN** `FEATURES["highlight_scorer"]` is `True` and daily briefing is generated
- **THEN** the output Markdown starts with a `## ⭐ 今日精選` section listing 3 articles with title, source, score, and URL
- **AND** the remaining briefing content follows unchanged

#### Scenario: Fewer than 3 articles available
- **WHEN** the daily window contains fewer than 3 relevant articles
- **THEN** the highlight section lists all available articles (no error)

#### Scenario: Weights configurable without code change
- **WHEN** `highlight_weights` values are modified in `config.py` or via environment variables
- **THEN** the score recalculation uses the updated weights on the next briefing run

---

### Requirement: MCP `get_trending_tools` tool

The system SHALL expose a `get_trending_tools(days=7, limit=10)` MCP tool that returns a ranked list of AI tools mentioned most frequently in recent articles.

**Entity extraction method**: Keyword matching against `backend/known_tools.txt` (no NLP dependency).

#### Scenario: Get trending tools for last 7 days
- **WHEN** an agent calls `get_trending_tools(days=7)`
- **THEN** the tool scans all posts from the last 7 days
- **AND** matches tool names from `known_tools.txt` against each post's `title` and `summary`
- **AND** returns a list of `{tool: string, count: int, sample_url: string}` sorted by count descending

#### Scenario: Tool not in known_tools.txt
- **WHEN** a tool that is not in `known_tools.txt` is frequently mentioned
- **THEN** it is not included in the results (by design — `known_tools.txt` is the authority)
- **Note**: Users or agents can request additions to `known_tools.txt` via PR

#### Scenario: No articles in the time window
- **WHEN** there are no posts in the specified `days` window
- **THEN** an empty list is returned
