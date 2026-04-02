## ADDED Requirements

### Requirement: Display news feed

The dashboard SHALL display a paginated feed of relevant news posts fetched from the `GET /api/news` endpoint. Each item SHALL show: source badge (`HN` / `Reddit` / `GitHub`), author handle, post content (truncated to 280 chars with expand option), relevance score badge, labels as chips, posted_at relative time, community vote count (`points`), and navigation links as described in the dual-link requirement below.

#### Scenario: Feed loads on page open
- **WHEN** a user opens the dashboard
- **THEN** the most recent relevant posts are displayed in a list sorted by date descending, each with a source badge

#### Scenario: Load more posts
- **WHEN** the user scrolls to the bottom of the feed or clicks "Load more"
- **THEN** the next page of posts is fetched and appended to the feed

### Requirement: Dual navigation links for HN posts

For posts with `source = "hackernews"`, the PostCard SHALL display two separate links:
- **"View article"** → `url` (the original linked resource, e.g. a GitHub repo or blog post)
- **"HN discussion"** → `discussion_url` (`https://news.ycombinator.com/item?id={external_id}`)

For Reddit and GitHub posts, only a single **"View source"** link is shown (pointing to `url`).

#### Scenario: HN post shows both links
- **WHEN** a post with `source = "hackernews"` is rendered
- **THEN** two links are displayed: "View article" and "HN discussion"

#### Scenario: Non-HN post shows single link
- **WHEN** a post with `source = "reddit"` or `source = "github"` is rendered
- **THEN** only one "View source" link is displayed

---

### Requirement: Display community vote count

Each PostCard SHALL display the `points` value when it is non-null and greater than 0, formatted as `▲ {points}` adjacent to the source badge.

#### Scenario: Points displayed for high-vote post
- **WHEN** a post has `points = 342`
- **THEN** the card shows `▲ 342` next to the source badge

#### Scenario: Points hidden when null or zero
- **WHEN** a post has `points = null` or `points = 0`
- **THEN** no vote count indicator is rendered

---

### Requirement: Filter feed by source, label, and score

The dashboard SHALL provide filter controls for:
- **Source** chips: `Hacker News`, `Reddit`, `GitHub` (toggleable, multi-select)
- **Label** chips: `ai-agent`, `ai-model`, `ai-tool`, `agent-skill` (toggleable, multi-select)
- **Minimum score** slider (range 0–10)

Applying filters SHALL reload the feed using the corresponding `GET /api/news` query parameters.

#### Scenario: Filter by source
- **WHEN** the user selects the `Reddit` source chip
- **THEN** the feed refreshes to show only Reddit posts

#### Scenario: Filter by label
- **WHEN** the user selects the `ai-agent` label chip
- **THEN** the feed refreshes to show only posts labeled `ai-agent`

#### Scenario: Filter by minimum score
- **WHEN** the user moves the score slider to 8
- **THEN** the feed refreshes to show only posts with score >= 8

#### Scenario: Clear filters
- **WHEN** the user clicks "Clear filters"
- **THEN** all filters are reset and the full unfiltered feed is shown

### Requirement: Search posts by keyword (server-side)

The dashboard SHALL provide a text search input that filters the feed by sending the search term to the server via `GET /api/news?q={term}`. All search queries are server-side; there is no client-side filtering. The search is triggered after the user stops typing (300ms debounce).

#### Scenario: Keyword search
- **WHEN** the user types a keyword in the search box and pauses for 300ms
- **THEN** a new API request is made with `?q={keyword}` and the feed is replaced with matching results

#### Scenario: No results found
- **WHEN** the server returns zero results for the search term
- **THEN** an empty state message "No posts match your search" is displayed

### Requirement: Trigger digest from dashboard

The dashboard SHALL provide a "Send Digest Now" button that calls `POST /api/digest/trigger` and displays the result (posts included, channels notified) in a toast notification.

#### Scenario: Digest triggered from UI
- **WHEN** the user clicks "Send Digest Now"
- **THEN** the API is called and a success toast shows "Digest sent: N posts to email/webhook"

#### Scenario: Digest trigger fails
- **WHEN** the API returns an error
- **THEN** an error toast is shown with the error message

### Requirement: Auto-refresh feed

The dashboard SHALL automatically poll `GET /api/news?since={last_fetched_at}` every 5 minutes in the background. When the response contains new posts, a banner SHALL appear prompting the user to reload the feed.

#### Scenario: New posts arrive during session
- **WHEN** the background poll to `GET /api/news?since={timestamp}` returns one or more posts
- **THEN** a banner appears at the top of the feed: "N new posts available — Click to refresh"
- **AND** clicking the banner replaces the current feed with the latest results

#### Scenario: No new posts
- **WHEN** the background poll returns zero posts
- **THEN** no banner is shown and the feed remains unchanged
