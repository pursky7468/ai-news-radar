## ADDED Requirements

### Requirement: Generate periodic digest of top posts
The system SHALL generate a digest of the top-ranked relevant posts (by `relevance_score` descending) that have not yet been sent (`digest_sent = false`). The digest SHALL include post content, author, URL, score, and labels. The number of posts per digest SHALL be configurable (default: 20).

#### Scenario: Digest generation with available posts
- **WHEN** the digest job runs and there are unsent relevant posts
- **THEN** the top N posts (by score) are selected and formatted into a digest payload

#### Scenario: No posts available for digest
- **WHEN** the digest job runs and there are no unsent relevant posts
- **THEN** no notification is sent and the job completes without error

### Requirement: Deliver digest via email
The system SHALL support sending the digest as an HTML email via a configurable SMTP provider (default: SendGrid). The email SHALL include a formatted list of posts with clickable links to the original X posts. The recipient list SHALL be configurable via environment variable.

#### Scenario: Email sent successfully
- **WHEN** the digest is triggered and the email provider is configured
- **THEN** an HTML digest email is sent to all configured recipients
- **AND** the included posts are marked `digest_sent = true` in the store

#### Scenario: Email delivery failure
- **WHEN** the email provider returns an error
- **THEN** the posts are NOT marked as `digest_sent`
- **AND** the error is logged for manual retry

### Requirement: Deliver digest via webhook
The system SHALL support posting the digest as a JSON payload to a configurable webhook URL (e.g., Slack incoming webhook, Discord webhook, or custom endpoint). The payload SHALL include an array of post objects with content, url, score, and labels.

#### Scenario: Webhook delivery succeeds
- **WHEN** the webhook URL is configured and the digest job runs
- **THEN** a POST request with the digest JSON is sent to the webhook URL
- **AND** the included posts are marked `digest_sent = true`

#### Scenario: Webhook URL not configured
- **WHEN** no webhook URL is set in environment
- **THEN** the webhook delivery step is skipped without error

### Requirement: Atomic mark-sent across delivery channels
The system SHALL mark posts as `digest_sent = true` only after all configured delivery channels (email, webhook) have been attempted. If a channel fails, posts SHALL still be marked sent for the channels that succeeded, but the failed channel SHALL be retried on the next digest run by NOT marking those posts sent until success. To support per-channel retry, the `digest_sent` flag tracks overall completion — a post is only marked `digest_sent = true` once all configured channels have delivered successfully.

#### Scenario: Both channels succeed
- **WHEN** both email and webhook deliver successfully
- **THEN** all included posts are marked `digest_sent = true`

#### Scenario: One channel fails
- **WHEN** email succeeds but webhook fails (or vice versa)
- **THEN** posts are NOT marked `digest_sent = true`
- **AND** the error is logged so the next digest run will retry both channels with the same posts

### Requirement: Configurable digest schedule
The system SHALL support configuring the digest send schedule via a cron expression in the environment configuration (default: daily at 08:00 UTC). Both email and webhook deliveries SHALL follow the same schedule.

#### Scenario: Default schedule fires
- **WHEN** it is 08:00 UTC on any day
- **THEN** the digest job is triggered automatically

#### Scenario: Custom schedule configured
- **WHEN** a custom cron expression is set (e.g., `0 9 * * 1` for weekly on Monday)
- **THEN** the digest job fires according to that expression
