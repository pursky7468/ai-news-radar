## ADDED Requirements

### Requirement: Display news feed
The dashboard SHALL display a paginated feed of relevant news posts fetched from the `GET /api/news` endpoint. Each item SHALL show: author handle, post content (truncated to 280 chars with expand option), relevance score badge, labels as chips, posted_at relative time, and a link to the original X post.

#### Scenario: Feed loads on page open
- **WHEN** a user opens the dashboard
- **THEN** the most recent relevant posts are displayed in a list sorted by date descending

#### Scenario: Load more posts
- **WHEN** the user scrolls to the bottom of the feed or clicks "Load more"
- **THEN** the next page of posts is fetched and appended to the feed

### Requirement: Filter feed by label and score
The dashboard SHALL provide filter controls for label (multi-select chips) and minimum relevance score (slider, range 0–10). Applying filters SHALL reload the feed using the corresponding `GET /api/news` query parameters.

#### Scenario: Filter by label
- **WHEN** the user selects the `ai-agent` label chip
- **THEN** the feed refreshes to show only posts labeled `ai-agent`

#### Scenario: Filter by minimum score
- **WHEN** the user moves the score slider to 8
- **THEN** the feed refreshes to show only posts with score >= 8

#### Scenario: Clear filters
- **WHEN** the user clicks "Clear filters"
- **THEN** all filters are reset and the full unfiltered feed is shown

### Requirement: Search posts by keyword
The dashboard SHALL provide a text search input that filters the displayed feed by matching the search term against post content (client-side for already-loaded posts, or server-side via API if post count exceeds 100).

#### Scenario: Keyword search within loaded posts
- **WHEN** the user types a keyword in the search box
- **THEN** the visible feed is filtered to posts containing that keyword in their content

#### Scenario: No results found
- **WHEN** the search term matches no visible posts
- **THEN** an empty state message "No posts match your search" is displayed

### Requirement: Trigger digest from dashboard
The dashboard SHALL provide a "Send Digest Now" button that calls `POST /api/digest/trigger` and displays the result (posts included, channels notified) in a toast notification.

#### Scenario: Digest triggered from UI
- **WHEN** the user clicks "Send Digest Now"
- **THEN** the API is called and a success toast shows "Digest sent: X posts to email/webhook"

#### Scenario: Digest trigger fails
- **WHEN** the API returns an error
- **THEN** an error toast is shown with the error message

### Requirement: Auto-refresh feed
The dashboard SHALL automatically refresh the news feed every 5 minutes in the background and show a "New posts available" banner when new items arrive, without reloading the full page.

#### Scenario: New posts arrive during session
- **WHEN** the background poll detects new posts since the last fetch
- **THEN** a banner appears at the top of the feed: "X new posts available — Click to refresh"

#### Scenario: No new posts
- **WHEN** the background poll finds no new posts
- **THEN** no banner is shown and the feed remains unchanged
