# Graph Report - nolapenses  (2026-07-09)

## Corpus Check
- 30 files · ~175,434 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 279 nodes · 349 edges · 28 communities (21 shown, 7 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d6ad46a2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Plan 001: Establish a repo verification baseline
- graphify reference: extra exports and benchmark
- NoLaPenses Landing Page
- graphify reference: query, path, explain
- Implementation Plans
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- AGENTS.md
- extraction-spec.md

## God Nodes (most connected - your core abstractions)
1. `debugLog()` - 29 edges
2. `What You Must Do When Invoked` - 12 edges
3. `Plan 001: Establish a repo verification baseline` - 12 edges
4. `Plan 002: Make the Docker/Nginx deploy path match Nginx Proxy Manager` - 12 edges
5. `Plan 003: Centralize lead widget config, tracking, and reCAPTCHA loading` - 12 edges
6. `init()` - 11 edges
7. `/graphify` - 10 edges
8. `Nolapenses — SEO, analítica y campañas pagas` - 10 edges
9. `buildChatbotPayload()` - 8 edges
10. `graphify reference: extra exports and benchmark` - 8 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (28 total, 7 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (20): author, bugs, url, description, devDependencies, tailwindcss, @tailwindcss/cli, homepage (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.18
Nodes (13): classifyFromFacts(), createWidget(), ensureRecaptchaClient(), escapeHtml(), getAttribution(), getSessionId(), init(), leadSummary() (+5 more)

### Community 2 - "Community 2"
Cohesion: 0.24
Nodes (12): getBrowserName(), getPersonalizedGreeting(), init(), initScrollAnimations(), sendAudioWebhook(), sendMoodWebhook(), setRandomAIMood(), setupScrollIndicator() (+4 more)

### Community 3 - "Community 3"
Cohesion: 0.13
Nodes (40): advanceChatStep(), buildChatbotPayload(), createSessionId(), debugLog(), debugWarn(), getBrowserName(), getPersonalizedGreeting(), getSelectedService() (+32 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 5 - "Community 5"
Cohesion: 0.25
Nodes (4): errors, htmlFiles, requiredFiles, root

### Community 6 - "Community 6"
Cohesion: 0.67
Nodes (5): attach(), getToken(), loadScript(), normalizeAction(), ready()

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (21): Campaigns, Content, Convención UTM para campañas, Ejemplo de tono, Ejemplos de URLs, Enfoque obligatorio, Estructura sugerida, Eventos GA4 importantes (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.53
Nodes (5): getBrowserName(), getPersonalizedGreeting(), init(), setRandomAIMood(), setUserMood()

### Community 9 - "Community 9"
Cohesion: 0.67
Nodes (5): attach(), getToken(), loadScript(), normalizeAction(), ready()

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (17): Commands you will need, Current state, Done criteria, Git workflow, Maintenance notes, Plan 002: Make the Docker/Nginx deploy path match Nginx Proxy Manager, Scope, Status (+9 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (17): Commands you will need, Current state, Done criteria, Git workflow, Maintenance notes, Plan 003: Centralize lead widget config, tracking, and reCAPTCHA loading, Scope, Status (+9 more)

### Community 16 - "Plan 001: Establish a repo verification baseline"
Cohesion: 0.12
Nodes (15): Commands you will need, Current state, Done criteria, Git workflow, Maintenance notes, Plan 001: Establish a repo verification baseline, Scope, Status (+7 more)

### Community 17 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 18 - "NoLaPenses Landing Page"
Cohesion: 0.22
Nodes (8): Core Concept, Features, NoLaPenses Landing Page, Requirements, Security notes for lead webhooks, Setup, Technologies, Verification

### Community 19 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 20 - "Implementation Plans"
Cohesion: 0.40
Nodes (4): Dependency notes, Execution order & status, Findings considered and rejected, Implementation Plans

### Community 21 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 22 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 23 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **133 isolated node(s):** `CONFIG`, `name`, `version`, `description`, `main` (+128 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `CONFIG`, `name`, `version` to the rest of the system?**
  _133 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.12804878048780488 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Should `Community 7` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._
- **Should `Community 10` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Should `Community 11` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._