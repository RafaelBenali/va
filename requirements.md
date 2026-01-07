# Telegram News Search Engine - Requirements Specification

## Document Information

| Field | Value |
|-------|-------|
| Document Version | 1.1 |
| Date | 2025-12-25 |
| Status | Draft |
| Project Name | Telegram News Search Engine (TNSE) |

---

## 1. Introduction

### 1.1 Purpose

This document defines the complete requirements specification for the Telegram News Search Engine (TNSE). The primary objective of this application is to aggregate, analyze, and rank news content from public Telegram channels, with a focus on Russian-language content, enabling users to discover top news items for repurposing into video content.

The application name is **Telegram News Search Engine (TNSE)**.

### 1.2 Scope

**In Scope:**
- Public Telegram channel monitoring and content aggregation
- AI-powered semantic analysis of news content (optional - see metrics-only mode)
- Metrics-only ranking mode without LLM dependency
- Multi-language support with Russian as primary language
- Cross-language news grouping and deduplication
- Engagement-weighted news ranking
- Conversational search interface (web or Telegram bot)
- Post-level topic categorization and relevance scoring
- Export functionality for content repurposing workflows

**Out of Scope:**
- Direct video creation or editing features
- Content publishing to Telegram or other platforms
- Real-time streaming of Telegram content
- Moderation of Telegram channels
- Direct messaging or bot interactions within monitored channels
- Historical analysis beyond 24-hour windows (initial release)
- Private channel or group management
- Channel administration features

### 1.3 Target Audience

This document is intended for:
- **Developers**: Technical implementation details and architecture guidance
- **Designers**: UX/UI requirements and user flow specifications
- **Stakeholders**: Business objectives and success metrics
- **Testers**: Acceptance criteria and testing requirements
- **AI/ML Engineers**: Neural network integration specifications

The technical detail level assumes familiarity with web application development, API integrations, and basic NLP/AI concepts.

### 1.4 Definitions and Acronyms

| Term | Definition |
|------|------------|
| TNSE | Telegram News Search Engine - the application being specified |
| LLM | Large Language Model - AI models used for semantic understanding |
| NLP | Natural Language Processing |
| API | Application Programming Interface |
| Engagement | Collective term for views, comments, reactions, and shares |
| Relative Engagement | Engagement normalized by channel subscriber count |
| Semantic Similarity | Measure of meaning-based similarity between content items |
| Topic Cluster | Group of news items covering the same event/subject |
| Post Profile | Categorization of individual Telegram post by content type and topic |
| Public Channel | A Telegram channel accessible without invitation or membership approval |
| Reaction Score | Weighted score calculated from individual emoji reaction counts |
| Metrics-Only Mode | Operating mode that ranks content using Telegram metrics without LLM APIs |

### 1.5 References

| Reference | Description |
|-----------|-------------|
| Telegram Bot API | https://core.telegram.org/bots/api |
| Telegram MTProto | https://core.telegram.org/mtproto |
| OpenAI API | https://platform.openai.com/docs/api-reference |
| Anthropic Claude API | https://docs.anthropic.com/claude/reference |

---

## 2. Goals and Objectives

### 2.1 Business Goals

| ID | Goal | Measurable Target |
|----|------|-------------------|
| BG-1 | Reduce time spent on news discovery for video content creation | 75% reduction in manual search time |
| BG-2 | Increase news coverage breadth | Monitor 100+ public Telegram channels simultaneously |
| BG-3 | Improve content relevance accuracy | 90%+ user satisfaction with recommended content |
| BG-4 | Enable discovery of underrated content | Identify 20%+ content with high relevance but low visibility |
| BG-5 | Support multi-language news aggregation | Cover Russian + 3 additional languages minimum |
| BG-6 | Provide cost-effective operation mode | Enable full functionality without paid LLM API access |

### 2.2 User Goals

| ID | Goal | Description |
|----|------|-------------|
| UG-1 | Find relevant news quickly | Users SHALL be able to discover top news on specified topics within minutes |
| UG-2 | Avoid information overload | System SHALL filter and rank content to surface only the most relevant items |
| UG-3 | Discover emerging topics | Users SHALL be able to identify trending subjects before they become mainstream |
| UG-4 | Understand news context | Users SHALL see grouped related content from multiple sources for comprehensive understanding |
| UG-5 | Customize search parameters | Users SHALL be able to refine and save topic configurations |
| UG-6 | Operate without paid APIs | Users SHALL be able to use the system effectively using metrics-only mode |

### 2.3 Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| News discovery time | < 5 minutes per session | User session analytics |
| Content relevance rating | > 4.0/5.0 average | User feedback ratings |
| False positive rate | < 15% | User marking items as irrelevant |
| Topic clustering accuracy | > 85% | Manual review sampling |
| System uptime | 99.5% | Infrastructure monitoring |
| API response time | < 3 seconds for searches | Application performance monitoring |
| Metrics-only mode satisfaction | > 3.5/5.0 average | User feedback ratings |

---

## 3. User Stories/Use Cases

### 3.1 User Stories

| ID | User Story | Priority |
|----|------------|----------|
| US-1 | As a content creator, I want to search for corruption-related news so that I can create investigative video content. | High |
| US-2 | As a content creator, I want to see engagement metrics relative to channel size so that I can identify truly viral content. | High |
| US-3 | As a researcher, I want to discover underrated news with high relevance but low engagement so that I can find unique story angles. | Medium |
| US-4 | As a user, I want to ask clarifying questions about my search so that I can refine results more precisely. | High |
| US-5 | As a user, I want the system to categorize individual posts by topic so that I can find relevant content regardless of channel focus. | High |
| US-6 | As a user, I want the system to group similar news from different sources so that I can see comprehensive coverage of topics. | High |
| US-7 | As a user, I want to discover new relevant public channels so that I can expand my news sources. | Medium |
| US-8 | As a user, I want to filter news by content type (text, images, video) so that I can focus on specific formats. | Low |
| US-9 | As a user, I want to export top news lists with links so that I can reference them during video production. | High |
| US-10 | As a user, I want to save topic configurations so that I can quickly run recurring searches. | Medium |
| US-11 | As a user, I want to use the system without paying for LLM APIs so that I can operate cost-effectively. | High |
| US-12 | As a user, I want to interact with the system via a Telegram bot so that I can search without leaving Telegram. | Medium |
| US-13 | As a user, I want to see detailed reaction breakdowns (each emoji type counted separately) so that I can understand audience sentiment. | Medium |

### 3.2 Use Cases

#### UC-1: Search for Topic News

| Field | Description |
|-------|-------------|
| **Use Case Name** | Search for Topic-Based News |
| **Actors** | Content Creator, System, LLM API (optional) |
| **Preconditions** | User is authenticated; At least one public channel is configured; Either LLM API is accessible OR metrics-only mode is enabled |
| **Basic Flow** | 1. User enters topic query (e.g., "news about corruption in healthcare")<br>2. System initiates conversational clarification if needed (LLM mode only)<br>3. User confirms or refines search parameters<br>4. System fetches content from monitored channels (last 24 hours)<br>5. System analyzes individual posts for topic relevance (LLM or keyword-based)<br>6. System calculates engagement scores including reaction breakdown<br>7. System groups related news into clusters<br>8. System presents ranked list with links |
| **Alternative Flows** | A1: No relevant content found - System suggests broadening search<br>A2: LLM API unavailable - System uses metrics-only mode with keyword matching<br>A3: User requests sub-rankings - System generates specialized lists (e.g., underrated)<br>A4: Metrics-only mode selected - System ranks using views and reaction scores only |
| **Postconditions** | User receives ranked list of relevant news items with links and engagement data |

#### UC-2: Metrics-Only Search

| Field | Description |
|-------|-------------|
| **Use Case Name** | Search Using Metrics-Only Mode |
| **Actors** | User, System |
| **Preconditions** | User is authenticated; At least one public channel is configured |
| **Basic Flow** | 1. User enters search keywords<br>2. System fetches content from monitored channels (last 24 hours)<br>3. System performs keyword matching on post content<br>4. System retrieves engagement metrics (views, reactions by emoji type)<br>5. System calculates reaction score from individual emoji counts<br>6. System ranks posts by combined metrics score<br>7. System presents ranked list with detailed metric breakdown |
| **Alternative Flows** | A1: No keyword matches - System shows top posts by metrics only<br>A2: User adjusts metric weights - System recalculates rankings |
| **Postconditions** | User receives ranked list based purely on Telegram metrics without LLM API usage |

#### UC-3: Conversational Search Refinement

| Field | Description |
|-------|-------------|
| **Use Case Name** | Refine Search Through Conversation |
| **Actors** | User, System, LLM API |
| **Preconditions** | Initial search query has been submitted; LLM mode is enabled |
| **Basic Flow** | 1. System analyzes query ambiguity<br>2. System generates clarifying questions<br>3. User provides answers<br>4. System updates search parameters<br>5. System displays current configuration<br>6. User confirms or continues refinement |
| **Alternative Flows** | A1: Query is clear - Skip to search execution<br>A2: User wants to start over - Reset search parameters |
| **Postconditions** | Search parameters are refined and confirmed by user |

#### UC-4: Telegram Bot Interaction

| Field | Description |
|-------|-------------|
| **Use Case Name** | Search via Telegram Bot |
| **Actors** | User, Telegram Bot, System |
| **Preconditions** | User has started conversation with TNSE bot |
| **Basic Flow** | 1. User sends search query to bot<br>2. Bot processes query and initiates search<br>3. System performs search (LLM or metrics-only mode)<br>4. Bot returns formatted results with inline links<br>5. User can request more details or refine search via bot commands |
| **Alternative Flows** | A1: User sends /help - Bot displays available commands<br>A2: User sends /mode - Bot toggles between LLM and metrics-only mode<br>A3: Results exceed message limit - Bot paginates with navigation buttons |
| **Postconditions** | User receives search results within Telegram interface |

---

## 4. Functional Requirements

### 4.1 Channel Configuration Module

| ID | Requirement | Priority | Testable | Traceable |
|----|-------------|----------|----------|-----------|
| REQ-CC-001 | System MUST allow users to add public Telegram channels by URL or @username. | High | Yes | US-5 |
| REQ-CC-002 | System MUST validate that added channels are public and accessible before adding to monitoring list. | High | Yes | US-5 |
| REQ-CC-003 | System MUST fetch and display channel metadata including name, description, and subscriber count. | High | Yes | US-5 |
| REQ-CC-004 | System SHOULD support bulk import of channels via CSV or JSON file upload. | Medium | Yes | US-5 |
| REQ-CC-005 | System MUST allow users to remove channels from their monitoring list. | High | Yes | US-5 |
| REQ-CC-006 | System MUST display channel health status (accessible, rate-limited, removed). | Medium | Yes | US-5 |
| REQ-CC-007 | System MAY provide a channel discovery feature to find relevant public channels based on topics. | Low | Yes | US-7 |

**Example - REQ-CC-004:** User uploads a CSV file with columns "channel_url" and "notes". System parses file, validates each channel is public, and adds valid channels to monitoring list.

### 4.2 Topic Configuration Module

| ID | Requirement | Priority | Testable | Traceable |
|----|-------------|----------|----------|-----------|
| REQ-TC-001 | System MUST accept free-text topic descriptions in Russian and English. | High | Yes | US-1, US-4 |
| REQ-TC-002 | System SHALL use LLM to interpret topic intent and generate search parameters (when LLM mode enabled). | High | Yes | US-4 |
| REQ-TC-003 | System MUST allow saving topic configurations for future use. | Medium | Yes | US-10 |
| REQ-TC-004 | System SHOULD suggest topic refinements based on available content. | Medium | Yes | US-4 |
| REQ-TC-005 | System MUST display interpreted search parameters for user confirmation. | High | Yes | US-4 |
| REQ-TC-006 | System MAY support boolean operators (AND, OR, NOT) for advanced topic definition. | Low | Yes | US-1 |
| REQ-TC-007 | System MUST support topic templates for common searches (e.g., "corruption", "science news"). | Medium | Yes | US-10 |
| REQ-TC-008 | System MUST support keyword-based topic definition for metrics-only mode. | High | Yes | US-11 |

**Example - REQ-TC-002:** User enters "scandals involving politicians and money". LLM interprets this as topics: [corruption, political scandals, financial crimes, bribery] with relevant keywords and semantic vectors.

### 4.3 News Processing Module

| ID | Requirement | Priority | Testable | Traceable |
|----|-------------|----------|----------|-----------|
| REQ-NP-001 | System MUST collect content from monitored public channels for the past 24 hours. | High | Yes | BG-2 |
| REQ-NP-002 | System SHALL extract text, images, and video content from messages. | High | Yes | US-8 |
| REQ-NP-003 | System MUST calculate relative engagement score (engagement / subscriber count). | High | Yes | US-2 |
| REQ-NP-004 | System SHALL categorize INDIVIDUAL POSTS by topic relevance, NOT whole channels. | High | Yes | US-5 |
| REQ-NP-005 | System MUST group news items about the same topic/event into clusters. | High | Yes | US-6 |
| REQ-NP-006 | System SHALL handle content in Russian, English, Ukrainian, and other Cyrillic languages. | High | Yes | BG-5 |
| REQ-NP-007 | System MUST rank news items by configurable criteria (relevance, engagement, recency). | High | Yes | US-1 |
| REQ-NP-008 | System SHALL determine topic relevance at the individual post level, enabling discovery of relevant content from any channel. | High | Yes | US-5 |
| REQ-NP-009 | System MUST filter posts by topic relevance using per-post semantic analysis or keyword matching. | High | Yes | BG-3 |
| REQ-NP-010 | System SHOULD detect and handle forwarded/reposted content to avoid duplication. | Medium | Yes | US-6 |

**Example - REQ-NP-004:** A general news channel posts 50 messages daily. Each post is individually categorized - a post about healthcare corruption is tagged with [corruption, healthcare] while a sports post from the same channel is tagged [sports]. Topic relevance is determined per-post, not per-channel.

### 4.4 Metrics-Only Mode Module

| ID | Requirement | Priority | Testable | Traceable |
|----|-------------|----------|----------|-----------|
| REQ-MO-001 | System MUST provide a fully functional metrics-only mode that does not require LLM API access. | High | Yes | US-11, BG-6 |
| REQ-MO-002 | System MUST retrieve and display view counts for each post. | High | Yes | US-11 |
| REQ-MO-003 | System MUST retrieve and count EACH emoji reaction type separately (e.g., thumbs up: 45, heart: 23, fire: 12). | High | Yes | US-13 |
| REQ-MO-004 | System MUST calculate a "reaction score" based on individual emoji counts with configurable weights. | High | Yes | US-11 |
| REQ-MO-005 | System SHALL support keyword-based search in metrics-only mode. | High | Yes | US-11 |
| REQ-MO-006 | System MUST rank posts in metrics-only mode using: views, reaction score, and relative engagement. | High | Yes | US-11 |
| REQ-MO-007 | System SHOULD allow users to configure reaction score weights (e.g., heart = 2 points, thumbs up = 1 point). | Medium | Yes | US-11 |
| REQ-MO-008 | System MUST display detailed reaction breakdown in results (count per emoji type). | High | Yes | US-13 |
| REQ-MO-009 | System SHALL treat metrics-only mode as a first-class feature, not a fallback. | High | Yes | BG-6 |
| REQ-MO-010 | System MUST allow switching between LLM mode and metrics-only mode per search. | Medium | Yes | US-11 |

**Example - REQ-MO-003:** A post has reactions: [thumbs_up: 150, heart: 89, fire: 34, thinking: 12, clap: 28]. System stores and displays each count separately, calculates reaction_score = (150*1) + (89*2) + (34*1.5) + (12*0.5) + (28*1) = 413 (with configurable weights).

### 4.5 AI/Neural Network Integration Module

| ID | Requirement | Priority | Testable | Traceable |
|----|-------------|----------|----------|-----------|
| REQ-AI-001 | System MUST integrate with at least one LLM API (OpenAI, Anthropic, or equivalent) for enhanced mode. | High | Yes | BG-3 |
| REQ-AI-002 | System SHALL use LLM for semantic content understanding at the individual post level. | High | Yes | BG-3, US-5 |
| REQ-AI-003 | System MUST support cross-language semantic similarity detection. | High | Yes | US-6 |
| REQ-AI-004 | System SHALL generate content summaries for news items. | Medium | Yes | UG-4 |
| REQ-AI-005 | System MUST categorize individual posts by sentiment and tone. | Medium | Yes | UG-4 |
| REQ-AI-006 | System SHALL identify "underrated" content (high relevance, low engagement). | High | Yes | US-3 |
| REQ-AI-007 | System SHOULD support experimental ranking approaches configurable by user. | Low | Yes | US-3 |
| REQ-AI-008 | System MUST handle LLM API failures gracefully by falling back to metrics-only mode. | High | Yes | UC-1 |
| REQ-AI-009 | System SHALL cache LLM responses to minimize API costs for identical queries. | Medium | Yes | - |
| REQ-AI-010 | System MUST log LLM API usage for cost monitoring and optimization. | High | Yes | - |
| REQ-AI-011 | System MUST NOT require LLM API access for basic functionality (see metrics-only mode). | High | Yes | US-11 |

**Example - REQ-AI-006:** A post about a scientific breakthrough has 500 views in a channel with 100,000 subscribers (0.5% reach) but scores 95% relevance to "science news" topic - flagged as "underrated".

### 4.6 Conversational Interface Module

| ID | Requirement | Priority | Testable | Traceable |
|----|-------------|----------|----------|-----------|
| REQ-CI-001 | System MUST provide a chat-based interface for search queries. | High | Yes | US-4 |
| REQ-CI-002 | System SHALL generate contextual clarifying questions when query is ambiguous (LLM mode). | High | Yes | US-4 |
| REQ-CI-003 | System MUST display current search configuration after refinement. | High | Yes | US-4 |
| REQ-CI-004 | System SHALL support natural language commands for filtering and sorting. | Medium | Yes | US-4 |
| REQ-CI-005 | System MUST maintain conversation context within a session. | High | Yes | US-4 |
| REQ-CI-006 | System SHOULD support voice input for search queries. | Low | Yes | US-4 |
| REQ-CI-007 | System SHALL provide suggested follow-up queries based on results. | Medium | Yes | US-4 |

**Example - REQ-CI-002:** User: "Show me news about medications". System: "I found 847 items. Would you like to focus on: (1) Drug recalls and safety, (2) New drug approvals, (3) Pharmaceutical industry news, (4) Alternative medicine, or describe more specifically?"

### 4.7 Telegram Bot Interface Module

| ID | Requirement | Priority | Testable | Traceable |
|----|-------------|----------|----------|-----------|
| REQ-TB-001 | System MAY provide a Telegram bot interface as an alternative to web interface. | Medium | Yes | US-12 |
| REQ-TB-002 | Telegram bot MUST support search queries via direct messages. | Medium | Yes | US-12 |
| REQ-TB-003 | Telegram bot MUST format results with clickable links to original posts. | Medium | Yes | US-12 |
| REQ-TB-004 | Telegram bot SHALL support both LLM mode and metrics-only mode via commands. | Medium | Yes | US-11, US-12 |
| REQ-TB-005 | Telegram bot MUST provide command-based navigation (/search, /mode, /help, /settings). | Medium | Yes | US-12 |
| REQ-TB-006 | Telegram bot SHOULD support inline keyboards for result pagination and actions. | Medium | Yes | US-12 |
| REQ-TB-007 | Telegram bot MUST respect Telegram message length limits and paginate accordingly. | Medium | Yes | US-12 |
| REQ-TB-008 | Telegram bot SHALL display reaction breakdown in a readable format. | Medium | Yes | US-13 |

**Example - REQ-TB-005:** User sends "/search corruption healthcare" to bot. Bot responds with top 5 results, each with title preview, metrics summary, and link button. User can tap "More results" to see next page.

### 4.8 Results Presentation Module

| ID | Requirement | Priority | Testable | Traceable |
|----|-------------|----------|----------|-----------|
| REQ-RP-001 | System MUST display ranked news list with direct Telegram links. | High | Yes | US-9 |
| REQ-RP-002 | System SHALL show engagement metrics (views, reactions by type, comments) for each item. | High | Yes | US-2, US-13 |
| REQ-RP-003 | System MUST display relative engagement score and ranking position. | High | Yes | US-2 |
| REQ-RP-004 | System SHALL group clustered news items with expand/collapse functionality. | High | Yes | US-6 |
| REQ-RP-005 | System MUST support export to CSV, JSON, and formatted text. | High | Yes | US-9 |
| REQ-RP-006 | System SHALL display content previews (text excerpt, thumbnail). | Medium | Yes | US-1 |
| REQ-RP-007 | System MUST indicate content type (text, image, video) for each item. | Medium | Yes | US-8 |
| REQ-RP-008 | System SHALL provide sub-lists (top overall, underrated, trending). | High | Yes | US-3 |
| REQ-RP-009 | System MUST display source channel information for each post. | Medium | Yes | US-5 |
| REQ-RP-010 | System SHOULD support pagination for large result sets. | Medium | Yes | - |
| REQ-RP-011 | System MUST display individual emoji reaction counts in results. | High | Yes | US-13 |
| REQ-RP-012 | System MUST display per-post topic tags when available. | High | Yes | US-5 |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-P-001 | Search query response time MUST be under 5 seconds for channels totaling < 10,000 messages. | < 5 seconds |
| NFR-P-002 | System SHALL support concurrent processing of 100+ public channels. | 100+ channels |
| NFR-P-003 | System MUST handle 1,000+ news items per search session. | 1,000+ items |
| NFR-P-004 | LLM API calls SHOULD be batched to optimize throughput. | 90% batch rate |
| NFR-P-005 | Background data collection MUST complete within 1 hour for 100 channels. | < 1 hour |
| NFR-P-006 | System SHALL maintain response times under load (50 concurrent users). | < 10 seconds |
| NFR-P-007 | Metrics-only mode response time MUST be under 3 seconds. | < 3 seconds |

### 5.2 Security

| ID | Requirement |
|----|-------------|
| NFR-S-001 | System MUST use OAuth 2.0 or equivalent for user authentication. |
| NFR-S-002 | Telegram API credentials MUST be encrypted at rest using AES-256 or equivalent. |
| NFR-S-003 | System SHALL implement role-based access control (admin, user, viewer). |
| NFR-S-004 | All API communications MUST use TLS 1.2 or higher. |
| NFR-S-005 | System MUST log all authentication attempts and sensitive operations. |
| NFR-S-006 | LLM API keys MUST be stored securely and never exposed to client-side code. |
| NFR-S-007 | System SHOULD implement rate limiting to prevent abuse. |
| NFR-S-008 | Telegram bot token MUST be stored securely and rotatable. |

### 5.3 Usability

| ID | Requirement |
|----|-------------|
| NFR-U-001 | New users SHALL be able to perform first search within 5 minutes of onboarding. |
| NFR-U-002 | Interface MUST be available in Russian and English languages. |
| NFR-U-003 | System SHOULD provide contextual help and tooltips. |
| NFR-U-004 | Error messages MUST be user-friendly and actionable. |
| NFR-U-005 | System SHALL provide keyboard shortcuts for common actions (web interface). |
| NFR-U-006 | Web interface MUST be responsive and usable on tablet devices (minimum 768px width). |
| NFR-U-007 | Telegram bot commands MUST be intuitive and well-documented via /help. |

### 5.4 Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-R-001 | System uptime MUST be 99.5% or higher (excluding planned maintenance). | 99.5% |
| NFR-R-002 | System SHALL implement automatic retry for transient API failures. | 3 retries |
| NFR-R-003 | Data collection failures MUST be logged and reported. | 100% logged |
| NFR-R-004 | System MUST gracefully degrade to metrics-only mode when LLM API is unavailable. | Fallback mode |
| NFR-R-005 | User data and configurations MUST be backed up daily. | Daily backups |

### 5.5 Maintainability

| ID | Requirement |
|----|-------------|
| NFR-M-001 | Code MUST follow established style guides (PEP 8 for Python, ESLint for JavaScript). |
| NFR-M-002 | System MUST have minimum 70% unit test coverage for core modules. |
| NFR-M-003 | All API integrations MUST be abstracted behind interfaces for easy replacement. |
| NFR-M-004 | System SHOULD use containerization (Docker) for consistent deployment. |
| NFR-M-005 | Configuration MUST be externalized and environment-specific. |

### 5.6 Portability

| ID | Requirement |
|----|-------------|
| NFR-PO-001 | Web interface MUST support Chrome, Firefox, Safari, and Edge (latest 2 versions). |
| NFR-PO-002 | Backend MUST be deployable on Linux-based cloud environments (AWS, GCP, Azure). |
| NFR-PO-003 | System MAY provide desktop application wrapper using Electron or equivalent. |
| NFR-PO-004 | Telegram bot MUST work on all Telegram clients (mobile, desktop, web). |

### 5.7 Data Requirements

| ID | Requirement |
|----|-------------|
| NFR-D-001 | System MUST store message content as UTF-8 encoded text. |
| NFR-D-002 | Engagement metrics MUST be stored with timestamps for historical comparison. |
| NFR-D-003 | System SHALL validate Telegram channel URLs before storage. |
| NFR-D-004 | User preferences MUST be serializable to JSON format. |
| NFR-D-005 | System MUST support data export in user-readable formats. |
| NFR-D-006 | Content older than 30 days MAY be archived or purged per retention policy. |
| NFR-D-007 | Reaction counts MUST be stored per emoji type with timestamps. |

### 5.8 Error Handling and Logging

| ID | Requirement |
|----|-------------|
| NFR-E-001 | All exceptions MUST be caught and logged with stack traces. |
| NFR-E-002 | System SHALL implement structured logging (JSON format). |
| NFR-E-003 | Log levels MUST include DEBUG, INFO, WARN, ERROR, FATAL. |
| NFR-E-004 | API errors MUST be logged with request/response details (sanitized). |
| NFR-E-005 | System SHOULD integrate with log aggregation service (e.g., ELK, CloudWatch). |

### 5.9 Internationalization and Localization

| ID | Requirement |
|----|-------------|
| NFR-I-001 | UI MUST support Russian and English languages. |
| NFR-I-002 | Date/time MUST be displayed in user's local timezone. |
| NFR-I-003 | Number formatting MUST respect locale settings. |
| NFR-I-004 | System SHALL support right-to-left (RTL) text rendering for applicable languages. |
| NFR-I-005 | Content analysis MUST support Cyrillic and Latin character sets. |

### 5.10 Accessibility Compliance

| ID | Requirement |
|----|-------------|
| NFR-A-001 | Web interface SHOULD comply with WCAG 2.1 Level AA. |
| NFR-A-002 | All interactive elements MUST be keyboard accessible. |
| NFR-A-003 | Images and icons MUST have alt text descriptions. |
| NFR-A-004 | Color contrast MUST meet minimum 4.5:1 ratio for text. |

### 5.11 Legal and Compliance Requirements

| ID | Requirement |
|----|-------------|
| NFR-L-001 | System MUST comply with Telegram's Terms of Service and API usage policies. |
| NFR-L-002 | User data handling MUST comply with GDPR requirements. |
| NFR-L-003 | System MUST provide data export and deletion capabilities per user request. |
| NFR-L-004 | LLM API usage MUST comply with provider's acceptable use policies. |
| NFR-L-005 | System MUST display content attribution and source links. |
| NFR-L-006 | System MUST only access public channels; private content access is prohibited. |

---

## 6. Technical Requirements

### 6.1 Platform and Browser Compatibility

| Platform | Requirement |
|----------|-------------|
| Desktop Web | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| Tablet Web | iOS Safari 14+, Chrome for Android |
| Server OS | Linux (Ubuntu 20.04+ or equivalent) |
| Mobile | Responsive web (native app not in initial scope) |
| Telegram Bot | All Telegram clients (iOS, Android, Desktop, Web) |

### 6.2 Technology Stack

| Component | Technology Options |
|-----------|-------------------|
| **Backend Language** | Python 3.10+ (recommended) or Node.js 18+ |
| **Web Framework** | FastAPI (Python) or Express/NestJS (Node.js) |
| **Frontend** | React 18+ or Vue 3+ with TypeScript |
| **Database** | PostgreSQL 14+ (primary), Redis (caching) |
| **Search Engine** | Elasticsearch 8+ or Meilisearch (optional for full-text search) |
| **Task Queue** | Celery with Redis or RabbitMQ |
| **Containerization** | Docker, Docker Compose |
| **Orchestration** | Kubernetes (production) or Docker Compose (development) |
| **Telegram Bot** | python-telegram-bot, Telethon, or Pyrogram |

### 6.3 API Integrations

| API | Purpose | Priority |
|-----|---------|----------|
| Telegram Bot API | Channel access, message retrieval, bot interface | Required |
| Telegram MTProto (Telethon/Pyrogram) | Advanced content access from public channels | Required |
| OpenAI API | LLM for semantic analysis | Optional (for LLM mode) |
| Anthropic Claude API | LLM for semantic analysis | Optional (for LLM mode) |
| DeepL or Google Translate API | Cross-language processing | Optional |

### 6.4 Data Storage

| Data Type | Storage Solution | Retention |
|-----------|-----------------|-----------|
| User accounts and preferences | PostgreSQL | Indefinite |
| Telegram channel metadata | PostgreSQL | Indefinite |
| Message content | PostgreSQL + File storage | 30 days |
| Engagement metrics (including per-emoji counts) | PostgreSQL (time-series optimized) | 90 days |
| LLM response cache | Redis | 24 hours |
| Search indices | Elasticsearch | Synced with source |
| Session data | Redis | 24 hours |
| Post-level topic tags | PostgreSQL | Synced with content |

### 6.5 Deployment Environment

| Environment | Platform |
|-------------|----------|
| Development | Local Docker Compose |
| Staging | Cloud VM or managed Kubernetes |
| Production | Managed Kubernetes (GKE, EKS, AKS) or VPS cluster |
| CI/CD | GitHub Actions or GitLab CI |

---

## 7. Design Considerations

### 7.1 User Interface Design

**Key UI Elements:**
- Dashboard with quick access to recent searches and saved topics
- Chat-based search interface with message threading
- Results view with sortable columns and expandable clusters
- Channel list panel with status indicators
- Settings panel for topic configurations and preferences
- Mode toggle (LLM / Metrics-Only) prominently displayed
- Reaction breakdown visualization (emoji counts)

**Wireframe References:** To be developed during design phase.

**Key Interactions:**
- Drag-and-drop for channel ordering
- Click-to-expand for news clusters
- Inline editing for topic configurations
- Copy-to-clipboard for news links
- One-click mode switching

### 7.2 User Experience Design

**Navigation:**
- Single-page application with sidebar navigation (web)
- Command-based navigation (Telegram bot)
- Breadcrumb trails for deep navigation
- Quick-access toolbar for frequent actions

**Information Architecture:**
- Primary: Search/Chat interface
- Secondary: Results and analysis
- Tertiary: Configuration and management

**User Flows:**
1. Onboarding: Sign up -> Add first channels -> Configure topic -> First search
2. Daily use: Open app -> Select saved topic -> Review results -> Export
3. Discovery: Enter new topic -> Conversational refinement -> Save configuration
4. Bot use: /search query -> Review results -> /export or continue refining

### 7.3 Branding and Style

**Visual Guidelines:**
- Clean, content-focused design
- Dark mode support (user preference)
- Telegram-inspired blue accent colors
- Clear typography hierarchy for Russian and Latin text
- Minimal decorative elements
- Emoji display for reaction breakdowns

---

## 8. Testing and Quality Assurance

### 8.1 Testing Strategy

| Test Type | Scope | Automation |
|-----------|-------|------------|
| Unit Tests | Core business logic, data processing, reaction scoring | Automated (pytest/Jest) |
| Integration Tests | API endpoints, database operations | Automated |
| E2E Tests | Critical user flows (web and bot) | Automated (Playwright/Cypress) |
| Performance Tests | Load testing, API response times | Semi-automated (k6/Locust) |
| Security Tests | Authentication, data protection | Manual + automated scanning |
| UAT | User acceptance with stakeholders | Manual |
| Bot Tests | Telegram bot command handling | Automated |

### 8.2 Acceptance Criteria

**General Criteria for all features:**
- Feature works as specified in requirements
- No critical or high-severity bugs
- Performance targets met
- Security review passed
- Documentation updated

**Specific Criteria:**
- US-1: Search returns relevant results with > 80% precision
- US-2: Engagement scores accurately calculated and displayed
- US-4: Conversational interface reduces clarification loops by 50%
- US-5: Post-level categorization correctly identifies topic relevance per post
- US-11: Metrics-only mode provides useful rankings without LLM
- US-13: All emoji reaction types are counted and displayed separately

### 8.3 Performance Testing Requirements

| Scenario | Target | Tool |
|----------|--------|------|
| Concurrent users (50) | < 10s response time | k6 |
| Large result sets (1000+ items) | < 5s render time | Lighthouse |
| API throughput | 100 requests/minute sustained | k6 |
| LLM API batch processing | 500 items in < 2 minutes | Custom script |
| Metrics-only search | < 3s response time | k6 |
| Telegram bot response | < 5s for search results | Custom script |

### 8.4 Security Testing Requirements

| Test | Description |
|------|-------------|
| Penetration testing | External security audit before production launch |
| OWASP Top 10 | Verify protection against common vulnerabilities |
| API security | Test authentication, authorization, input validation |
| Data encryption | Verify encryption at rest and in transit |
| Bot security | Verify bot token protection and user authentication |

---

## 9. Deployment and Release

### 9.1 Deployment Process

1. Code merged to main branch triggers CI/CD pipeline
2. Automated tests run (unit, integration, E2E)
3. Docker images built and pushed to registry
4. Staging environment updated automatically
5. Manual QA verification on staging
6. Production deployment via blue-green or rolling update
7. Post-deployment health checks and monitoring

### 9.2 Release Criteria

- All automated tests passing
- No critical or high-severity open bugs
- Performance benchmarks met
- Security scan passed
- Documentation updated
- Stakeholder sign-off obtained
- Telegram bot tested in production-like environment

### 9.3 Rollback Plan

1. Monitor production metrics post-deployment (15-minute window)
2. If critical issues detected, initiate rollback
3. Revert to previous container image version
4. Database migrations must be backward-compatible
5. Notify stakeholders of rollback
6. Post-mortem analysis within 24 hours

---

## 10. Maintenance and Support

### 10.1 Support Procedures

| Channel | Purpose | Response Time |
|---------|---------|---------------|
| In-app feedback | Bug reports, feature requests | 48 hours acknowledgment |
| Email support | Account issues, technical problems | 24 hours |
| Telegram bot /feedback | Quick feedback via bot | 48 hours |
| Documentation | Self-service help | Always available |

### 10.2 Maintenance Schedule

| Activity | Frequency |
|----------|-----------|
| Security patches | As needed (within 24 hours for critical) |
| Dependency updates | Monthly |
| Database maintenance | Weekly (off-peak hours) |
| Backup verification | Weekly |
| Performance review | Monthly |

### 10.3 Service Level Agreements

| Metric | Target |
|--------|--------|
| Uptime | 99.5% monthly |
| Critical bug fix | 4 hours |
| High bug fix | 24 hours |
| Medium bug fix | 1 week |
| Feature request response | 2 weeks |

---

## 11. Future Considerations

**The following are explicitly OUT OF SCOPE for initial release but may be considered for future versions:**

| Feature | Description | Priority |
|---------|-------------|----------|
| Video content analysis | AI analysis of video content in posts | Medium |
| Sentiment trend tracking | Historical sentiment analysis over time | Medium |
| Custom ranking algorithms | User-defined ranking formulas | Low |
| Team collaboration | Shared workspaces and annotations | Medium |
| Mobile native app | iOS and Android applications | Low |
| Browser extension | Quick-save content from Telegram web | Low |
| Webhook integrations | Push notifications to external systems | Medium |
| Historical analysis | Search beyond 24-hour window | Medium |
| Local LLM integration | On-premise LLM for privacy-conscious users | Medium |
| Advanced reaction analytics | Trend analysis of emoji usage over time | Low |

---

## 12. Training Requirements

### 12.1 User Training

| Training | Format | Duration |
|----------|--------|----------|
| Getting Started | Interactive tutorial in-app | 10 minutes |
| Feature walkthroughs | Video tutorials | 5-10 minutes each |
| Best practices guide | Documentation | Self-paced |
| Metrics-only mode guide | Documentation + video | 15 minutes |
| Telegram bot usage | In-bot /help command + documentation | 5 minutes |

### 12.2 Administrator Training

| Training | Format | Duration |
|----------|--------|----------|
| System configuration | Documentation + video | 1 hour |
| Monitoring and troubleshooting | Documentation | Self-paced |
| API key management | Documentation | 30 minutes |
| Bot deployment | Documentation | 30 minutes |

---

## 13. Stakeholder Responsibilities

| Stakeholder | Responsibilities |
|-------------|-----------------|
| Product Owner | Requirements approval, prioritization, UAT sign-off |
| Development Lead | Technical decisions, code review, deployment |
| QA Lead | Test strategy, quality gates, bug triage |
| DevOps | Infrastructure, CI/CD, monitoring |
| UX Designer | Interface design, usability testing |

---

## 14. Change Management Process

### 14.1 Change Request Procedure

1. Submit change request via issue tracker
2. Product Owner reviews and prioritizes
3. Impact assessment by Development Lead
4. Stakeholder review for significant changes
5. Approval/rejection decision
6. Update requirements document if approved
7. Schedule implementation

### 14.2 Documentation Updates

- All approved changes must be reflected in this document
- Version history maintained in document header
- Change log appended to Appendix

---

## Appendix

### A. Glossary

Extended definitions of domain-specific terms used throughout this document.

| Term | Definition |
|------|------------|
| Post-level categorization | The process of assigning topic tags to individual posts rather than entire channels |
| Reaction score | A calculated metric derived from weighted counts of individual emoji reactions |
| Metrics-only mode | System operation using only Telegram-provided metrics without LLM API calls |
| Public channel | A Telegram channel that can be accessed without invitation or approval |

### B. Telegram API Rate Limits Reference

| API Type | Limit |
|----------|-------|
| Bot API messages | 30 messages/second |
| GetHistory (MTProto) | 100 messages/request |
| Flood wait | Variable, typically 1-60 seconds |
| Bot API getUpdates | 100 updates/request |

### C. LLM API Cost Estimates

| Provider | Model | Estimated Cost per 1000 news items |
|----------|-------|-----------------------------------|
| OpenAI | GPT-4 | $2-5 |
| OpenAI | GPT-3.5-turbo | $0.20-0.50 |
| Anthropic | Claude 3 Opus | $3-6 |
| Anthropic | Claude 3 Sonnet | $0.50-1.00 |

*Estimates based on average message length and required analysis depth.*

*Note: Metrics-only mode incurs $0 LLM API costs.*

### D. Reaction Score Calculation

Default reaction weights for metrics-only mode:

| Emoji Type | Default Weight | Rationale |
|------------|---------------|-----------|
| Heart | 2.0 | Strong positive sentiment |
| Thumbs Up | 1.0 | Standard positive |
| Fire | 1.5 | High engagement indicator |
| Clap | 1.0 | Standard positive |
| Thinking | 0.5 | Neutral/contemplative |
| Thumbs Down | -1.0 | Negative sentiment |
| Custom emoji | 1.0 | Default for unlisted |

Formula: `reaction_score = SUM(emoji_count * emoji_weight)`

### E. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Initial | Initial requirements document |
| 1.1 | 2025-12-25 | Update | Removed group management features; Changed from groups to public channels; Added metrics-only mode with detailed reaction scoring; Added Telegram bot interface option; Changed to post-level categorization |

---

*End of Requirements Document*
