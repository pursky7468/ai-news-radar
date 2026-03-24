## ADDED Requirements

### Requirement: Score posts using TF-IDF and keyword weights
The system SHALL score each post locally using a tiered keyword weight dictionary. The keyword dictionary SHALL have two tiers: high-weight terms (weight 3, e.g., `ai agent`, `agent skill`, `multi-agent`, `MCP`, `RAG`, `tool use`, `LangChain`, `AutoGen`) and standard-weight terms (weight 1, e.g., `AI`, `LLM`, `model`, `GPT`, `Claude`, `OpenAI`). TF-IDF is used to down-weight terms that appear extremely frequently across the corpus (IDF component), preventing common words from inflating scores. The final score SHALL be computed as the sum of `(term_weight × idf_factor)` for each matched term, normalized to a 0–10 scale and clamped. No external API SHALL be called during scoring.

#### Scenario: Post with high-weight term matches
- **WHEN** a post contains terms like `ai agent` and `tool use`
- **THEN** the score reflects the sum of their weights, resulting in a high score (e.g., 8–10)

#### Scenario: Post with only generic AI terms
- **WHEN** a post contains only standard-weight terms like `AI` and `model`
- **THEN** the score is moderate (e.g., 2–4)

#### Scenario: Post with no matching terms
- **WHEN** a post contains no terms from either tier
- **THEN** the score is 0 and the label is `other`

### Requirement: Assign category labels from keyword group matches
The system SHALL assign one or more category labels based on which keyword groups fired during scoring. Label mapping SHALL be: high-weight agent terms → `ai-agent`, agent skill terms → `agent-skill`, model/research terms → `ai-model`, tool/framework terms → `ai-tool`. Posts matching no group SHALL receive label `other`.

#### Scenario: Agent-related post
- **WHEN** a post matches high-weight terms in the agent group
- **THEN** labels include `ai-agent`

#### Scenario: Multi-group match
- **WHEN** a post matches terms from both agent and model groups
- **THEN** labels include both `ai-agent` and `ai-model`

### Requirement: Cache scores by post ID
The system SHALL not re-score a post that already has a stored relevance score. Before scoring, it SHALL check the news store and skip any post with an existing score.

#### Scenario: Post already scored
- **WHEN** a post ID already has a relevance score in the news store
- **THEN** the scorer returns the cached score without recomputing

#### Scenario: Post not yet scored
- **WHEN** a post ID has no stored score
- **THEN** the scorer computes and returns a new score

### Requirement: Keyword dictionary is configurable
The system SHALL load the keyword weight dictionary from a config file (YAML or JSON) so weights and terms can be tuned without code changes. It SHALL fall back to a built-in default dictionary if no config file is found.

#### Scenario: Custom keyword config present
- **WHEN** a keywords config file exists at the configured path
- **THEN** the scorer loads weights from that file

#### Scenario: No config file found
- **WHEN** no keywords config file is present
- **THEN** the scorer uses the built-in default keyword dictionary and logs a warning

### Requirement: Threshold-based relevance flag
The system SHALL expose a minimum score threshold (default: 5) for the `is_relevant` boolean flag. Posts meeting or exceeding the threshold are marked relevant and eligible for digest inclusion.

#### Scenario: Post meets threshold
- **WHEN** a post receives a score >= configured threshold
- **THEN** `is_relevant` is set to true

#### Scenario: Post below threshold
- **WHEN** a post receives a score < configured threshold
- **THEN** `is_relevant` is set to false
