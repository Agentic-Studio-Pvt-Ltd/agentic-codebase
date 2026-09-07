#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentify :: scripts/discover.py  --  phase 1, the repo analyzer.

Walks a repository ONCE and emits a single JSON object on stdout describing
what the repo is made of, so the model never has to scrape the tree itself.

    python3 "$SKILL_DIR/scripts/discover.py" --repo /path/to/repo

Design constraints (build contract, PRD 7.2):

* Python 3.9+, standard library only, no network calls, ever.
* Under 10 seconds on a 200k-line repo.  One `os.walk` pass with aggressive
  pruning; `--timeout-s` is a soft budget that is checked *during* the walk.
  Blowing the budget degrades the output, it never hangs and never raises.
* The main walk NEVER follows symlinks -- cycles, and a link can walk the
  analyzer straight out of the repo.  The agent config directories
  (`.claude/skills`, `.claude/agents`, ...) are the one exception, scanned
  separately by `scan_agentic_dirs` WITH links followed, because a shared
  skill store symlinked into `.claude/skills/` is a skill the agent really
  loads: missing it hides that skill from de-duplication and undercounts the
  maturity check that reports what a repo already has.  That scan is
  depth-capped, entry-capped, cycle-proof, and refuses any target that
  resolves outside both the repo and the user's home.
* File contents are read only for: manifests, CI files, `.claude`/`.codex`
  config (including `.codex/config.toml`, scanned for `[mcp_servers.*]` by a
  hand-rolled bounded reader -- `tomllib` is 3.11+ and a dependency is
  forbidden), index docs (marker search), the first 4 KB of at most 200 skill
  and agent entrypoints for the provenance pass, and a bounded newline count
  for LOC.
* `config.toml` is the one file on either target that routinely holds a live
  credential, so it gets a VALUE ALLOWLIST, not a parser.  Section headers
  (`[mcp_servers.<n>]`, `[projects."<path>"]`, `[plugins."x@y"]`,
  `[marketplaces.<n>]`, `[features]`, `[hooks...]`) plus exactly three keys --
  `trust_level`, the `[features]` booleans, and whether
  `project_doc_fallback_filenames` contains `CLAUDE.md` -- are all that can be
  read.  Every other line is discarded before it is stored, so a bearer token,
  an `Authorization` header or an `[mcp_servers.x.env]` table cannot reach
  stdout whatever the file contains.  `--selftest` asserts this against a file
  shaped like a real one, and it was verified against the real
  `~/.codex/config.toml` on the development machine: names only, zero hits.
* Codex USER scope (`${CODEX_HOME:-~/.codex}` plus `~/.agents/skills`) is
  listed -- skills, rules, subagents, `hooks.json`, plugin cache, MCP server
  names -- because those load in every session in this repo and de-duplication
  is impossible without them.  It is reported in `user_scope` and never summed
  into `counts` or `maturity`: agentify builds repo-scoped files, and a global
  setup is not this repo's setup.  Cross-target identity is by RESOLVED path,
  because a Codex skills tree is routinely symlinked into (or imported from) a
  Claude Code one and must not be counted twice.
* `existing_agentic_config.maturity` is computed from the artifacts the TEAM
  wrote, not from every artifact found.  Vendored third-party skills -- ones a
  `skills-lock.json` installed, ones resolving through a vendor or
  plugin-cache directory, ones whose frontmatter names an external source --
  stay in `skills`/`agents`/`counts` because de-duplication needs them, and
  are excluded only from the `>= 5` threshold that flips the run into
  a throttle that no longer exists.  Measured: a repo with 17 skills, 16 of
  them installed library guides, was throttled to audit-only caps and refused
  to build the
  setup it most needed.  `classify_provenance` errs toward calling an artifact
  the team's own, which errs toward reporting an existing setup rather than
  missing one.
* Secrets are never read.  Any path matching `lib.scrub.is_secret_path` is
  refused.  `.env*` files are the single exception and get names-only
  treatment: everything left of the first `=` on a line, and the value is
  never bound to a variable at all (`line[:line.find("=")]`).
* Exit codes follow the shared contract in `lib/emit.py`'s module docstring,
  which is the single normative statement -- do not restate it here and do not
  invent a code.  In one line: a missing, empty, unreadable or not-a-directory
  `--repo` is DEGRADED, so it prints the full schema with empty values plus a
  `warnings` entry and exits 0.  Exit 1 is reserved for an unhandled
  exception, which `emit.main_guard()` turns into JSON on the way out.

  This matters more here than anywhere else in the pipeline: discover.py is
  phase 1, and an agent reading a non-zero exit from phase 1 abandons a run
  that should have continued on reduced evidence.

`commands` is RESOLVED, never synthesized.  A slot is filled only from an
entry that literally exists in a manifest -- a package.json/composer.json
script, a Makefile target, a justfile recipe, a configured `[tool.x]` section
in pyproject.toml/setup.cfg/tox.ini -- or from a subcommand that is universal
for a toolchain whose manifest is present (`cargo test`, `go build ./...`,
`<pm> install`).  A dependency on its own never fills a slot: `typescript` in
devDependencies does not tell you whether this repo typechecks with
`tsc --noEmit`, `tsc -b`, or `tsc -p tsconfig.ts.json`.  When nothing matches,
the slot stays `""` and two warnings say which slots are empty and which
dependency-only tools were seen, so the model asks instead of inventing.

Provenance rides in `raw_scripts["#commands"]`: seven keys, one per slot, each
a citation line `"<manifest>#<key> (<how>) -> <command>; also: ..."` naming the
file, the entry, why it matched (name / body / configured tool / toolchain
convention) and every other entry that also qualified.  "#" cannot begin a
repo-relative path, so the key can never collide with a real manifest, and the
value keeps `raw_scripts`' `{str: {str: str}}` shape.

A repo can run MORE THAN ONE workspace system at once, so `monorepo` reports
them all.  `is_monorepo`, `tool` and `workspaces` keep their old names, types
and meaning for a single-value consumer -- `tool` is still one string, and
`workspaces` is still a flat glob list, now the union across systems with the
negations moved out.  Three keys are new: `tools` (every system's tool),
`systems` (`{tool, manifest, workspaces, excludes}` per declaration, so globs
stay with the manifest that declared them) and `task_runners` (turbo.json,
nx.json and friends -- a layer ON TOP of a workspace system, never one itself).
`excludes` holds the negations that used to sit inline in `workspaces`.  See
`detect_monorepo`.  Only the ROOT manifests declare the repo's workspaces; a
nested `package.json` "workspaces" or `[workspace]` is counted and reported in
`warnings`, never merged into the root block.

Run `python3 scripts/discover.py --selftest` for a sub-second sanity check
(imports resolve, emit round-trips, regexes compile, a synthetic repo walks
end to end).  It prints the shared selftest JSON and exits 1 on any failure.

LOC numbers are ESTIMATES: newline counts, per-file read capped at 2 MB and
scaled by size beyond that, and only over code files (markdown, JSON, YAML and
TOML are excluded so a docs-heavy repo does not land in the wrong size bucket).
The `warnings` array says so on every run.
"""

import json
import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from lib import emit as emitlib  # noqa: E402
from lib import scrub as scrublib  # noqa: E402

TOOL = "discover.py"
SCHEMA_VERSION = emitlib.SCHEMA_VERSION

#: discover.json is the phase-3 evidence base, so it gets a bigger cap than
#: the transcript miner's ~3k tokens.  ~10k tokens.
DEFAULT_CAP_CHARS = 40000

#: Lists whose tails may be dropped to fit the cap, weakest evidence last.
#: Trimmed in this order when the output exceeds the cap.  The per-target
#: artifact groups go LAST: they are small (about 1.7 KB on a repo with
#: 80 artifacts) and they are the only place that says which agent loads
#: which file, so shedding them first silently deleted the whole Codex
#: half of the answer while `folders` kept 6 KB of directory names.
TRIM_KEYS = ["folders", "env_var_names", "raw_scripts", "languages",
             "existing_agentic_config.artifacts_by_target"]

#: Reserved key inside `raw_scripts` carrying one citation line per command
#: slot: which manifest, which key, why it matched, and every other entry that
#: also qualified.  "#" cannot begin a repo-relative path, so it can never
#: collide with a real manifest, and the value keeps raw_scripts' shape
#: (a dict of string -> string) so existing consumers still walk it cleanly.
COMMAND_PROVENANCE_KEY = "#commands"

MAX_FILE_READ_BYTES = 512 * 1024       # manifests, CI files, config
MAX_LOC_READ_BYTES = 2 * 1024 * 1024   # per file, for newline counting
MAX_TOTAL_READ_BYTES = 96 * 1024 * 1024
MAX_INDEX_DOC_BYTES = 2 * 1024 * 1024
MAX_ENV_LINES = 800
MAX_MANIFEST_READS = 60
#: per workspace system, and on the union in `monorepo.workspaces`
MAX_WORKSPACE_GLOBS = 40
#: how often the walk checks itself against the soft time budget
CLOCK_EVERY = 200
AGENTIFY_MARKER = "agentify:begin"

#: The general repo walk NEVER follows symlinks (cycles, and escaping the
#: repo).  These directories are the one exception, scanned separately by
#: `scan_agentic_dirs` WITH symlinks followed -- see that function for why and
#: for the bounds that keep it safe.
#
#: Codex note (verified 2026-09-05 against codex-cli 0.152.1): the repo-level
#: skills root is `.agents/skills`, NOT `.codex/skills`.  `.codex/skills` is
#: kept here anyway -- it is not a load path, but a directory a user created
#: by following the old guidance is still an artifact that must be
#: de-duplicated against, and a warning tells them it is inert.  Codex's real
#: repo-scoped homes are `.codex/agents/*.toml`, `.codex/rules/*.rules`,
#: `.codex/hooks.json` and `.codex/hooks/`.
AGENTIC_CONFIG_DIRS = (
    ".claude/skills", ".claude/agents", ".claude/rules", ".claude/commands",
    ".claude/hooks",
    ".codex/skills", ".codex/agents", ".codex/prompts",
    ".codex/rules", ".codex/hooks",
    ".agents/skills",
    ".cursor/rules",
)
#: Hard bounds on that scan.  A symlink can point anywhere, so every one of
#: these is a refusal, not a best effort.
AGENTIC_SCAN_MAX_DEPTH = 4        # levels below each config dir
AGENTIC_SCAN_MAX_ENTRIES = 4000   # files recorded across all config dirs
AGENTIC_SCAN_MAX_PER_DIR = 400    # entries read from any one directory


# ---------------------------------------------------------------------------
# Static knowledge
# ---------------------------------------------------------------------------

#: Always pruned, whatever `.gitignore` says.  Contract: node_modules, .git,
#: dist, build, .next, vendor, target, .venv, __pycache__.
PRUNE_DIRS = frozenset([
    ".git", "node_modules", "bower_components", "jspm_packages",
    "dist", "build", "out", "vendor", "target", "coverage", "tmp-build",
    "__pycache__", ".venv", "venv", "env-venv", ".tox", ".eggs", ".nox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".pytype",
    ".next", ".nuxt", ".svelte-kit", ".astro", ".output", ".parcel-cache",
    ".turbo", ".cache", ".yarn", ".pnpm-store", ".bundle", ".dart_tool",
    ".gradle", ".idea", ".terraform", ".serverless", ".sst", ".wrangler",
    ".vercel", ".netlify", ".angular", ".nx", ".expo", ".expo-shared",
    ".ipynb_checkpoints", ".DS_Store", "Pods", "DerivedData",
    "site-packages", "elm-stuff", "_build", "deps-cache", "cdk.out",
])

LOCKFILES = frozenset([
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "npm-shrinkwrap.json",
    "bun.lock", "bun.lockb", "deno.lock", "Cargo.lock", "poetry.lock",
    "uv.lock", "Pipfile.lock", "composer.lock", "Gemfile.lock", "go.sum",
    "mix.lock", "pubspec.lock", "Package.resolved", "packages.lock.json",
    "gradle.lockfile", "conan.lock", "requirements.lock",
])

#: extension -> language name.  Code only; see module docstring.
LANG_BY_EXT = {
    ".py": "Python", ".pyi": "Python", ".pyx": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".rake": "Ruby", ".php": "PHP",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".groovy": "Groovy",
    ".swift": "Swift", ".m": "Objective-C", ".mm": "Objective-C",
    ".c": "C", ".h": "C", ".cc": "C++", ".cpp": "C++", ".cxx": "C++",
    ".hpp": "C++", ".hh": "C++", ".cs": "C#", ".fs": "F#",
    ".scala": "Scala", ".clj": "Clojure", ".cljs": "Clojure",
    ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang",
    ".hs": "Haskell", ".ml": "OCaml", ".dart": "Dart", ".lua": "Lua",
    ".jl": "Julia", ".r": "R", ".pl": "Perl", ".pm": "Perl",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".fish": "Shell",
    ".ps1": "PowerShell", ".bat": "Batch",
    ".sql": "SQL", ".graphql": "GraphQL", ".gql": "GraphQL",
    ".proto": "Protocol Buffers", ".thrift": "Thrift",
    ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".sass": "SCSS", ".less": "Less", ".styl": "Stylus",
    ".tf": "Terraform", ".hcl": "HCL", ".zig": "Zig", ".nim": "Nim",
    ".sol": "Solidity", ".vim": "Vimscript", ".el": "Emacs Lisp",
}

MANIFEST_KINDS = {
    "package.json": "package.json",
    "deno.json": "deno.json", "deno.jsonc": "deno.json",
    "bunfig.toml": "bunfig.toml",
    "pyproject.toml": "pyproject.toml",
    "setup.py": "setup.py", "setup.cfg": "setup.cfg",
    "Pipfile": "Pipfile", "tox.ini": "tox.ini",
    "environment.yml": "conda", "environment.yaml": "conda",
    "Makefile": "Makefile", "makefile": "Makefile", "GNUmakefile": "Makefile",
    "justfile": "justfile", "Justfile": "justfile", ".justfile": "justfile",
    "Taskfile.yml": "Taskfile", "Taskfile.yaml": "Taskfile",
    "go.mod": "go.mod", "go.work": "go.work",
    "Cargo.toml": "Cargo.toml",
    "Gemfile": "Gemfile", "Rakefile": "Rakefile",
    "composer.json": "composer.json",
    "pom.xml": "pom.xml", "build.gradle": "build.gradle",
    "build.gradle.kts": "build.gradle", "settings.gradle": "build.gradle",
    "CMakeLists.txt": "CMakeLists.txt",
    "Dockerfile": "Dockerfile",
    "docker-compose.yml": "docker-compose", "docker-compose.yaml": "docker-compose",
    "compose.yml": "docker-compose", "compose.yaml": "docker-compose",
    "mix.exs": "mix.exs", "pubspec.yaml": "pubspec.yaml",
    "Package.swift": "Package.swift", "build.sbt": "build.sbt",
    "requirements.txt": "requirements.txt",
    "requirements-dev.txt": "requirements.txt",
    "requirements_dev.txt": "requirements.txt",
    "dev-requirements.txt": "requirements.txt",
}

#: lockfile -> (package manager, ecosystem)
PM_BY_LOCKFILE = {
    "bun.lock": ("bun", "js"), "bun.lockb": ("bun", "js"),
    "pnpm-lock.yaml": ("pnpm", "js"), "yarn.lock": ("yarn", "js"),
    "package-lock.json": ("npm", "js"), "npm-shrinkwrap.json": ("npm", "js"),
    "deno.lock": ("deno", "js"),
    "uv.lock": ("uv", "py"), "poetry.lock": ("poetry", "py"),
    "Pipfile.lock": ("pipenv", "py"),
    "Cargo.lock": ("cargo", "rust"), "go.sum": ("go", "go"),
    "Gemfile.lock": ("bundler", "ruby"), "composer.lock": ("composer", "php"),
    "mix.lock": ("mix", "elixir"), "pubspec.lock": ("pub", "dart"),
}

#: The JavaScript package managers, in the order used to break a tie between
#: two ROOT lockfiles when nothing is declared.  Reaching this order is already
#: an ambiguous repo, so it also raises a warning and empties commands.install.
JS_PACKAGE_MANAGERS = ("bun", "pnpm", "yarn", "npm", "deno")
_JS_LOCK_TIEBREAK = ("pnpm", "yarn", "bun", "npm", "deno")

#: How a package manager runs a named script.  Deno is the odd one out: it has
#: `deno task`, not `deno run <script>` (`deno run` executes a FILE), so the
#: generic "<pm> run %s" would emit a command that cannot work.
PM_RUN_FORMAT = {"deno": "deno task %s"}

#: A lockfile deeper than this never decides anything.  Depth 0 is the repo
#: root; 1-2 covers a workspace package (`apps/web/package-lock.json`).
MAX_NESTED_LOCK_DEPTH = 2

#: Path segments that mark a tree as *material under test* rather than as this
#: repo's own code.  A lockfile under one of them describes the fixture, not
#: the repo -- measured on vercel/turborepo, where 20+ fixture lockfiles under
#: `lockfile-tests/fixtures/` and `examples/` outvoted the root pnpm-lock.yaml
#: and made a pnpm monorepo report as bun.  Matched on the sub-words of each
#: segment, so `lockfile-tests` hits on `tests`.
_VENDORED_PATH_WORDS = frozenset([
    "fixture", "fixtures", "example", "examples", "template", "templates",
    "test", "tests", "testdata", "spec", "specs", "e2e", "demo", "demos",
    "sample", "samples", "snapshot", "snapshots", "integration",
    "benchmark", "benchmarks", "bench", "sandbox", "playground", "scratch",
])

#: dependency name (exact, or prefix when it ends in "/") -> framework label
DEP_FRAMEWORKS = [
    ("next", "Next.js"), ("nuxt", "Nuxt"), ("astro", "Astro"),
    ("@sveltejs/kit", "SvelteKit"), ("svelte", "Svelte"),
    ("@angular/core", "Angular"), ("solid-js", "SolidJS"),
    ("@remix-run/react", "Remix"), ("react-native", "React Native"),
    ("expo", "Expo"), ("react-dom", "React"), ("react", "React"),
    ("vue", "Vue"), ("preact", "Preact"), ("lit", "Lit"),
    ("express", "Express"), ("fastify", "Fastify"), ("hono", "Hono"),
    ("@nestjs/core", "NestJS"), ("koa", "Koa"), ("elysia", "Elysia"),
    ("@trpc/server", "tRPC"), ("graphql", "GraphQL"), ("apollo-server", "Apollo"),
    ("socket.io", "Socket.IO"),
    ("vite", "Vite"), ("webpack", "webpack"), ("rollup", "Rollup"),
    ("esbuild", "esbuild"), ("turbopack", "Turbopack"),
    ("tailwindcss", "Tailwind CSS"), ("styled-components", "styled-components"),
    ("typescript", "TypeScript"),
    ("jest", "Jest"), ("vitest", "Vitest"), ("mocha", "Mocha"),
    ("@playwright/test", "Playwright"), ("playwright", "Playwright"),
    ("cypress", "Cypress"), ("@testing-library/react", "Testing Library"),
    ("eslint", "ESLint"), ("prettier", "Prettier"), ("@biomejs/biome", "Biome"),
    ("@storybook/", "Storybook"),
    ("prisma", "Prisma"), ("@prisma/client", "Prisma"),
    ("drizzle-orm", "Drizzle ORM"), ("typeorm", "TypeORM"), ("sequelize", "Sequelize"),
    ("kysely", "Kysely"), ("mongoose", "Mongoose"),
    ("electron", "Electron"), ("@tauri-apps/api", "Tauri"),
    ("zod", "Zod"), ("better-auth", "Better Auth"), ("next-auth", "NextAuth"),
    ("@radix-ui/", "Radix UI"), ("@xyflow/react", "React Flow"), ("ai", "Vercel AI SDK"),
    ("@react-email/", "React Email"),
    # python
    ("django", "Django"), ("flask", "Flask"), ("fastapi", "FastAPI"),
    ("starlette", "Starlette"), ("tornado", "Tornado"), ("aiohttp", "aiohttp"),
    ("sqlalchemy", "SQLAlchemy"), ("alembic", "Alembic"), ("pydantic", "Pydantic"),
    ("celery", "Celery"), ("pytest", "pytest"), ("ruff", "Ruff"),
    ("black", "Black"), ("mypy", "mypy"), ("pyright", "pyright"),
    ("flake8", "flake8"), ("pylint", "pylint"), ("poetry", "Poetry"),
    ("numpy", "NumPy"), ("pandas", "pandas"), ("torch", "PyTorch"),
    ("transformers", "Transformers"), ("langchain", "LangChain"),
    # ruby / php / jvm
    ("rails", "Ruby on Rails"), ("sinatra", "Sinatra"), ("rspec", "RSpec"),
    ("rubocop", "RuboCop"),
    ("laravel/framework", "Laravel"), ("symfony/framework-bundle", "Symfony"),
    ("phpunit/phpunit", "PHPUnit"),
    ("spring-boot-starter", "Spring Boot"), ("junit", "JUnit"),
    # go / rust
    ("gin-gonic/gin", "Gin"), ("labstack/echo", "Echo"), ("gofiber/fiber", "Fiber"),
    ("go-chi/chi", "chi"), ("gorm.io/gorm", "GORM"),
    ("actix-web", "Actix Web"), ("axum", "Axum"), ("rocket", "Rocket"),
    ("tokio", "Tokio"), ("serde", "Serde"), ("clap", "clap"),
]

#: marker file (exact basename or a `prefix*` glob) -> framework label
FILE_FRAMEWORKS = [
    ("next.config.*", "Next.js"), ("nuxt.config.*", "Nuxt"),
    ("astro.config.*", "Astro"), ("svelte.config.*", "Svelte"),
    ("angular.json", "Angular"), ("remix.config.*", "Remix"),
    ("vite.config.*", "Vite"), ("webpack.config.*", "webpack"),
    ("tailwind.config.*", "Tailwind CSS"), ("postcss.config.*", "PostCSS"),
    ("tsconfig.json", "TypeScript"),
    ("jest.config.*", "Jest"), ("vitest.config.*", "Vitest"),
    ("playwright.config.*", "Playwright"), ("cypress.config.*", "Cypress"),
    ("eslint.config.*", "ESLint"), (".eslintrc*", "ESLint"),
    ("biome.json", "Biome"), ("biome.jsonc", "Biome"),
    (".prettierrc*", "Prettier"), ("prettier.config.*", "Prettier"),
    ("manage.py", "Django"), ("artisan", "Laravel"),
    ("schema.prisma", "Prisma"), ("drizzle.config.*", "Drizzle ORM"),
    ("Dockerfile", "Docker"), ("docker-compose.y*ml", "Docker Compose"),
    ("app.config.*", "Expo"), ("metro.config.*", "React Native"),
    ("turbo.json", "Turborepo"), ("nx.json", "Nx"),
    ("serverless.yml", "Serverless Framework"), ("wrangler.toml", "Cloudflare Workers"),
    ("main.tf", "Terraform"), ("components.json", "shadcn/ui"),
]

#: dependency name (exact, or prefix when it ends in "/") -> external service
DEP_SERVICES = [
    ("@stripe/", "stripe"), ("stripe", "stripe"),
    ("@supabase/", "supabase"), ("supabase", "supabase"),
    ("@neondatabase/", "neon"), ("@planetscale/", "planetscale"),
    ("@linear/", "linear"), ("linear-sdk", "linear"),
    ("posthog-js", "posthog"), ("posthog-node", "posthog"), ("posthog", "posthog"),
    ("@sentry/", "sentry"), ("sentry-sdk", "sentry"), ("sentry", "sentry"),
    ("dd-trace", "datadog"), ("datadog", "datadog"), ("ddtrace", "datadog"),
    ("@vercel/", "vercel"), ("vercel", "vercel"),
    ("netlify-cli", "netlify"), ("@netlify/", "netlify"),
    ("wrangler", "cloudflare"), ("@cloudflare/", "cloudflare"),
    ("aws-sdk", "aws"), ("@aws-sdk/", "aws"), ("boto3", "aws"), ("aws-cdk-lib", "aws"),
    ("@google-cloud/", "gcp"), ("google-cloud-storage", "gcp"),
    ("firebase", "firebase"), ("firebase-admin", "firebase"),
    ("@react-native-firebase/", "firebase"),
    ("@clerk/", "clerk"), ("better-auth", "better-auth"),
    ("auth0", "auth0"), ("@auth0/", "auth0"),
    ("resend", "resend"), ("twilio", "twilio"), ("@sendgrid/", "sendgrid"),
    ("openai", "openai"), ("@ai-sdk/openai", "openai"),
    ("@anthropic-ai/", "anthropic"), ("anthropic", "anthropic"),
    ("replicate", "replicate"),
    ("@playwright/test", "playwright"), ("playwright", "playwright"),
    ("cypress", "cypress"), ("@storybook/", "storybook"),
    ("@prisma/client", "prisma"), ("prisma", "prisma"),
    ("drizzle-orm", "drizzle"),
    ("ioredis", "redis"), ("redis", "redis"), ("@upstash/redis", "redis"),
    ("pg", "postgres"), ("postgres", "postgres"), ("psycopg2", "postgres"),
    ("psycopg2-binary", "postgres"), ("asyncpg", "postgres"),
    ("mongodb", "mongodb"), ("mongoose", "mongodb"), ("pymongo", "mongodb"),
    ("@elastic/elasticsearch", "elasticsearch"), ("elasticsearch", "elasticsearch"),
    ("@notionhq/client", "notion"), ("@slack/", "slack"), ("slack-sdk", "slack"),
    ("@octokit/", "github"), ("octokit", "github"), ("PyGithub", "github"),
    ("expo", "expo"), ("react-native-purchases", "revenuecat"),
    ("@revenuecat/", "revenuecat"),
    ("@sanity/", "sanity"), ("contentful", "contentful"),
    ("algoliasearch", "algolia"), ("@segment/", "segment"),
    ("mixpanel", "mixpanel"), ("mixpanel-browser", "mixpanel"),
    ("@amplitude/", "amplitude"),
    # background jobs
    ("@trigger.dev/", "trigger.dev"), ("trigger.dev", "trigger.dev"),
    ("inngest", "inngest"), ("@temporalio/", "temporal"), ("bullmq", "bullmq"),
    ("@upstash/qstash", "qstash"),
    # billing beyond stripe
    ("dodopayments", "dodo"), ("@dodopayments/", "dodo"),
    ("@lemonsqueezy/", "lemonsqueezy"), ("@paddle/", "paddle"), ("@polar-sh/", "polar"),
    # model providers
    ("@openrouter/", "openrouter"), ("@fal-ai/", "fal"), ("fal-client", "fal"),
    ("fal_client", "fal"), ("@google/generative-ai", "gemini"), ("@google/genai", "gemini"),
    ("google-generativeai", "gemini"), ("elevenlabs", "elevenlabs"), ("@elevenlabs/", "elevenlabs"),
    ("@deepgram/", "deepgram"), ("modal", "modal"),
    # media, storage, realtime, notifications
    ("uploadthing", "uploadthing"), ("@uploadthing/", "uploadthing"), ("cloudinary", "cloudinary"),
    ("@mux/", "mux"), ("@livekit/", "livekit"), ("pusher", "pusher"), ("pusher-js", "pusher"),
    ("ably", "ably"), ("@liveblocks/", "liveblocks"), ("@novu/", "novu"),
    ("@pinecone-database/", "pinecone"), ("@qdrant/", "qdrant"),
    ("@shopify/", "shopify"), ("@hubspot/", "hubspot"), ("discord.js", "discord"),
]

#: env-var-name prefix (or exact name) -> external service.  NAMES ONLY.
ENV_SERVICES = [
    ("STRIPE_", "stripe"), ("SUPABASE_", "supabase"), ("NEXT_PUBLIC_SUPABASE_", "supabase"),
    ("NEON_", "neon"), ("PLANETSCALE_", "planetscale"), ("PSCALE_", "planetscale"),
    ("DATABASE_URL", "postgres"), ("POSTGRES_", "postgres"), ("PGHOST", "postgres"),
    ("PGUSER", "postgres"), ("PGDATABASE", "postgres"), ("DIRECT_URL", "postgres"),
    ("REDIS_", "redis"), ("UPSTASH_", "redis"),
    ("MONGO", "mongodb"), ("SENTRY_", "sentry"), ("POSTHOG_", "posthog"),
    ("NEXT_PUBLIC_POSTHOG_", "posthog"),
    ("OPENAI_", "openai"), ("ANTHROPIC_", "anthropic"), ("CLAUDE_", "anthropic"),
    ("REPLICATE_", "replicate"),
    ("AWS_", "aws"), ("GCP_", "gcp"), ("GOOGLE_APPLICATION_", "gcp"),
    ("FIREBASE_", "firebase"), ("CLERK_", "clerk"), ("NEXT_PUBLIC_CLERK_", "clerk"),
    ("AUTH0_", "auth0"), ("BETTER_AUTH", "better-auth"), ("NEXTAUTH_", "next-auth"),
    ("RESEND_", "resend"), ("TWILIO_", "twilio"), ("SENDGRID_", "sendgrid"),
    ("LINEAR_", "linear"), ("NOTION_", "notion"), ("SLACK_", "slack"),
    ("GITHUB_", "github"), ("GH_", "github"), ("GITLAB_", "gitlab"),
    ("VERCEL_", "vercel"), ("NETLIFY_", "netlify"),
    ("CLOUDFLARE_", "cloudflare"), ("CF_ACCOUNT", "cloudflare"),
    ("REVENUECAT_", "revenuecat"), ("EXPO_", "expo"),
    ("SANITY_", "sanity"), ("CONTENTFUL_", "contentful"),
    ("ALGOLIA_", "algolia"), ("SEGMENT_", "segment"), ("MIXPANEL_", "mixpanel"),
    ("AMPLITUDE_", "amplitude"), ("DATADOG_", "datadog"), ("DD_API", "datadog"),
    ("JIRA_", "jira"), ("FIGMA_", "figma"), ("ELASTIC", "elasticsearch"),
    ("TRIGGER_", "trigger.dev"), ("INNGEST_", "inngest"), ("TEMPORAL_", "temporal"),
    ("QSTASH_", "qstash"),
    ("DODO_", "dodo"), ("LEMONSQUEEZY_", "lemonsqueezy"), ("LEMON_SQUEEZY_", "lemonsqueezy"),
    ("PADDLE_", "paddle"), ("POLAR_", "polar"),
    ("OPENROUTER_", "openrouter"), ("FAL_", "fal"), ("GEMINI_", "gemini"),
    ("GOOGLE_GENERATIVE_", "gemini"), ("GOOGLE_CLIENT_", "google-oauth"),
    ("ELEVENLABS_", "elevenlabs"), ("ELEVEN_", "elevenlabs"), ("DEEPGRAM_", "deepgram"),
    ("MODAL_", "modal"),
    ("R2_", "cloudflare"), ("CLOUDINARY_", "cloudinary"), ("UPLOADTHING_", "uploadthing"),
    ("MUX_", "mux"), ("LIVEKIT_", "livekit"), ("PUSHER_", "pusher"), ("ABLY_", "ably"),
    ("LIVEBLOCKS_", "liveblocks"), ("NOVU_", "novu"),
    ("PINECONE_", "pinecone"), ("QDRANT_", "qdrant"),
    ("SHOPIFY_", "shopify"), ("HUBSPOT_", "hubspot"), ("DISCORD_", "discord"),
    ("NEXT_PUBLIC_GA_", "google-analytics"), ("GA_MEASUREMENT", "google-analytics"),
]

#: repo-relative path suffix -> external service
FILE_SERVICES = [
    ("prisma/schema.prisma", "prisma"), ("supabase/config.toml", "supabase"),
    ("wrangler.toml", "cloudflare"), ("vercel.json", "vercel"),
    ("netlify.toml", "netlify"), ("playwright.config.ts", "playwright"),
    ("playwright.config.js", "playwright"), ("cypress.config.ts", "cypress"),
    ("drizzle.config.ts", "drizzle"), ("sentry.client.config.ts", "sentry"),
    ("sentry.server.config.ts", "sentry"), ("firebase.json", "firebase"),
    ("trigger.config.ts", "trigger.dev"), ("trigger.config.js", "trigger.dev"),
    ("trigger.config.mjs", "trigger.dev"),
    ("app.json", None),  # placeholder, filtered below
]
FILE_SERVICES = [(p, s) for p, s in FILE_SERVICES if s]

ZONE_NAMES = {
    "api": "api", "apis": "api", "routes": "api", "route": "api",
    "controllers": "api", "controller": "api", "handlers": "api",
    "endpoints": "api", "resolvers": "api", "graphql": "api", "trpc": "api",
    "server": "api", "services": "api",
    "db": "db", "database": "db", "models": "db", "model": "db",
    "schema": "db", "schemas": "db", "entities": "db", "repositories": "db",
    "prisma": "db", "drizzle": "db", "queries": "db", "dal": "db",
    "migrations": "migrations", "migration": "migrations", "migrate": "migrations",
    "alembic": "migrations", "versions": "migrations",
    "components": "components", "component": "components", "ui": "components",
    "views": "components", "widgets": "components", "screens": "components",
    "pages": "routes", "layouts": "components", "partials": "components",
    "test": "tests", "tests": "tests", "__tests__": "tests", "spec": "tests",
    "specs": "tests", "e2e": "tests", "cypress": "tests", "testing": "tests",
    "__mocks__": "tests", "fixtures": "tests",
    "docs": "docs", "doc": "docs", "documentation": "docs", "adr": "docs",
    "adrs": "docs", "rfcs": "docs",
    "config": "config", "configs": "config", "settings": "config",
    ".github": "config", "infra": "config", "infrastructure": "config",
    "terraform": "config", "k8s": "config", "kubernetes": "config",
    "helm": "config", "deploy": "config", "deployment": "config",
    "scripts": "scripts", "bin": "scripts", "tools": "scripts",
    "tooling": "scripts", "cli": "scripts", "tasks": "scripts",
    # the zones a real app is made of and the old table left `null`
    "actions": "actions",
    "trigger": "jobs", "jobs": "jobs", "workers": "jobs", "worker": "jobs",
    "queues": "jobs", "queue": "jobs", "crons": "jobs", "cron": "jobs", "inngest": "jobs",
    "lib": "lib", "utils": "lib", "util": "lib", "helpers": "lib", "shared": "lib",
    "common": "lib", "core": "lib",
    "hooks": "hooks", "store": "state", "stores": "state", "state": "state",
    "types": "types", "interfaces": "types",
    "public": "assets", "static": "assets", "assets": "assets",
    "styles": "styles", "css": "styles", "locales": "i18n", "i18n": "i18n",
    "emails": "email", "email": "email", "middleware": "api", "middlewares": "api",
}

#: Frameworks whose `app/` or `pages/` directory is the route tree, so a folder
#: named `app` is zone `routes` rather than a domain directory nobody classifies.
ROUTES_FRAMEWORKS = frozenset(["Next.js", "Remix", "Nuxt", "SvelteKit", "Astro"])

#: Binaries probed on PATH by name -- environment evidence, never repo
#: evidence.  A generated `qa` skill needs to know whether `agent-browser` is
#: here before it can name its browser driver; a `pr-reviewer` needs `gh`.
#: `shutil.which` reads nothing and runs nothing.
TOOLING_PROBES = (
    "agent-browser", "playwright", "gh", "psql", "docker", "vercel", "wrangler",
    "codex", "claude", "bun", "pnpm", "yarn", "npm", "node", "python3", "uv",
    "poetry", "cargo", "go",
)

DOC_KINDS = [
    (re.compile(r"^readme(\.[a-z]+)?$", re.I), "readme"),
    (re.compile(r"^contributing(\.[a-z]+)?$", re.I), "contributing"),
    (re.compile(r"^pull_request_template(\.[a-z]+)?$", re.I), "pr-template"),
    (re.compile(r"^issue_template(\.[a-z]+)?$", re.I), "issue-template"),
]
ADR_DIRS = frozenset(["adr", "adrs", "decisions", "rfc", "rfcs", "architecture-decisions"])
#: A directory whose prose is how-to material: each file there is a procedure
#: the developer wrote down, which blueprint.md §6.2 turns into a skill.
GUIDE_DIRS = frozenset([
    "guides", "guide", "how-to", "howto", "howtos", "recipes", "playbooks",
    "runbooks", "runbook", "cookbook", "tutorials",
])
GUIDE_STEM_RE = re.compile(
    r"^(adding|add|creating|create|how[-_]?to|writing|building|setting[-_]up|setup|"
    r"deploying|migrating|onboarding)([-_]|$)"
)
DESIGN_DOC_RE = re.compile(r"^(design|design[-_]?system|design[-_]?guidelines|ui[-_]?guidelines|brand)$")
#: index docs are reported under existing_agentic_config, not twice under docs
INDEX_DOC_BASENAMES = frozenset(["CLAUDE.md", "AGENTS.md", "CODEX.md"])
DOC_EXTS = frozenset([".md", ".mdx", ".rst", ".txt", ".adoc"])
#: the root-level catch-all is prose only, so requirements.txt stays a manifest
PROSE_EXTS = frozenset([".md", ".mdx", ".rst", ".adoc"])
OTHER_DOC_NAMES = frozenset([
    "architecture", "changelog", "security", "code_of_conduct", "codeowners",
    "roadmap", "support", "governance",
    "development", "testing", "deployment", "onboarding", "conventions",
])

CI_FILES = frozenset([
    ".gitlab-ci.yml", ".travis.yml", "azure-pipelines.yml", "Jenkinsfile",
    ".circleci/config.yml", "appveyor.yml", ".drone.yml", "cloudbuild.yaml",
    "bitbucket-pipelines.yml", ".woodpecker.yml",
])

ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
CI_RUN_RE = re.compile(r"^\s*(?:-\s+)?run:\s*(?:\|[-+]?|>[-+]?)?\s*(.*)$")
CI_SECRET_RE = re.compile(r"\$\{\{\s*(?:secrets|vars|env)\.([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.\-/]*)\s*:(?!=)")
#: A justfile recipe signature opens with an optional `@` -- which suppresses
#: the echo of the whole body -- and then the recipe name.  Only the NAME is
#: matched here; where the signature ends is `_just_signature_end`'s job,
#: because `docs port="8000": cog` and `alias t := test` carry characters no
#: single anchored pattern can tell apart.  The pattern this replaces,
#: `^([a-zA-Z0-9][a-zA-Z0-9_-]*)(?:\s+[^:=]*?)?:(?!=)`, allowed neither: no
#: leading `@`, and a parameter run that excluded `=`.  Measured on a fresh
#: clone of simonw/llm -- nine recipes, every one of them `@name ...:`, two
#: with parameters -- it matched ZERO, so `manifests` listed the Justfile,
#: `raw_scripts` held no entry for it, and commands.test / lint / typecheck
#: came back empty on a repo whose Justfile defines exactly those recipes.
JUST_RECIPE_RE = re.compile(r"^@?([A-Za-z_][A-Za-z0-9_-]*)")

#: justfile line-openers that bind or configure instead of defining a recipe:
#: `set shell := [...]`, `export FOO := "1"`, `alias t := test`,
#: `import 'common.just'`, `mod docs`.  Each can carry a colon, so the name is
#: what keeps them out of the recipe table.
JUST_DIRECTIVES = frozenset(
    ["set", "export", "unexport", "alias", "import", "mod"])

#: Recipe body lines that run but characterize nothing: a comment, the `#!`
#: shebang that ALWAYS opens a shebang recipe, or shell option setup.
JUST_BODY_NOISE_RE = re.compile(r"^(?:#|set\s+[-+]|shopt\s)")


# ---------------------------------------------------------------------------
# .gitignore
# ---------------------------------------------------------------------------

class GitignoreMatcher(object):
    """
    A deliberately small `.gitignore` matcher: literals, `*.ext`, `dir/`,
    `/anchored`, `**`, `[classes]`, and `!negations`.  Anything more exotic
    (backslash escapes) is skipped and reported in `warnings`.

    Never raises.  An unparseable file yields a matcher that ignores nothing.
    """

    def __init__(self):
        self.rules = []          # (regex, dir_only, negate)
        self.skipped = []        # patterns we refused to interpret
        self.has_negation = False
        self._fast = None        # combined regex when there are no negations
        self._fast_dir = None

    # -- construction -------------------------------------------------
    def add_file(self, path):
        """Parse one `.gitignore`-format file.  Returns the number of rules."""
        added = 0
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for raw in fh:
                    if self.add_pattern(raw):
                        added += 1
        except (IOError, OSError):
            return 0
        return added

    def add_pattern(self, raw):
        line = raw.rstrip("\n").rstrip("\r")
        # trailing whitespace is insignificant unless escaped
        line = re.sub(r"(?<!\\)\s+$", "", line)
        if not line or line.startswith("#"):
            return False
        negate = False
        if line.startswith("!"):
            negate = True
            line = line[1:]
        if not line:
            return False
        dir_only = line.endswith("/")
        if dir_only:
            line = line[:-1]
        if not line:
            return False
        anchored = line.startswith("/") or ("/" in line)
        if line.startswith("/"):
            line = line[1:]
        if not line:
            return False
        body = _glob_to_regex(line)
        if body is None:
            self.skipped.append(raw.strip()[:60])
            return False
        prefix = "" if anchored else "(?:.*/)?"
        try:
            regex = re.compile("^" + prefix + body + "$")
        except re.error:
            self.skipped.append(raw.strip()[:60])
            return False
        self.rules.append((regex, dir_only, negate))
        if negate:
            self.has_negation = True
        return True

    def compile(self):
        """Build the single-regex fast path when no negation rules exist."""
        if self.has_negation or not self.rules:
            return
        alls = [r.pattern for r, _d, _n in self.rules]
        dirs = [r.pattern for r, d, _n in self.rules if d]
        nondirs = [r.pattern for r, d, _n in self.rules if not d]
        try:
            self._fast = re.compile("|".join(nondirs)) if nondirs else None
            self._fast_dir = re.compile("|".join(alls)) if dirs or nondirs else None
        except re.error:  # pragma: no cover - defensive
            self._fast = None
            self._fast_dir = None

    # -- matching -----------------------------------------------------
    def is_ignored(self, rel, is_dir):
        if not self.rules:
            return False
        if not self.has_negation:
            probe = self._fast_dir if is_dir else self._fast
            if probe is None:
                return False
            return probe.match(rel) is not None
        ignored = False
        for regex, dir_only, negate in self.rules:
            if dir_only and not is_dir:
                continue
            if regex.match(rel) is not None:
                ignored = not negate
        return ignored


def _glob_to_regex(pattern):
    """gitignore glob -> regex body, or None when the pattern is too exotic."""
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        ch = pattern[i]
        if ch == "\\":
            return None
        if ch == "*":
            if pattern.startswith("**", i):
                j = i + 2
                if j < n and pattern[j] == "/":
                    out.append("(?:[^/]+/)*")
                    i = j + 1
                    continue
                out.append(".*")
                i = j
                continue
            out.append("[^/]*")
            i += 1
            continue
        if ch == "?":
            out.append("[^/]")
            i += 1
            continue
        if ch == "[":
            close = pattern.find("]", i + 1)
            if close == -1:
                out.append(re.escape(ch))
                i += 1
                continue
            body = pattern[i + 1:close]
            if body.startswith("!"):
                body = "^" + body[1:]
            out.append("[" + body.replace("\\", "\\\\") + "]")
            i = close + 1
            continue
        out.append(re.escape(ch))
        i += 1
    body = "".join(out)
    # `foo` also ignores everything under `foo/`
    return body + "(?:/.*)?"


# ---------------------------------------------------------------------------
# Bounded, secret-refusing file access
# ---------------------------------------------------------------------------

class Reader(object):
    """Every byte this script reads goes through here."""

    def __init__(self, warnings):
        self.warnings = warnings
        self.bytes_read = 0
        self.refused = 0

    def budget_left(self):
        return self.bytes_read < MAX_TOTAL_READ_BYTES

    def text(self, path, max_bytes=MAX_FILE_READ_BYTES):
        """Read a bounded amount of text, or "" if the path is off limits."""
        if scrublib.is_secret_path(path):
            self.refused += 1
            return ""
        if not self.budget_left():
            return ""
        try:
            with open(path, "rb") as fh:
                data = fh.read(max_bytes)
        except (IOError, OSError):
            return ""
        self.bytes_read += len(data)
        if b"\x00" in data[:4096]:
            return ""
        try:
            return data.decode("utf-8", "replace")
        except Exception:  # pragma: no cover - defensive
            return ""

    def json(self, path):
        text = self.text(path)
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            # tolerate JSONC-style trailing commas / // comments
            stripped = re.sub(r"^\s*//.*$", "", text, flags=re.M)
            stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
            try:
                return json.loads(stripped)
            except ValueError:
                emitlib.warn(self.warnings, "could not parse JSON: %s" % os.path.basename(path))
                return None

    def count_lines(self, path, size):
        """
        Newline count for a code file.  Returns (loc, is_binary).

        Reads at most MAX_LOC_READ_BYTES and scales the count by file size
        beyond that, which is why every LOC number is called an estimate.
        """
        if size <= 0:
            return (0, False)
        if not self.budget_left():
            return (max(1, int(size / 32)), False)
        try:
            with open(path, "rb") as fh:
                data = fh.read(MAX_LOC_READ_BYTES)
        except (IOError, OSError):
            return (0, False)
        self.bytes_read += len(data)
        if not data:
            return (0, False)
        if b"\x00" in data[:8192]:
            return (0, True)
        lines = data.count(b"\n")
        if not data.endswith(b"\n"):
            lines += 1
        if size > len(data) and len(data) > 0:
            lines = int(lines * (float(size) / float(len(data))))
        return (lines, False)

    def env_var_names(self, path):
        """
        Dotenv NAMES only.  The value is never bound: we slice up to the first
        `=` with `line[:idx]` rather than splitting, so the right-hand side is
        never materialized as a string.
        """
        names = []
        if not scrublib.is_env_file(path):
            return names
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for count, raw in enumerate(fh):
                    if count >= MAX_ENV_LINES:
                        break
                    idx = raw.find("=")
                    if idx <= 0:
                        continue
                    head = raw[:idx].strip()          # <- left of "=" ONLY
                    if head.startswith("export "):
                        head = head[7:].strip()
                    if head.startswith("#") or not ENV_NAME_RE.match(head):
                        continue
                    names.append(head)
        except (IOError, OSError):
            return names
        return names


# ---------------------------------------------------------------------------
# Small parsers (stdlib only, tolerant, never raise)
# ---------------------------------------------------------------------------

def parse_toml_sections(text):
    """
    `{section_name: [line, ...]}` for a TOML-ish file.  Good enough to pull
    dependency names and detect `[tool.x]` blocks without a TOML parser
    (tomllib is 3.11+, and this script targets 3.9).
    """
    sections = {"": []}
    current = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line.strip("[]").strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


_TOML_KEY_RE = re.compile(r"^([A-Za-z0-9_.\-]+|\"[^\"]+\")\s*=")
_TOML_STR_RE = re.compile(r"[\"']([^\"']{1,120})[\"']")
_PY_REQ_SPLIT = re.compile(r"[\s<>=!~;\[\]#]")


def toml_dep_names(lines):
    names = []
    for line in lines:
        match = _TOML_KEY_RE.match(line)
        if match:
            key = match.group(1).strip('"')
            if key not in ("python", "version", "path", "git", "features"):
                names.append(key)
        for value in _TOML_STR_RE.findall(line):
            token = _PY_REQ_SPLIT.split(value.strip())[0]
            if token and re.match(r"^[A-Za-z][A-Za-z0-9_.\-]{0,60}$", token):
                names.append(token)
    return names


def toml_array_values(lines, key):
    """
    String values of `key = [...]`, whether the array is inline or spread over
    the lines that follow.  `parse_toml_sections` hands back one stripped line
    at a time, so a multi-line array arrives as `members = [`, then the entries,
    then `]` -- and a regex applied per line finds nothing in any of them.
    """
    opener = re.compile(r"^" + re.escape(key) + r"\s*=\s*(.*)$")
    values = []
    collecting = False
    for line in lines:
        if not collecting:
            match = opener.match(line)
            if match is None:
                continue
            rest = match.group(1).strip()
            if not rest.startswith("["):
                continue
            rest = rest[1:]
            if "]" in rest:
                values.extend(_TOML_STR_RE.findall(rest.split("]", 1)[0]))
                break
            values.extend(_TOML_STR_RE.findall(rest))
            collecting = True
        else:
            if "]" in line:
                values.extend(_TOML_STR_RE.findall(line.split("]", 1)[0]))
                break
            values.extend(_TOML_STR_RE.findall(line))
        if len(values) >= 200:
            break
    return values[:200]


def parse_requirements(text):
    names = []
    for raw in text.splitlines()[:500]:
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        token = _PY_REQ_SPLIT.split(line)[0].strip()
        if token and re.match(r"^[A-Za-z][A-Za-z0-9_.\-]{0,60}$", token):
            names.append(token.lower())
    return names


def parse_make_targets(text):
    """`{target: first recipe line}` in file order."""
    targets = {}
    lines = text.splitlines()
    for index, raw in enumerate(lines[:1200]):
        if raw.startswith("\t") or raw.startswith(" "):
            continue
        match = MAKE_TARGET_RE.match(raw)
        if not match:
            continue
        name = match.group(1)
        if name.startswith(".") or "$" in name or "%" in name:
            continue
        recipe = ""
        for follow in lines[index + 1:index + 6]:
            if follow.startswith("\t"):
                recipe = follow.strip()
                break
            if follow.strip() and not follow.startswith(" "):
                break
        targets[name] = recipe
    return targets


def _just_note(notes, kind, detail=""):
    """Record something the justfile reader deliberately did not report."""
    if notes is None or len(notes) >= 40:
        return
    notes.append((kind, str(detail)[:40]))


def _just_signature_end(rest):
    """
    Index of the colon that ends a recipe signature in `rest` -- everything on
    the line after the recipe name -- or -1 when the line is not a signature.

    Quote-aware on purpose: a colon inside a parameter default
    (`deploy env="eu:1":`) does not end the signature, and `:=` is a binding
    (`version := "1.0"`) rather than a recipe however much it looks like one.
    """
    quote = ""
    for index, char in enumerate(rest):
        if quote:
            if char == quote:
                quote = ""
        elif char in ("'", '"'):
            quote = char
        elif char == "#":
            return -1
        elif char == ":":
            return -1 if rest[index + 1:index + 2] == "=" else index
    return -1


def _just_params(text):
    """Split a recipe's parameters on whitespace, keeping quoted runs whole."""
    params = []
    current = ""
    quote = ""
    for char in text:
        if quote:
            current += char
            if char == quote:
                quote = ""
        elif char in ("'", '"'):
            quote = char
            current += char
        elif char.isspace():
            if current:
                params.append(current)
                current = ""
        else:
            current += char
    if current:
        params.append(current)
    return params


def _just_needs_args(text):
    """
    True when `just <name>` on its own cannot run the recipe.

    `*options` takes zero or more and `port="8000"` has a default, so both run
    bare.  A plain `target` and a `+args` (one or MORE) do not: just exits
    with "Recipe `x` got 0 arguments but takes 1".  Such a recipe exists, but
    `just x` is not a command that works, and a slot filled with a line that
    always fails is exactly the wrong-is-worse-than-empty case -- so the
    recipe is skipped and named in a warning instead.
    """
    for param in _just_params(text):
        token = param.lstrip("$")
        if not token or token.startswith("*") or "=" in token:
            continue
        return True
    return False


def _just_body(lines, start, limit=40):
    """
    The first line of a recipe body that names a command, or "".

    Skips blank lines, comments and the `#!/usr/bin/env bash` shebang that
    opens a shebang recipe, strips just's per-line `@` (suppress echo) and `-`
    (ignore failure) prefixes, and joins backslash continuations so what is
    reported is a command rather than a fragment.  The body is the WEAK
    signal: what fills a slot is the recipe NAME (`just test`), and the body
    only lets `_body_slot` recognize a recipe whose name says nothing.
    """
    index = start
    stop = min(len(lines), start + limit)
    while index < stop:
        raw = lines[index]
        index += 1
        if not raw.strip():
            continue
        if not raw.startswith((" ", "\t")):
            break  # unindented and non-blank: the next item has begun
        line = raw.strip()
        if line.startswith("@"):
            line = line[1:].lstrip()
        if line.startswith("-") and not line.startswith("--"):
            line = line[1:].lstrip()
        if not line or JUST_BODY_NOISE_RE.match(line):
            continue
        joined = 0
        while line.endswith("\\") and index < len(lines) and joined < 4:
            line = line[:-1].rstrip() + " " + lines[index].strip()
            index += 1
            joined += 1
        return line
    return ""


def parse_just_recipes(text, notes=None):
    """
    `{recipe: first body command}` for every PUBLIC, runs-bare recipe in a
    justfile, in file order.  Skips are appended to `notes` as
    `(kind, detail)` so the caller can report them instead of dropping them.

    This extracts recipe NAMES and one representative body line.  It is not a
    just parser and does not try to be: the name is what fills a slot, because
    `just <name>` is a command that literally exists once the recipe does --
    and nothing here ever invents a flag for it.  The syntax it has to
    survive, all of it measured on simonw/llm's Justfile and the just manual:

      `@test *options:`        a leading `@` suppresses the echo
      `docs port="8000": cog`  parameter defaults, then dependencies
      `test: build`            dependencies with no parameters
      `alias t := test`        an alias, `set shell := [...]` a setting,
                               `version := "1.0"` a binding -- none a recipe
      `_fmt:` / `[private]`    private recipes, hidden from `just --list`
      `deploy target:`         needs an argument, so `just deploy` fails
      a body opening `#!/usr/bin/env bash`, then `set -euo pipefail`
    """
    recipes = {}
    lines = text.splitlines()
    pending_private = False
    for index, raw in enumerate(lines[:1200]):
        if not raw.strip() or raw.startswith((" ", "\t")):
            continue  # blank, or a recipe body -- `_just_body` reads those
        line = raw.strip()
        if line.startswith("#"):
            continue
        if line.startswith("["):
            # Recipe attributes: `[private]`, `[group('build')]`, `[unix]`.
            # Only `private` changes what is reported; the rest are noise.
            attrs = [part.strip() for part in line.strip("[]").split(",")]
            if "private" in attrs:
                pending_private = True
            continue
        match = JUST_RECIPE_RE.match(line)
        if not match:
            pending_private = False
            continue
        name = match.group(1)
        rest = line[match.end():]
        if name in JUST_DIRECTIVES:
            _just_note(
                notes,
                "alias" if name == "alias" else
                ("import/mod" if name in ("import", "mod") else "setting"),
                (rest.split() or [name])[0],
            )
            pending_private = False
            continue
        end = _just_signature_end(rest)
        if end < 0:
            # A binding (`version := "1.0"`) or a line that is not a signature.
            pending_private = False
            continue
        private = pending_private or name.startswith("_")
        pending_private = False
        if private:
            _just_note(notes, "private recipe", name)
            continue
        if _just_needs_args(rest[:end]):
            _just_note(notes, "recipe with required parameters", name)
            continue
        recipes[name] = _just_body(lines, index + 1)
    return recipes


def parse_go_mod(text):
    names = []
    in_block = False
    for raw in text.splitlines()[:600]:
        line = raw.strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block and line == ")":
            in_block = False
            continue
        if in_block:
            token = line.split()[0] if line.split() else ""
        elif line.startswith("require "):
            parts = line.split()
            token = parts[1] if len(parts) > 1 else ""
        else:
            continue
        if token and not token.startswith("//"):
            names.append(token)
    return names


def parse_gemfile(text):
    return re.findall(r"^\s*gem\s+[\"']([^\"']+)[\"']", text, re.M)[:200]


# ---------------------------------------------------------------------------
# Walk state
# ---------------------------------------------------------------------------

class State(object):
    def __init__(self, root, warnings):
        self.root = root
        self.warnings = warnings
        self.file_count = 0
        self.dir_direct_files = {}
        #: rel_dir -> direct child basenames (capped) and kept subdirectory
        #: names, so folders[] can show the naming convention of a zone
        #: (`0001_init.sql`, `(protected)`) without the model listing it.
        self.dir_sample_files = {}
        self.dir_subdirs = {}
        self.lang_files = {}
        self.lang_loc = {}
        self.manifest_paths = []     # (rel, kind, depth)
        self.doc_paths = []          # (rel, kind, bytes, depth)
        self.ci_paths = []           # rel
        self.env_paths = []          # (rel, depth)
        self.agentic_paths = []      # rel
        #: lockfile basename -> (depth of the shallowest one, its rel path).
        #: Depth is load-bearing: a lockfile in a fixture is not this repo's
        #: package manager, so nothing may consult this map name-only.
        self.lockfiles = {}
        self.marker_files = set()    # basenames seen at depth <= 2
        self.rel_files = set()       # notable rel paths (shallow) for services
        self.ci_env_names = []       # env var NAMES referenced by CI files
        self.stopped_early = False


def _rel(root, path):
    rel = os.path.relpath(path, root)
    if rel == ".":
        return ""
    return rel.replace(os.sep, "/")


def walk(root, state, reader, matcher, deadline_ms, timer, max_files):
    """
    One pass.  Prunes hard, checks the clock, never follows symlinks.

    Symlink-following is confined to `scan_agentic_dirs`; see the module
    docstring for why the two walks differ.
    """
    content_deadline = int(deadline_ms * 0.65)
    checked = 0
    read_content = True

    def on_error(_exc):
        emitlib.warn(state.warnings, "unreadable directory skipped during walk")

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=on_error):
        if timer.elapsed_ms() > deadline_ms:
            state.stopped_early = True
            emitlib.warn(
                state.warnings,
                "time budget exceeded after %d files; walk stopped early "
                "and results are partial" % state.file_count,
            )
            break
        rel_dir = _rel(root, dirpath)
        depth = 0 if not rel_dir else rel_dir.count("/") + 1

        kept = []
        for name in dirnames:
            if name in PRUNE_DIRS:
                continue
            rel_child = name if not rel_dir else rel_dir + "/" + name
            if matcher.is_ignored(rel_child, True):
                continue
            if scrublib.is_secret_path(rel_child):
                continue
            kept.append(name)
        dirnames[:] = kept
        if rel_dir and kept:
            state.dir_subdirs[rel_dir] = sorted(kept)[:12]

        direct = 0
        for name in filenames:
            rel_path = name if not rel_dir else rel_dir + "/" + name
            if name in (".DS_Store", "Thumbs.db"):
                continue
            if matcher.is_ignored(rel_path, False):
                continue

            state.file_count += 1
            direct += 1
            checked += 1

            if checked % CLOCK_EVERY == 0:
                elapsed = timer.elapsed_ms()
                if read_content and elapsed > content_deadline:
                    read_content = False
                    emitlib.warn(
                        state.warnings,
                        "time budget: stopped reading file contents part-way; "
                        "LOC for the remaining files is size-estimated",
                    )
                if elapsed > deadline_ms:
                    state.stopped_early = True
                    emitlib.warn(
                        state.warnings,
                        "time budget exceeded after %d files; walk stopped early "
                        "and results are partial" % state.file_count,
                    )
                    break
            if state.file_count > max_files:
                state.stopped_early = True
                emitlib.warn(
                    state.warnings,
                    "--max-files (%d) reached; walk stopped early and results "
                    "are partial" % max_files,
                )
                break

            full = os.path.join(dirpath, name)
            lower = name.lower()
            _stem, ext = os.path.splitext(lower)

            if name in LOCKFILES:
                seen_lock = state.lockfiles.get(name)
                if seen_lock is None or depth < seen_lock[0]:
                    state.lockfiles[name] = (depth, rel_path)
                continue

            if depth <= 2:
                state.marker_files.add(name)
            if depth <= 3:
                state.rel_files.add(rel_path)

            kind = MANIFEST_KINDS.get(name)
            if kind is None and lower.startswith("requirements") and lower.endswith(".txt"):
                kind = "requirements.txt"
            if kind is None and lower.endswith(".csproj"):
                kind = "csproj"
            if kind is not None:
                state.manifest_paths.append((rel_path, kind, depth))

            if scrublib.is_env_file(name):
                state.env_paths.append((rel_path, depth))
                continue

            if rel_dir and not scrublib.is_secret_path(rel_path):
                sample = state.dir_sample_files.setdefault(rel_dir, [])
                if len(sample) < 200:
                    sample.append(name)

            if rel_dir.startswith(".github/workflows") and ext in (".yml", ".yaml"):
                state.ci_paths.append(rel_path)
            elif rel_path in CI_FILES or name in CI_FILES:
                state.ci_paths.append(rel_path)

            if (rel_dir == ".claude" or rel_dir.startswith(".claude/")
                    or rel_dir == ".codex" or rel_dir.startswith(".codex/")
                    or rel_dir == ".cursor" or rel_dir.startswith(".cursor/")
                    or rel_dir == ".husky"
                    or rel_path in ("CLAUDE.md", "AGENTS.md", ".cursorrules",
                                    ".mcp.json", "CODEX.md",
                                    ".github/copilot-instructions.md")):
                state.agentic_paths.append(rel_path)

            doc_kind = None if kind is not None else classify_doc(rel_dir, name, ext)
            if doc_kind is not None and depth <= 3:
                try:
                    size = os.path.getsize(full)
                except (IOError, OSError):
                    size = 0
                state.doc_paths.append((rel_path, doc_kind, size, depth))

            language = LANG_BY_EXT.get(ext)
            if language is not None and ".min." not in lower:
                state.lang_files[language] = state.lang_files.get(language, 0) + 1
                try:
                    size = os.path.getsize(full)
                except (IOError, OSError):
                    size = 0
                if read_content and not scrublib.is_secret_path(rel_path):
                    loc, is_binary = reader.count_lines(full, size)
                    if is_binary:
                        state.lang_files[language] -= 1
                        continue
                else:
                    loc = max(1, int(size / 32)) if size else 0
                state.lang_loc[language] = state.lang_loc.get(language, 0) + loc

        if direct:
            state.dir_direct_files[rel_dir] = state.dir_direct_files.get(rel_dir, 0) + direct
        if state.stopped_early:
            break


def classify_doc(rel_dir, name, ext):
    stem = os.path.splitext(name)[0].lower()
    top = rel_dir.split("/")[0] if rel_dir else ""
    if top in (".claude", ".codex", ".cursor", ".agents"):
        return None
    for regex, kind in DOC_KINDS:
        if regex.match(name):
            return kind
    if rel_dir.startswith(".github/ISSUE_TEMPLATE"):
        return "issue-template"
    if ext not in DOC_EXTS:
        return None
    parts = [p.lower() for p in rel_dir.split("/") if p]
    for part in parts:
        if part in ADR_DIRS:
            return "adr"
    # The kinds blueprint.md reads by name.  `design` licenses the designer
    # subagent and a doc-stated-check hook; `context` the memory rule; `guide`
    # a skill per procedure.  Root-level or under docs/, never inside code.
    if DESIGN_DOC_RE.match(stem) and (not parts or parts[0] in ("docs", "doc", "documentation")):
        return "design"
    if stem == "context" and not parts:
        return "context"
    if stem in ("style_guide", "styleguide", "style-guide"):
        return "style-guide"
    for part in parts:
        if part in GUIDE_DIRS:
            return "guide"
    if GUIDE_STEM_RE.match(stem) and parts and parts[0] in ("docs", "doc", "documentation"):
        return "guide"
    if stem in OTHER_DOC_NAMES:
        return "other"
    if parts and parts[0] in ("docs", "doc", "documentation"):
        return "other"
    if not parts and ext in PROSE_EXTS and name not in INDEX_DOC_BASENAMES:
        # a root-level prose file that is not an index doc: PRD.md, SPEC.md, ...
        return "other"
    return None


# ---------------------------------------------------------------------------
# Manifest analysis
# ---------------------------------------------------------------------------

class Manifests(object):
    def __init__(self):
        self.deps = {}            # dep name -> "<manifest rel path>"
        self.raw_scripts = {}     # rel path -> {name: cmd}
        self.root_scripts = {}
        self.pkg_json_root = None
        self.make_targets = {}
        self.just_recipes = {}
        self.composer_scripts = {}
        self.py_tools = set()
        self.py_sections = {}
        self.py_tool_sources = {}  # tool name -> (manifest rel path, section)
        self.has = set()          # manifest kinds present, ANY depth
        #: Manifest kinds that belong to THIS repo: shallow, and not under
        #: a fixture or example tree.  `has` includes every depth, so a
        #: pyproject.toml in an integration fixture added `pip` to a repo
        #: with no Python of its own (measured on vercel/turborepo).
        #: Anything that decides a package manager or a command reads THIS.
        self.own = set()
        #: Manifest kinds AT THE REPO ROOT.  A toolchain convention
        #: (`cargo test`, `go build ./...`, `bundle install`) is only
        #: universal for a repo whose manifest is the root one: run from
        #: the root of denoland/std, `cargo test` found nothing but the
        #: `crypto/_wasm` sub-crate's Cargo.toml, two levels down.
        self.root_kinds = set()
        #: One entry per workspace DECLARATION, globs kept with the manifest
        #: that declared them.  A repo can run more than one workspace system
        #: at once (turborepo: pnpm over apps/ + packages/, cargo over
        #: crates/), and flattening them is what made `tool` and `workspaces`
        #: describe two different systems.
        self.workspace_systems = []
        self.workspaces = []      # union of every system's include globs
        self.monorepo_tool = ""   # first named system; back-compat only
        #: workspace declarations found BELOW the repo root, counted and not
        #: used -- a nested package.json "workspaces" must never inflate the
        #: root monorepo block.
        self.nested_workspace_decls = 0
        #: rel paths actually parsed, in read order, so `manifests` in the
        #: payload can lead with the rows that have data behind them
        self.read_paths = []
        self.go_module = ""
        # Where each command-bearing manifest actually lives, so a resolved
        # command can cite the file it came from instead of a guessed name.
        self.root_scripts_path = ""
        self.make_path = ""
        self.just_path = ""
        self.composer_path = ""
        self.py_manifest_path = ""
        self.tox_path = ""
        self.requirements_path = ""
        self.requirements_rank = None   # (depth, plain-name-first, rel)
        self.deno_tasks = {}
        self.deno_path = ""
        self.cargo_path = ""
        self.go_path = ""
        self.gemfile_path = ""

    def add_workspace_system(self, tool, manifest, globs, excludes=()):
        """Register one declaration.  Returns True when it held any glob."""
        return self.add_workspace_row(
            build_workspace_system(tool, manifest, globs, excludes))

    def add_workspace_row(self, system):
        """Register an already-built declaration row."""
        if system is None:
            return False
        self.workspace_systems.append(system)
        for glob in system["workspaces"]:
            if glob not in self.workspaces:
                self.workspaces.append(glob)
        if system["tool"] and not self.monorepo_tool:
            self.monorepo_tool = system["tool"]
        return True


def build_workspace_system(tool, manifest, globs, excludes=()):
    """
    One workspace declaration as a row: `{tool, manifest, workspaces, excludes}`.

    Negation (`!packages/turbo` in pnpm and npm, `exclude = [...]` in cargo) is
    split out here rather than left in the include list.  A consumer that reads
    `workspaces` and expands the globs cannot tell `"!examples/non-monorepo"`
    from a directory literally named that, so leaving it inline produced a
    workspace list naming packages the repo had deliberately excluded.
    """
    includes = []
    negated = [str(item).strip() for item in excludes if str(item).strip()]
    for raw in globs:
        glob = str(raw).strip()
        if not glob:
            continue
        if glob.startswith("!"):
            rest = glob[1:].strip()
            if rest:
                negated.append(rest)
        else:
            includes.append(glob)
    if not includes and not negated:
        return None
    return {
        "tool": tool,
        "manifest": manifest,
        "workspaces": includes[:MAX_WORKSPACE_GLOBS],
        "excludes": negated[:MAX_WORKSPACE_GLOBS],
    }


# ---------------------------------------------------------------------------
# Workspace globs
#
# A workspace glob names a DIRECTORY ("packages/*", "crates/turborepo*"), so a
# manifest is a declared member when the directory holding it matches.  `*` and
# `?` stop at a path separator, `**` crosses them.  Deliberately not fnmatch:
# fnmatch's `*` eats `/`, which would make "packages/*" claim every manifest
# nested anywhere below packages/ and defeat the whole point of the tiering.
# ---------------------------------------------------------------------------

def _glob_to_re(glob):
    out = []
    index = 0
    length = len(glob)
    while index < length:
        char = glob[index]
        if char == "*":
            if glob[index + 1:index + 2] == "*":
                out.append(".*")
                index += 2
                if glob[index:index + 1] == "/":
                    index += 1
                continue
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        index += 1
    try:
        return re.compile("^" + "".join(out) + "$")
    except re.error:  # every literal is escaped, so this should be unreachable
        return None


class GlobSet(object):
    """Compiled include/exclude globs for workspace-member matching."""

    def __init__(self, includes, excludes):
        self.includes = [rx for rx in
                         (_glob_to_re(g) for g in list(includes)[:MAX_WORKSPACE_GLOBS])
                         if rx is not None]
        self.excludes = [rx for rx in
                         (_glob_to_re(g) for g in list(excludes)[:MAX_WORKSPACE_GLOBS])
                         if rx is not None]

    def __bool__(self):
        return bool(self.includes)

    __nonzero__ = __bool__

    def matches(self, directory):
        if not directory or not self.includes:
            return False
        for regex in self.excludes:
            if regex.match(directory):
                return False
        for regex in self.includes:
            if regex.match(directory):
                return True
        return False


def workspace_globset(manifests):
    includes, excludes = [], []
    for system in manifests.workspace_systems:
        includes.extend(system["workspaces"])
        excludes.extend(system["excludes"])
    return GlobSet(includes, excludes)


def _manifest_dir(rel):
    return rel.rsplit("/", 1)[0] if "/" in rel else ""


def _round_robin_by_kind(rows, budget):
    """
    Spread `budget` slots across manifest KINDS instead of handing them all to
    whichever kind the walk reached first.  Order inside a kind is preserved,
    so the shallowest and alphabetically earliest member of each kind wins its
    own slots.  Without this, 54 `Cargo.toml` under `crates/` took every slot
    on turborepo and not one `packages/*/package.json` was ever parsed.
    """
    if budget <= 0 or not rows:
        return []
    buckets = {}
    order = []
    for row in rows:
        kind = row[1]
        if kind not in buckets:
            buckets[kind] = []
            order.append(kind)
        buckets[kind].append(row)
    picked = []
    while len(picked) < budget:
        moved = False
        for kind in order:
            if len(picked) >= budget:
                break
            queue = buckets[kind]
            if queue:
                picked.append(queue.pop(0))
                moved = True
        if not moved:
            break
    return picked


def select_manifests(rows, globset, budget):
    """
    Shape-aware allocation of the read cap.

    Walk order is not a priority signal.  On a monorepo it is alphabetical, so
    one prolific kind in an early directory takes every slot before a declared
    workspace member in a later directory is ever reached.  Two tiers instead,
    round-robin by kind inside each: declared workspace members first, then
    everything else.  Root manifests never enter here -- they are read
    unconditionally, because they are what declare the workspaces.
    """
    members, rest = [], []
    for row in rows:
        if globset.matches(_manifest_dir(row[0])):
            members.append(row)
        else:
            rest.append(row)

    # A kind that appears ONLY outside the declared workspaces would otherwise
    # be invisible whenever tier 1 alone can exhaust the budget -- so hold back
    # one slot for each such kind, capped at a quarter of the budget so this
    # can never crowd out the workspace members it is protecting them from.
    member_kinds = set(row[1] for row in members)
    orphan_kinds = set(row[1] for row in rest) - member_kinds
    reserve = min(len(orphan_kinds), max(0, budget // 4))

    picked = _round_robin_by_kind(members, budget - reserve)
    picked.extend(_round_robin_by_kind(rest, budget - len(picked)))
    return picked, members, rest


def _coverage_line(eligible, read):
    """`kind read/total` for the kinds that lost the most, most-missed first."""
    totals, order = {}, []
    for _rel, kind, _depth in eligible:
        if kind not in totals:
            totals[kind] = [0, 0]
            order.append(kind)
        totals[kind][1] += 1
    for _rel, kind, _depth in read:
        totals[kind][0] += 1
    order.sort(key=lambda k: (-(totals[k][1] - totals[k][0]), k))
    shown = order[:6]
    parts = ["%s %d/%d" % (k, totals[k][0], totals[k][1]) for k in shown]
    if len(order) > len(shown):
        parts.append("+%d more kind(s)" % (len(order) - len(shown)))
    return ", ".join(parts)


#: Skip class -> how it reads in the warning, in the order shown.
_JUST_SKIP_LABELS = (
    ("private recipe", "private recipe(s)"),
    ("recipe with required parameters", "recipe(s) with required parameters"),
    ("alias", "alias(es)"),
    ("import/mod", "import/mod line(s), whose recipes are NOT read"),
    ("setting", "setting line(s)"),
)


def _warn_just_skips(warnings, rel, recipes, notes):
    """
    One bounded line saying what the root justfile held and this reader did
    not report.  Every skip here is still real: `just _fmt` runs, `just deploy
    prod` runs, an alias runs -- they are simply not offered as the command
    for a slot, and the user gets told which rather than wondering why the
    recipe they know about is missing.  A justfile that parsed to NOTHING is
    the louder case, and the one this whole reader exists to stop being
    silent: it says so even with no skips to report.
    """
    if not recipes and not notes:
        emitlib.warn(
            warnings,
            "%s parsed to no recipes; every command slot it could have filled "
            "is empty -- read it by hand before asking the user" % rel,
        )
        return
    if not notes:
        return
    groups = {}
    for kind, detail in notes:
        groups.setdefault(kind, []).append(_printable(detail))
    parts = []
    for kind, label in _JUST_SKIP_LABELS:
        rows = groups.get(kind) or []
        if not rows:
            continue
        shown = ", ".join([row for row in rows[:4] if row])
        parts.append("%d %s%s"
                     % (len(rows), label, " (%s)" % shown if shown else ""))
    if not parts:
        return
    emitlib.warn(
        warnings,
        "%s: %d recipe(s) read; skipped %s -- a skipped recipe is still "
        "runnable by name, it is just not offered as a command"
        % (rel, len(recipes), ", ".join(parts)),
    )


def _read_one_manifest(root, rel, kind, depth, reader, out):
    """
    Parse ONE manifest into `out`.  Which manifests get here, and in what
    order, is `read_manifests`' problem -- this function only parses.
    """
    full = os.path.join(root, rel.replace("/", os.sep))

    if kind == "deno.json":
        # Deno's scripts live under `tasks`, not `scripts`, and run with
        # `deno task <name>` -- `deno run <name>` executes a FILE.  Without
        # this branch a Deno repo has no manifest entries at all, and
        # denoland/std resolved to `cargo test` off a nested wasm crate.
        data = reader.json(full)
        if not isinstance(data, dict):
            return
        tasks = data.get("tasks")
        if isinstance(tasks, dict) and tasks:
            clean = {}
            for name, body in list(tasks.items())[:60]:
                if isinstance(body, dict):
                    body = body.get("command") or ""
                clean[str(name)] = _clean(str(body))[:200]
            out.raw_scripts[rel] = clean
            if depth == 0:
                out.deno_tasks = clean
                out.deno_path = rel
        return

    if kind == "package.json":
        data = reader.json(full)
        if not isinstance(data, dict):
            return
        if depth == 0:
            out.pkg_json_root = data
        for field in ("dependencies", "devDependencies", "peerDependencies",
                      "optionalDependencies"):
            block = data.get(field)
            if isinstance(block, dict):
                for name in block:
                    out.deps.setdefault(str(name), rel)
        scripts = data.get("scripts")
        if isinstance(scripts, dict) and scripts:
            clean = {}
            for name, cmd in list(scripts.items())[:60]:
                clean[str(name)] = _clean(str(cmd))[:200]
            out.raw_scripts[rel] = clean
            if depth == 0:
                out.root_scripts = clean
                out.root_scripts_path = rel
        spaces = data.get("workspaces")
        if isinstance(spaces, dict):
            spaces = spaces.get("packages")
        if isinstance(spaces, list) and spaces:
            if depth == 0:
                # tool is left empty here: package.json says THAT there are
                # workspaces, the lockfile says who runs them.  Resolved in
                # detect_monorepo.
                out.add_workspace_system(
                    "", rel, [str(w) for w in spaces[:MAX_WORKSPACE_GLOBS]])
            else:
                out.nested_workspace_decls += 1

    elif kind in ("Makefile",):
        targets = parse_make_targets(reader.text(full))
        if targets:
            out.raw_scripts[rel] = dict(
                (k, _clean(v)[:200]) for k, v in list(targets.items())[:60]
            )
            if depth == 0:
                out.make_targets = targets
                out.make_path = rel

    elif kind == "justfile":
        notes = []
        recipes = parse_just_recipes(reader.text(full), notes)
        if recipes:
            out.raw_scripts[rel] = dict(
                (k, _clean(v)[:200]) for k, v in list(recipes.items())[:60]
            )
            if depth == 0:
                out.just_recipes = recipes
                out.just_path = rel
        if depth == 0:
            # Only the root justfile warns.  A monorepo can carry one per
            # package, and a per-file line for each would bury the warning
            # that matters in noise.
            _warn_just_skips(reader.warnings, rel, recipes, notes)

    elif kind == "pyproject.toml":
        sections = parse_toml_sections(reader.text(full))
        if depth == 0:
            out.py_sections = sections
        if not out.py_manifest_path:
            out.py_manifest_path = rel
        for section, lines in sections.items():
            if section.startswith("tool."):
                tool = section.split(".")[1]
                out.py_tools.add(tool)
                out.py_tool_sources.setdefault(tool, (rel, section))
            if section in ("project", "build-system") or "dependencies" in section:
                for name in toml_dep_names(lines):
                    out.deps.setdefault(name.lower(), rel)
            if section.startswith("tool.poetry"):
                for name in toml_dep_names(lines):
                    out.deps.setdefault(name.lower(), rel)

    elif kind in ("requirements.txt", "Pipfile", "setup.py", "setup.cfg"):
        text = reader.text(full)
        if kind == "requirements.txt":
            # `requirements.txt`, `requirements-dev.txt` and
            # `docs/requirements.txt` all land here and they are NOT
            # interchangeable: the dev file installs the lint and test
            # toolchain, the docs one installs Sphinx.  Rank by (depth, then
            # plain name), so a root file always beats a nested one and a plain
            # name beats a dev one at the same depth.  Manifests are no longer
            # visited in depth order, so this must be a comparison and not a
            # first-writer-wins.  psf/requests has only `requirements-dev.txt`
            # at the root, and that is then the honest answer.
            rank = (depth, 0 if os.path.basename(rel).lower() == "requirements.txt" else 1, rel)
            if out.requirements_rank is None or rank < out.requirements_rank:
                out.requirements_rank = rank
                out.requirements_path = rel
            for name in parse_requirements(text):
                out.deps.setdefault(name, rel)
        else:
            if kind in ("setup.py", "Pipfile") and not out.py_manifest_path:
                out.py_manifest_path = rel
            if kind == "setup.cfg":
                # `[tool:pytest]`, `[flake8]`, `[mypy]` -- a configured tool
                # is a manifest entry, and the only python signal allowed to
                # fill a command slot.
                for section in parse_toml_sections(text):
                    tool = section.split(":")[-1].split("-")[0].strip()
                    if tool in ("pytest", "flake8", "mypy", "pylint", "isort",
                                "black", "ruff", "pyright", "coverage"):
                        out.py_tools.add(tool)
                        out.py_tool_sources.setdefault(tool, (rel, section))
            for name in re.findall(r"[\"']([A-Za-z][A-Za-z0-9_.\-]{1,40})[\"']", text)[:200]:
                out.deps.setdefault(name.lower(), rel)

    elif kind == "Cargo.toml":
        if not out.cargo_path:
            out.cargo_path = rel
        sections = parse_toml_sections(reader.text(full))
        for section, lines in sections.items():
            if "dependencies" in section:
                for name in toml_dep_names(lines):
                    out.deps.setdefault(name.lower(), rel)
            if section == "workspace":
                # `members = [` on its own line with the entries below it is
                # the common cargo spelling, and a per-line regex reads zero
                # from it -- which is how a 64-crate cargo workspace reported
                # tool "cargo" with no members at all.
                members = toml_array_values(lines, "members")
                excluded = toml_array_values(lines, "exclude")
                if depth == 0:
                    out.add_workspace_system("cargo", rel, members, excluded)
                elif members:
                    out.nested_workspace_decls += 1

    elif kind == "go.mod":
        if not out.go_path:
            out.go_path = rel
        text = reader.text(full)
        for name in parse_go_mod(text):
            out.deps.setdefault(name, rel)
        match = re.search(r"^module\s+(\S+)", text, re.M)
        if match:
            out.go_module = match.group(1)

    elif kind == "go.work":
        text = reader.text(full)
        uses = re.findall(r"^\s*(?:use\s+)?\.?/?([A-Za-z0-9_./-]+)", text, re.M)
        uses = [u for u in uses if u not in ("go", "use")][:MAX_WORKSPACE_GLOBS]
        if depth == 0:
            out.add_workspace_system("go-work", rel, uses)
        elif uses:
            out.nested_workspace_decls += 1

    elif kind == "Gemfile":
        if not out.gemfile_path:
            out.gemfile_path = rel
        for name in parse_gemfile(reader.text(full)):
            out.deps.setdefault(name.lower(), rel)

    elif kind == "composer.json":
        data = reader.json(full)
        if isinstance(data, dict):
            for field in ("require", "require-dev"):
                block = data.get(field)
                if isinstance(block, dict):
                    for name in block:
                        out.deps.setdefault(str(name), rel)
            if not out.composer_path:
                out.composer_path = rel
            scripts = data.get("scripts")
            if isinstance(scripts, dict):
                clean = {}
                for name, cmd in list(scripts.items())[:40]:
                    if isinstance(cmd, list):
                        cmd = " && ".join(str(part) for part in cmd[:6])
                    clean[str(name)] = _clean(str(cmd))[:200]
                out.raw_scripts[rel] = clean
                if depth == 0:
                    out.composer_scripts = clean

    elif kind == "tox.ini":
        out.py_tools.add("tox")
        if not out.tox_path:
            out.tox_path = rel
        for section in parse_toml_sections(reader.text(full)):
            out.py_tool_sources.setdefault("tox", (rel, section or "tox.ini"))


def read_manifests(root, state, reader, out):
    """
    Decide WHICH manifests to parse, then parse them.

    Two passes, because the ordering depends on the first one's results: the
    root manifests are what declare the workspaces, so a workspace-aware
    ordering of the nested manifests cannot exist until the root ones have been
    read.  `has` is filled from the complete walk and is never capped -- kind
    PRESENCE is cheap and drives package-manager detection, so it must not
    depend on which files won a read slot.
    """
    rows = sorted(state.manifest_paths, key=lambda item: (item[2], item[0]))
    for _rel, kind, _depth in rows:
        out.has.add(kind)
        if _depth <= MAX_NESTED_LOCK_DEPTH and not under_vendored_tree(_rel):
            out.own.add(kind)
        if _depth == 0:
            out.root_kinds.add(kind)

    eligible = [row for row in rows if row[2] <= 3]
    root_rows = [row for row in eligible if row[2] == 0]
    nested_rows = [row for row in eligible if row[2] > 0]

    read = []
    for rel, kind, depth in root_rows[:MAX_MANIFEST_READS]:
        _read_one_manifest(root, rel, kind, depth, reader, out)
        read.append((rel, kind, depth))

    # pnpm-workspace.yaml is a root manifest that MANIFEST_KINDS does not list
    # (it carries no dependencies and no scripts), but it DECLARES workspaces,
    # so it belongs in this pass with the other root manifests rather than at
    # reporting time.  Reading it late left the selection below blind to
    # "packages/*" on turborepo: every slot went to the cargo members, because
    # they were the only globs known when the choice was made.
    out.add_workspace_row(parse_pnpm_workspace(root, reader, state.warnings))

    globset = workspace_globset(out)
    picked, members, _rest = select_manifests(
        nested_rows, globset, MAX_MANIFEST_READS - len(read))
    for rel, kind, depth in picked:
        _read_one_manifest(root, rel, kind, depth, reader, out)
    read.extend(picked)
    out.read_paths = [row[0] for row in read]

    deeper = len(rows) - len(eligible)
    if deeper:
        emitlib.warn(
            state.warnings,
            "%d manifest(s) more than 3 levels deep were listed but not parsed"
            % deeper,
        )
    if len(read) < len(eligible):
        member_reads = sum(1 for row in read if row in members)
        emitlib.warn(
            state.warnings,
            "manifest reads capped at %d of %d eligible (%s); the %d root "
            "manifest(s) and %d of %d declared workspace-member manifest(s) "
            "were read first and the remaining slots were shared across "
            "manifest kinds, so what went unread is the manifests furthest "
            "from a declared workspace"
            % (len(read), len(eligible), _coverage_line(eligible, read),
               len(root_rows), member_reads, len(members)),
        )
    return out


def _clean(text):
    """Scrub before anything reaches stdout."""
    cleaned, _hits = scrublib.scrub(text)
    return cleaned.strip()


def _printable(text):
    """ASCII-safe, scrubbed, short: for echoing a file's own bytes in a warning."""
    cleaned = _clean(str(text))
    cleaned = re.sub(r"[^\x20-\x7e]", ".", cleaned)
    return cleaned[:40]


# ---------------------------------------------------------------------------
# Derived blocks
# ---------------------------------------------------------------------------

def lock_depth(state, name):
    """Depth of the shallowest lockfile with this basename, or None."""
    row = state.lockfiles.get(name)
    return None if row is None else row[0]


def _path_words(rel):
    """`"lockfile-tests/fixtures/x"` -> `{"lockfile","tests","fixtures","x"}`."""
    return set(w for w in re.split(r"[^a-z0-9]+", str(rel).lower()) if w)


def under_vendored_tree(rel):
    """
    True when a path sits under material-under-test rather than under this
    repo's own code -- a fixture, an example, a template, a sample.
    """
    parent = "/".join(str(rel).split("/")[:-1])
    return bool(_path_words(parent) & _VENDORED_PATH_WORDS)


def lock_evidence(state, warnings):
    """
    Root-scoped, ranked lockfile evidence -- never "any lockfile anywhere wins".

    Returns `(root, nested, ignored)`, each a list of
    `(package manager, ecosystem, lockfile name, rel path, depth)`:

      * `root`    -- depth 0.  The repo's own lockfiles.
      * `nested`  -- depth 1..MAX_NESTED_LOCK_DEPTH, outside any fixture or
                     example tree.  A real workspace package; usable only for
                     an ecosystem the root says nothing about.
      * `ignored` -- everything else: fixtures, examples, vendored trees, and
                     anything buried deeper than a workspace package.  Reported
                     in a warning, never allowed to decide.
    """
    root, nested, ignored = [], [], []
    for name in sorted(state.lockfiles):
        entry = PM_BY_LOCKFILE.get(name)
        if not entry:
            continue
        depth, rel = state.lockfiles[name]
        row = (entry[0], entry[1], name, rel, depth)
        if depth == 0:
            root.append(row)
        elif depth <= MAX_NESTED_LOCK_DEPTH and not under_vendored_tree(rel):
            nested.append(row)
        else:
            ignored.append(row)
    if ignored:
        emitlib.warn(
            warnings,
            "%d lockfile(s) live under a fixture, example or vendored tree and "
            "were NOT treated as this repo's package manager: %s"
            % (len(ignored), ", ".join(row[3] for row in ignored[:6])),
        )
    return root, nested, ignored


def declared_js_pm(manifests):
    """
    The package manager the ROOT package.json *declares* -- the strongest
    signal there is, and it outranks every lockfile and every heuristic.

    `packageManager` is what corepack reads and what the repo's own CI obeys;
    `devEngines.packageManager.name` is the newer spelling of the same promise.
    A repo can carry a stray `bun.lock` from one developer's `bun install` and
    still be a pnpm repo -- measured on vercel/turborepo.  Returns
    `(pm, "package.json#packageManager = \\"pnpm@12.0.0\\"")` or `("", "")`.
    """
    data = manifests.pkg_json_root or {}
    if not isinstance(data, dict):
        return ("", "")
    declared = data.get("packageManager")
    if isinstance(declared, str) and declared.strip():
        name = declared.split("@")[0].strip().lower()
        if name in JS_PACKAGE_MANAGERS:
            return (name, 'package.json#packageManager = "%s"'
                    % _printable(declared.strip()))
    dev = data.get("devEngines")
    if isinstance(dev, dict):
        block = dev.get("packageManager")
        rows = block if isinstance(block, list) else [block]
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip().lower()
            if name in JS_PACKAGE_MANAGERS:
                return (name, 'package.json#devEngines.packageManager.name = "%s"'
                        % _printable(name))
    return ("", "")


def detect_package_managers(state, manifests, warnings):
    """
    `(package_managers, js)` where `js` describes how the JavaScript package
    manager was decided: `{"pm": "", "reason": "", "ambiguous": False}`.

    Precedence, strongest first, and nothing below may override anything above:

      1. `packageManager` / `devEngines` in the ROOT package.json.
      2. A lockfile at the repo ROOT.
      3. A lockfile in a workspace package (depth <= 2, not a fixture), for an
         ecosystem the root is silent about.
      4. The manifest's own default (`package.json` with nothing else -> npm).

    Two root lockfiles from different managers with nothing declared is
    genuinely ambiguous: the list still reports a deterministic pick so the
    rest of the run has something to say, `ambiguous` is set, and
    `resolve_commands` leaves `commands.install` EMPTY rather than tell the
    user's agent to run `npm install` in a pnpm repo.
    """
    root_locks, nested_locks, _ignored = lock_evidence(state, warnings)
    found = []

    def add(pm):
        if pm and pm not in found:
            found.append(pm)

    root_ecosystems = set(row[1] for row in root_locks)
    for row in root_locks:
        add(row[0])
    dropped_nested = []
    for row in nested_locks:
        if row[1] in root_ecosystems:
            dropped_nested.append(row)
        else:
            add(row[0])
    if dropped_nested:
        emitlib.warn(
            warnings,
            "%d nested lockfile(s) were ignored because the repo root already "
            "says which package manager this ecosystem uses: %s"
            % (len(dropped_nested), ", ".join(r[3] for r in dropped_nested[:6])),
        )

    js = {"pm": "", "reason": "", "ambiguous": False}
    declared, declared_reason = declared_js_pm(manifests)
    root_js = [row for row in root_locks if row[1] == "js"]
    root_js_pms = []
    for row in root_js:
        if row[0] not in root_js_pms:
            root_js_pms.append(row[0])

    if declared:
        js["pm"], js["reason"] = declared, declared_reason
        add(declared)
        conflicting = [pm for pm in root_js_pms if pm != declared]
        if conflicting:
            emitlib.warn(
                warnings,
                "package.json declares %s but the root also holds %s; the "
                "DECLARATION wins -- the lockfile(s) are stray"
                % (declared, ", ".join(
                    row[2] for row in root_js if row[0] in conflicting)),
            )
    elif len(root_js_pms) == 1:
        row = root_js[0]
        js["pm"] = row[0]
        js["reason"] = "%s at the repo root" % row[2]
    elif len(root_js_pms) > 1:
        js["ambiguous"] = True
        js["pm"] = next(
            (pm for pm in _JS_LOCK_TIEBREAK if pm in root_js_pms), root_js_pms[0])
        js["reason"] = "ambiguous: %s all at the repo root" % ", ".join(
            row[2] for row in root_js)
        emitlib.warn(
            warnings,
            "the repo root holds lockfiles for %d package managers (%s) and "
            "package.json declares none; commands.install is left empty on "
            "purpose -- ask the user which one this repo really uses"
            % (len(root_js_pms), ", ".join(row[2] for row in root_js)),
        )
    else:
        nested_js = [row for row in nested_locks if row[1] == "js"]
        if nested_js:
            js["pm"] = nested_js[0][0]
            js["reason"] = "%s (no root lockfile; workspace package only)" % nested_js[0][3]
            emitlib.warn(
                warnings,
                "no lockfile and no packageManager at the repo root; the "
                "package manager was read from %s, which may describe only "
                "that package" % nested_js[0][3],
            )

    if not js["pm"] and "deno.json" in manifests.root_kinds:
        # A root deno.json is a declaration in its own right: this repo is run
        # by Deno.  Without it denoland/std reported no JS toolchain at all.
        js["pm"] = "deno"
        js["reason"] = "deno.json at the repo root"
        add("deno")

    if "package.json" in manifests.own:
        if not js["pm"]:
            js["pm"] = "npm"
            js["reason"] = "package.json with no lockfile and no declaration (npm default)"
        add(js["pm"])

    if "pyproject.toml" in manifests.own and not any(
            pm in found for pm in ("uv", "poetry", "pipenv", "pip")):
        add("poetry" if "poetry" in manifests.py_tools else "pip")
    if "requirements.txt" in manifests.own and "pip" not in found:
        add("pip")
    if "Cargo.toml" in manifests.own and "cargo" not in found:
        add("cargo")
    if "go.mod" in manifests.own and "go" not in found:
        add("go")
    if "Gemfile" in manifests.own and "bundler" not in found:
        add("bundler")
    if "composer.json" in manifests.own and "composer" not in found:
        add("composer")

    # The decided JS manager leads the list so a consumer that reads
    # package_managers[0] is not looking at a fixture's leftovers.
    if js["pm"] in found:
        found.remove(js["pm"])
        found.insert(0, js["pm"])
    return found, js


def _js_pm(package_managers):
    """Legacy positional lookup.  Prefer `detect_package_managers(...)[1]`."""
    for pm in JS_PACKAGE_MANAGERS:
        if pm in package_managers:
            return pm
    return ""


def _py_runner(package_managers):
    if "uv" in package_managers:
        return "uv run "
    if "poetry" in package_managers:
        return "poetry run "
    if "pipenv" in package_managers:
        return "pipenv run "
    return ""


# ---------------------------------------------------------------------------
# Commands -- resolved, never invented
# ---------------------------------------------------------------------------
#
# NOTHING IN THIS SECTION MAY SYNTHESIZE A COMMAND.  A slot is filled only
# from something that literally exists in a manifest:
#
#   * a package.json or composer.json script, a deno.json task,
#   * a Makefile target, a justfile recipe,
#   * a configured tool section in pyproject.toml / setup.cfg / tox.ini,
#   * a subcommand that is universal for a toolchain whose manifest is AT THE
#     REPO ROOT (`cargo test`, `go build ./...`, `<pm> install`).
#
# If nothing matches, the slot stays "" and a warning names it.  An empty
# slot is a true statement about the repo; a guessed one is a lie that the
# generated index doc then hands to the user's agent as an instruction.
# A WRONG slot is worse than an empty one, because it reads as authoritative.
#
# Three rules carry most of the weight, each written against a measured miss:
#
#   1. THE PACKAGE MANAGER IS DECLARED, NOT INFERRED.  `packageManager` in the
#      root package.json outranks every lockfile, and a lockfile only counts
#      at the repo ROOT -- see `detect_package_managers`.  vercel/turborepo
#      declares pnpm@12.0.0 and resolved as bun, off fixture lockfiles.
#   2. INSTALLING IS THE MANAGER'S JOB, NOT A SCRIPT'S.  `commands.install`
#      comes from `<pm> install`; no package.json script can fill it --
#      see `_script_candidates`.  `install-hooks` installs git hooks.
#   3. A SLOT TOKEN IS NOT ENOUGH.  Everything else in the name must be a
#      recognized qualifier, or the name is rejected -- see QUALIFIER_TOKENS.
#      `build-docs` builds docs; `lint-staged` lints the index.
#
# The regression this rule exists to prevent, measured on a clean clone of
# tj/commander.js: `typescript` in devDependencies made discover.py emit
# `commands.typecheck = "npx tsc --noEmit"` -- a string that appears nowhere
# in that repo -- while its real `check:type` / `check:type:ts` /
# `check:type:js` scripts went unreported, because the old resolver was an
# exact-name lookup against a hand-maintained alias list.  Matching is now on
# the normalized token stream of the script NAME, with the script BODY as a
# weaker secondary signal, and every filled slot records where it came from.

#: Tokens that identify a slot inside a script / target / recipe NAME.
#: `strong` counts anywhere in the name; `weak` only as the first token.
#: Every strong token belongs to exactly ONE slot, and that uniqueness is what
#: lets `_STRONG_OWNER` say "build:types is a build script, not a typecheck
#: one" -- the first token decides which slot a name may compete for.
SLOT_NAME_TOKENS = [
    ("test", ("test", "tests", "spec", "specs", "jest", "vitest", "pytest",
              "mocha", "ava", "testing", "unittest", "phpunit", "rspec"), ("unit",)),
    ("lint", ("lint", "eslint", "oxlint", "stylelint", "flake8", "pylint",
              "clippy", "rubocop", "vet"), ()),
    ("typecheck", ("typecheck", "typechecks", "typechecking", "typing",
                   "tsc", "types", "type", "mypy", "pyright"), ()),
    ("format", ("format", "formatting", "fmt", "prettier", "black",
                "gofmt", "rustfmt", "autoformat"), ()),
    ("build", ("build", "compile", "bundle", "rollup", "webpack", "esbuild",
               "tsup", "dist"), ()),
    ("dev", ("dev", "develop", "serve", "server", "start"), ("watch",)),
    ("install", ("install", "bootstrap", "deps", "dependencies"), ("setup",)),
]

#: The seven contract slots, in the order the JSON reports them.
SLOT_ORDER = ("install", "dev", "build", "test", "lint", "typecheck", "format")

#: token -> the one slot that owns it.
_STRONG_OWNER = {}
for _slot, _strong, _weak in SLOT_NAME_TOKENS:
    for _token in _strong:
        _STRONG_OWNER[_token] = _slot

#: A sub-variant of a real command: still real, still reported as an
#: alternate, but not the one to name as "the" command for the slot.
VARIANT_TOKENS = frozenset([
    "watch", "e2e", "integration", "coverage", "cov", "ci", "debug", "all",
    "docker", "prod", "production", "release", "staging", "staged", "changed",
    "browser", "ui", "only", "legacy", "bench", "perf", "smoke", "acceptance",
    "snapshot", "update", "verbose", "silent",
])

#: Tokens that may sit beside a slot token WITHOUT changing what the command
#: does -- the flavour of the same action (`check:type:ts`, `test:watch`,
#: `lint:fix`, `build:prod`).  A remainder token outside this set is an
#: arbitrary noun naming a DIFFERENT object, and a name whose remainder is an
#: arbitrary noun does not name the slot however confidently its first token
#: reads.  Measured misses this exists to stop, all of them scoring 65-78 under
#: the old first-token rule and all of them wrong:
#:
#:   install-hooks  installs git hooks, not dependencies  (anthropics/claude-code-action)
#:   build:turbo    builds one cargo package              (vercel/turborepo)
#:   test-setup     prepares a fixture, runs no test
#:   build-docs     builds documentation, not the project
#:   lint-staged    lints the git index, not the repo
#:
#: The list is deliberately short.  A rejected name falls through to the BODY
#: match, so a script that really does run the tool is still found -- and one
#: that does not leaves the slot empty, which is the correct answer.
QUALIFIER_TOKENS = frozenset([
    # check/fix polarity -- already scored, listed here so it survives the gate
    "check", "fix", "write", "verify",
    # language / runtime flavour of the same action
    "ts", "tsx", "js", "jsx", "mjs", "cjs", "esm", "umd", "types", "type",
    "py", "python", "rs", "node", "deno", "bun",
    # environment / target
    "ci", "dev", "development", "prod", "production", "staging", "release",
    "local", "docker", "debug",
    # execution mode
    "watch", "all", "full", "quick", "fast", "serial", "parallel", "force",
    "quiet", "silent", "verbose", "strict", "once", "dry", "run",
    # test flavours -- narrower, still tests
    "unit", "integration", "e2e", "component", "coverage", "cov",
    "bench", "perf", "smoke", "acceptance", "snapshot",
])

#: Executables that identify a slot from a script BODY, used only when the
#: name says nothing.  Multi-word entries are matched as a prefix, longest
#: first, so `vite build` is a build and a bare `vite` is a dev server.
BODY_PREFIXES = [
    ("node --test", "test"), ("bun test", "test"), ("deno test", "test"),
    ("cargo test", "test"), ("go test", "test"), ("dotnet test", "test"),
    ("mix test", "test"), ("rake test", "test"), ("gradle test", "test"),
    ("vite build", "build"), ("next build", "build"), ("nuxt build", "build"),
    ("astro build", "build"), ("remix build", "build"), ("cargo build", "build"),
    ("go build", "build"), ("deno compile", "build"),
    ("next dev", "dev"), ("nuxt dev", "dev"), ("astro dev", "dev"),
    ("vite dev", "dev"), ("vite serve", "dev"), ("deno serve", "dev"),
    ("biome lint", "lint"), ("biome check", "lint"), ("ruff check", "lint"),
    ("cargo clippy", "lint"), ("go vet", "lint"), ("deno lint", "lint"),
    ("biome format", "format"), ("ruff format", "format"), ("cargo fmt", "format"),
    ("go fmt", "format"), ("deno fmt", "format"),
    ("deno check", "typecheck"),
]

#: Single-token executables -> slot.
BODY_TOOLS = {
    "tsc": "typecheck", "tsgo": "typecheck", "vue-tsc": "typecheck",
    "svelte-check": "typecheck", "mypy": "typecheck", "pyright": "typecheck",
    "pyre": "typecheck", "tsd": "typecheck", "flow": "typecheck",
    "eslint": "lint", "oxlint": "lint", "stylelint": "lint", "flake8": "lint",
    "pylint": "lint", "rubocop": "lint", "standard": "lint", "xo": "lint",
    "golangci-lint": "lint", "credo": "lint",
    "prettier": "format", "black": "format", "gofmt": "format",
    "rustfmt": "format", "autopep8": "format", "yapf": "format", "dprint": "format",
    "jest": "test", "vitest": "test", "mocha": "test", "ava": "test",
    "pytest": "test", "tap": "test", "karma": "test", "phpunit": "test",
    "rspec": "test", "tox": "test", "nyc": "test", "c8": "test",
    "tsup": "build", "rollup": "build", "webpack": "build", "esbuild": "build",
    "parcel": "build",
    "nodemon": "dev", "ts-node-dev": "dev", "vite": "dev", "uvicorn": "dev",
    "live-server": "dev",
}

#: Wrappers to strip off the front of a script body before looking at it.
_BODY_RUNNER_RE = re.compile(
    r"^(?:npx|bunx|pnpx|uvx|npm\s+exec|pnpm\s+exec|yarn\s+exec|bun\s+x|"
    r"yarn\s+dlx|pnpm\s+dlx|uv\s+run|poetry\s+run|pipenv\s+run|hatch\s+run|"
    r"bundle\s+exec|dotenv\s+--|cross-env|python3?\s+-m|node\s+--run|"
    r"[A-Za-z_][A-Za-z0-9_]*=\S*)\s+"
)
_BODY_SPLIT_RE = re.compile(r"&&|\|\||[;|]")
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NAME_SPLIT_RE = re.compile(r"[^a-z0-9]+")

#: A name match must clear this; a body match scores below every name match.
NAME_SCORE_FLOOR = 30
BODY_SCORE = 20
MAX_ALTERNATES = 3
MAX_PROVENANCE_CHARS = 300

#: Dependencies whose presence hints at a slot but NEVER fills one: how a repo
#: actually invokes them is a guess (`tsc --noEmit` vs `tsc -b` vs
#: `tsc -p tsconfig.ts.json`).  They are named in a warning instead, so the
#: model asks the user rather than inventing the flags.
TOOL_DEP_SLOTS = [
    ("typescript", "typecheck"), ("mypy", "typecheck"), ("pyright", "typecheck"),
    ("pytest", "test"), ("jest", "test"), ("vitest", "test"), ("mocha", "test"),
    ("rspec", "test"), ("phpunit", "test"),
    ("eslint", "lint"), ("ruff", "lint"), ("flake8", "lint"), ("pylint", "lint"),
    ("rubocop", "lint"), ("@biomejs/biome", "lint"),
    ("prettier", "format"), ("black", "format"),
    ("vite", "build"), ("webpack", "build"), ("rollup", "build"), ("tsup", "build"),
]


def _name_tokens(name):
    """`"check:type:ts"` and `"checkTypeTs"` both -> `["check", "type", "ts"]`."""
    text = _CAMEL_RE.sub(" ", str(name)).lower()
    return [token for token in _NAME_SPLIT_RE.split(text) if token]


def _score_name(slot, tokens, strong, weak):
    """
    How well a script name names this slot.  0 means "not a candidate".

    100 is a bare `test`; a weak token counts only as a whole name; a
    first-token hit beats a later one; every extra
    token costs a little, a variant token (`test:watch`) costs a lot, and the
    check/fix preference is inverted for `format` -- a format command is
    expected to WRITE (`fix:format`), a lint command to CHECK (`check:lint`).

    A slot token is NOT enough on its own.  Every token it does not account
    for must be a recognized qualifier (QUALIFIER_TOKENS) -- a flavour of the
    same action.  One arbitrary noun in the remainder and the name is rejected
    outright, because the noun is what the command actually acts on:
    `install-hooks` installs hooks, `build-docs` builds docs, `test-setup`
    sets up a fixture.  A first-token hit buys no exemption from this; it was
    exactly the first-token bonus that scored `install-hooks` 78 for the
    install slot on anthropics/claude-code-action.
    """
    hits = [token for token in tokens if token in strong]
    if hits:
        score = 60
        if tokens[0] in strong:
            score += 20
        if len(tokens) == 1:
            score += 20
        matched = set(hits)
    elif len(tokens) == 1 and tokens[0] in weak:
        # A weak token only names the slot when it is the WHOLE name: `watch`
        # is a dev server, `watch:css` is not; `setup` bootstraps a checkout,
        # `setup:company-secret` (measured, a real repo) does not.
        score = 50
        matched = set([tokens[0]])
    else:
        return 0
    for token in tokens:
        if token in matched or token in strong or token in weak:
            continue
        if token not in QUALIFIER_TOKENS:
            return 0
    for token in tokens:
        if token in matched:
            continue
        score -= 2
        if token in VARIANT_TOKENS:
            score -= 13
        if token in ("fix", "write"):
            score += 6 if slot == "format" else -6
        elif token == "check":
            score += -6 if slot == "format" else 2
    return score


def _body_slot(body):
    """
    `("test", "vitest")` for a body that runs ONE known tool, and nothing else.

    A chained body characterizes nothing, so it matches nothing.  This used to
    scan every segment and return the first tool it recognized anywhere in the
    chain, which on denoland/std made
    `ok = "deno task lint && deno fmt --check && deno task test:browser &&
    deno task test"` -- a full CI gate -- resolve as `commands.format`, on the
    strength of the `deno fmt` in its middle.  A script that runs four things
    is not the command for any one of them.
    """
    text = " ".join(str(body).split()).lower()
    if not text:
        return (None, "")
    segments = [seg for seg in
                (part.strip().lstrip("(").strip() for part in _BODY_SPLIT_RE.split(text))
                if seg]
    if len(segments) != 1:
        return (None, "")
    segment = segments[0]
    for _ in range(4):
        stripped = _BODY_RUNNER_RE.sub("", segment, count=1)
        if stripped == segment:
            break
        segment = stripped.strip()
    if not segment:
        return (None, "")
    for prefix, slot in BODY_PREFIXES:
        if segment == prefix or segment.startswith(prefix + " "):
            return (slot, prefix)
    head = segment.split(" ")[0]
    head = head.split("/")[-1]
    if head in BODY_TOOLS:
        return (BODY_TOOLS[head], head)
    return (None, "")


def _candidate(slot, command, manifest, key, how, score, detail=""):
    return {
        "slot": slot, "command": command, "manifest": manifest, "key": key,
        "how": how, "score": score, "detail": detail,
    }


#: Names that may fill the `install` slot from a NON-package.json manifest,
#: and only as the WHOLE name.  See `_script_candidates` for why package.json
#: is excluded entirely.
_EXACT_INSTALL_NAMES = frozenset(["install", "deps", "dependencies", "bootstrap"])


def _script_candidates(entries, manifest, key_prefix, runner_fmt, is_package_json=False):
    """
    Every slot a set of manifest entries can honestly fill, ranked.

    `entries` is `{name: body}` straight out of a manifest, so every command
    this produces names something that literally exists in that file.

    THE INSTALL SLOT IS SPECIAL, and the rule is: installing dependencies is
    the package MANAGER's job, not a script's.

      * From package.json the install slot is never filled at all.  npm, pnpm,
        yarn and bun all treat a script literally named `install` as a
        LIFECYCLE HOOK that runs *during* `<pm> install` (the node-gyp
        rebuild), so `<pm> run install` installs nothing; and any longer name
        is naming a different object -- `install-hooks` on
        anthropics/claude-code-action installs git hooks, and was resolved as
        that repo's dependency-install command.
      * From a Makefile, justfile or composer.json an install candidate must
        match one of `_EXACT_INSTALL_NAMES` as the whole name, and it still
        loses to `<pm> install` when a package manager is known.

    An install command that installs the wrong thing is worse than an empty
    slot: the empty slot asks, the wrong one instructs.
    """
    found = dict((slot, []) for slot in SLOT_ORDER)
    for name in sorted(entries):
        body = str(entries.get(name) or "")
        tokens = _name_tokens(name)
        if not tokens:
            continue
        if tokens[0] in ("pre", "post"):
            # A lifecycle hook, not a command: composer's `post-install-cmd`
            # ran as the install command would install nothing.
            continue
        owner = _STRONG_OWNER.get(tokens[0])
        matched = False
        for slot, strong, weak in SLOT_NAME_TOKENS:
            if not strong and not weak:
                continue
            if owner is not None and owner != slot:
                continue  # the first token already assigned this name a slot
            if slot == "install" and (
                    is_package_json
                    or len(tokens) != 1
                    or tokens[0] not in _EXACT_INSTALL_NAMES):
                continue
            score = _score_name(slot, tokens, strong, weak)
            if score >= NAME_SCORE_FLOOR:
                found[slot].append(_candidate(
                    slot, runner_fmt % name, manifest, key_prefix + name,
                    "name", score))
                matched = True
        if matched:
            continue
        slot, exe = _body_slot(body)
        if slot and slot != "install" and (owner is None or owner == slot):
            # When the NAME already claims a slot -- `build:turbo`, rejected
            # above because `turbo` is a noun -- the body may only confirm that
            # same slot, never overrule it.  `lint:tools-types` runs
            # `deno check`, but its author called it a lint task, and reporting
            # it as `commands.typecheck` contradicts the name in the manifest.
            found[slot].append(_candidate(
                slot, runner_fmt % name, manifest, key_prefix + name,
                "body", BODY_SCORE, exe))
    for slot in found:
        found[slot].sort(key=lambda cand: (-cand["score"], len(cand["key"]), cand["key"]))
    return found


_HOW_LABEL = {
    "name": "name match",
    "body": "body match",
    "config": "configured tool",
    "convention": "toolchain convention",
    "package-manager": "package manager",
    "ci": "CI workflow run step",
}


def _provenance(cand, alternates):
    """One citable line: which manifest, which key, why, and what else exists."""
    label = _HOW_LABEL.get(cand["how"], cand["how"])
    if cand["how"] == "body" and cand["detail"]:
        label = "body match: runs %s" % cand["detail"]
    elif cand["how"] == "convention" and cand["detail"]:
        label = "toolchain convention: %s" % cand["detail"]
    elif cand["how"] == "package-manager" and cand["detail"]:
        label = "package manager: %s" % cand["detail"]
    where = cand["manifest"]
    if cand["key"]:
        where = "%s#%s" % (where, cand["key"])
    line = "%s (%s) -> %s" % (where, label, cand["command"])
    if alternates:
        line += "; also: " + ", ".join(
            "%s -> %s" % (alt["key"] or alt["manifest"], alt["command"])
            for alt in alternates
        )
    #: Bounded: seven slots x this cap is the most provenance can ever add to
    #: the output budget, whatever a repo names its scripts.
    return _clean(line)[:MAX_PROVENANCE_CHARS]


def _ci_install_lines(ci, js_pm):
    """
    Literal `<pm> ci` / frozen-lockfile install lines from the CI workflows.

    Reported as an alternate on `commands.install`, never as the command
    itself: `npm ci` is what a CI runner does to a clean checkout, and telling
    a developer's agent to wipe node_modules is not what "how do I install"
    means.  It is real, it exists in the repo, so the user gets to see it.
    """
    if not js_pm:
        return []
    pattern = re.compile(
        r"^%s\s+(?:ci\b|install\b(?:\s+--(?:frozen-lockfile|immutable|"
        r"no-save|production))+)" % re.escape(js_pm))
    out = []
    for row in ci or []:
        for line in row.get("runs") or []:
            text = " ".join(str(line).split())
            if pattern.match(text) and text not in [c["command"] for c in out]:
                out.append(_candidate(
                    "install", text[:120], row.get("file") or "CI", "",
                    "ci", 5, "CI install step"))
    return out[:MAX_ALTERNATES]


def resolve_commands(state, manifests, package_managers, warnings,
                     js=None, ci=None):
    """
    The canonical command per slot, resolved -- never synthesized -- in
    contract order: package.json scripts -> Makefile -> justfile ->
    composer.json -> pyproject/tox tool sections -> Cargo/Go/package-manager
    conventions.  The first source that can honestly fill a slot wins it.

    Two orderings inside that are deliberate:

      * A NAME match anywhere beats a BODY match anywhere.  The old loop took
        the first source that could fill a slot at all, so a package.json
        script matched only on its body outranked a Makefile target that says
        `build` in its name -- weaker evidence winning on file order.
      * `install` is decided by the package manager FIRST (see
        `_script_candidates` for the rule), so no script named `install` can
        take it.  When the manager itself is ambiguous the slot stays empty.

    `js` is the decision block from `detect_package_managers`; `ci` is the
    parsed CI list, used only to list `npm ci`-style lines as alternates.

    Returns `(commands, provenance)`.  `commands` is the contract-fixed map of
    seven slots to command strings; `provenance` is the same seven keys mapped
    to a one-line citation ("" for an unfilled slot) that the caller parks
    under `raw_scripts["#commands"]`.  Commands are REPORTED, never executed.
    """
    cmds = dict((slot, "") for slot in SLOT_ORDER)
    chosen = {}
    alternates = dict((slot, []) for slot in SLOT_ORDER)

    def take(cand):
        """Fill a slot, if it is still empty.  Never overwrite better evidence."""
        if cmds[cand["slot"]]:
            return
        cmds[cand["slot"]] = cand["command"]
        chosen[cand["slot"]] = cand

    js = js or {"pm": "", "reason": "", "ambiguous": False}
    js_pm = js.get("pm") or ""
    if not js_pm:
        js_pm = _js_pm(package_managers)
    if not js_pm and "package.json" in manifests.own:
        js_pm = "npm"
    run_fmt = PM_RUN_FORMAT.get(js_pm, "%s run %%s" % js_pm if js_pm else "")

    # -- 0. install comes from the package manager, not from a script --------
    # A package manager that the repo DECLARES or that owns the root lockfile
    # is the authority on how this repo installs.  When two managers own the
    # root and nothing is declared the answer is unknown, and an unknown
    # install command is left empty rather than guessed.
    js_install_manifest = ""
    if "package.json" in manifests.own:
        js_install_manifest = manifests.root_scripts_path or "package.json"
    elif js_pm == "deno" and "deno.json" in manifests.root_kinds:
        js_install_manifest = manifests.deno_path or "deno.json"
    if js_pm and js_install_manifest:
        if js.get("ambiguous"):
            emitlib.warn(
                warnings,
                "commands.install left empty: the package manager is ambiguous "
                "(%s)" % (js.get("reason") or "two root lockfiles"),
            )
        else:
            take(_candidate(
                "install", "%s install" % js_pm, js_install_manifest, "",
                "package-manager", 90,
                js.get("reason") or "%s is the package manager" % js_pm))
            alternates["install"] = _ci_install_lines(ci, js_pm)

    # -- 1. named entries in manifests ---------------------------------------
    sources = []
    if manifests.root_scripts and js_pm:
        sources.append(_script_candidates(
            manifests.root_scripts, manifests.root_scripts_path or "package.json",
            "scripts.", run_fmt, True))
    if manifests.deno_tasks:
        sources.append(_script_candidates(
            manifests.deno_tasks, manifests.deno_path or "deno.json",
            "tasks.", "deno task %s"))
    if manifests.make_targets:
        sources.append(_script_candidates(
            manifests.make_targets, manifests.make_path or "Makefile", "", "make %s"))
    if manifests.just_recipes:
        sources.append(_script_candidates(
            manifests.just_recipes, manifests.just_path or "justfile", "", "just %s"))
    if manifests.composer_scripts:
        sources.append(_script_candidates(
            manifests.composer_scripts, manifests.composer_path or "composer.json",
            "scripts.", "composer run %s"))

    for how in ("name", "body"):
        for slot in SLOT_ORDER:
            if cmds[slot]:
                continue
            for found in sources:
                ranked = [cand for cand in (found.get(slot) or [])
                          if cand["how"] == how]
                if not ranked:
                    continue
                take(ranked[0])
                # Alternates are only ever the SAME kind of evidence as the
                # winner: a body match listed beside a name match reads as
                # "the repo has two build commands" when it does not.
                alternates[slot] = ranked[1:1 + MAX_ALTERNATES]
                break

    # -- 2. tools the repo has actually CONFIGURED ----------------------------
    # A `[tool.ruff]` block in pyproject.toml is a manifest entry: the repo
    # committed to that tool, and the tool has one documented invocation.  A
    # bare dependency is not -- see TOOL_DEP_SLOTS.
    tools = manifests.py_tools
    run = _py_runner(package_managers)

    def configured(tool, slot, command):
        if tool not in tools or cmds[slot]:
            return
        manifest, section = manifests.py_tool_sources.get(tool, ("pyproject.toml", "tool." + tool))
        take(_candidate(slot, run + command, manifest, section, "config", 50))

    configured("pytest", "test", "pytest")
    configured("ruff", "lint", "ruff check .")
    configured("flake8", "lint", "flake8")
    configured("pylint", "lint", "pylint .")
    configured("black", "format", "black .")
    configured("ruff", "format", "ruff format .")
    configured("mypy", "typecheck", "mypy .")
    configured("pyright", "typecheck", "pyright")

    # -- 3. conventions that are universal for a toolchain -------------------
    # Only commands that work in ANY repo of that toolchain.  `cargo run` and
    # `go run .` are deliberately absent: they fail outright in a library
    # crate or a module with no main package, which is most of them.
    def convention(present, slot, command, detail):
        if present and not cmds[slot]:
            take(_candidate(slot, command, present, "", "convention", 10, detail))

    # The JS install slot was decided in step 0 from the package manager
    # itself.  It is NOT retried here: if it is still empty the manager was
    # ambiguous, and a second pass would fill it with the guess step 0
    # refused to make.
    js_install_undecided = bool(js.get("ambiguous")) and "package.json" in manifests.own

    # A toolchain convention is only universal for a repo whose manifest is AT
    # THE ROOT.  `cargo test` run from the root of denoland/std reaches nothing
    # -- its only Cargo.toml is `crypto/_wasm/Cargo.toml`, a sub-crate -- yet
    # a nested manifest filled every slot with cargo commands that do not work.
    # `root_kinds`, not `own`, from here down.
    root_kinds = manifests.root_kinds

    py_manifest = manifests.py_manifest_path
    if "tox.ini" in root_kinds and not cmds["test"]:
        convention(manifests.tox_path or "tox.ini", "test", "tox", "tox.ini defines the envs")
    if not cmds["install"] and not js_install_undecided:
        if "uv" in package_managers:
            convention(py_manifest or "pyproject.toml", "install", "uv sync", "uv lockfile")
        elif "poetry" in package_managers:
            convention(py_manifest or "pyproject.toml", "install", "poetry install", "poetry project")
        elif "pipenv" in package_managers:
            convention(py_manifest or "Pipfile", "install", "pipenv install --dev", "Pipfile")
        elif "requirements.txt" in root_kinds:
            convention(manifests.requirements_path or "requirements.txt", "install",
                       "pip install -r %s" % (manifests.requirements_path or "requirements.txt"),
                       "requirements file")
        elif "pyproject.toml" in root_kinds or "setup.py" in root_kinds:
            convention(py_manifest or "pyproject.toml", "install", "pip install -e .",
                       "installable python project")

    if "Cargo.toml" in root_kinds:
        for slot, value in (("install", "cargo fetch"), ("build", "cargo build"),
                            ("test", "cargo test"), ("lint", "cargo clippy"),
                            ("format", "cargo fmt")):
            convention(manifests.cargo_path or "Cargo.toml", slot, value, "cargo")

    if "go.mod" in root_kinds:
        for slot, value in (("install", "go mod download"), ("build", "go build ./..."),
                            ("test", "go test ./..."), ("lint", "go vet ./..."),
                            ("format", "gofmt -l .")):
            convention(manifests.go_path or "go.mod", slot, value, "go toolchain")

    if "Gemfile" in root_kinds:
        convention(manifests.gemfile_path or "Gemfile", "install", "bundle install", "bundler")

    if "composer.json" in root_kinds:
        convention(manifests.composer_path or "composer.json", "install",
                   "composer install", "composer")

    # -- 4. provenance + honest reporting of what is NOT known ---------------
    provenance = dict((slot, "") for slot in SLOT_ORDER)
    for slot in SLOT_ORDER:
        if slot in chosen:
            provenance[slot] = _provenance(chosen[slot], alternates.get(slot) or [])

    # A CI install line is listed for the user's information, not as a rival
    # manifest entry, so it must not inflate this count.
    multi = []
    for slot in SLOT_ORDER:
        rival = [alt for alt in (alternates.get(slot) or []) if alt["how"] != "ci"]
        if rival:
            multi.append("%s (%d)" % (slot, 1 + len(rival)))
    if multi:
        emitlib.warn(
            warnings,
            "more than one manifest entry fills these slots, all listed in "
            "raw_scripts['#commands']: %s" % ", ".join(multi),
        )

    empty = [slot for slot in SLOT_ORDER if not cmds[slot]]
    if empty:
        emitlib.warn(
            warnings,
            "no manifest entry defines %s; the slot is empty on purpose -- ask "
            "the user, never invent a command"
            % ", ".join("commands.%s" % slot for slot in empty),
        )
        hinted = []
        for dep, slot in TOOL_DEP_SLOTS:
            if slot in empty and dep in manifests.deps and dep not in hinted:
                hinted.append(dep)
        if hinted:
            emitlib.warn(
                warnings,
                "these tools are dependencies but no script, target or config "
                "section says how this repo runs them, so no command was "
                "derived from them: %s" % ", ".join(hinted[:8]),
            )

    emitlib.warn(
        warnings,
        "commands were resolved from manifests, not executed; "
        "offer to run them only with the user's consent",
    )
    # `commands` is a contract-fixed map of slot -> command string (7 keys).
    # Do not add non-string members: consumers iterate it as commands.
    # Provenance rides in raw_scripts["#commands"] instead -- see main().
    return cmds, provenance


def _dep_lookup(table, deps):
    """Match a dep table (exact names + `prefix/` entries) against deps."""
    hits = []
    for key, label in table:
        if key.endswith("/"):
            for dep in deps:
                if dep.startswith(key):
                    hits.append((label, dep))
                    break
        else:
            lowered = key.lower()
            for dep in deps:
                dep_l = dep.lower()
                if dep_l == lowered or dep_l.endswith("/" + lowered):
                    hits.append((label, dep))
                    break
    return hits


def detect_frameworks(state, manifests):
    seen = {}
    for label, dep in _dep_lookup(DEP_FRAMEWORKS, manifests.deps):
        if label not in seen:
            seen[label] = "dep:%s in %s" % (dep, manifests.deps.get(dep, "manifest"))
    import fnmatch as _fnmatch
    for pattern, label in FILE_FRAMEWORKS:
        if label in seen:
            continue
        for name in state.marker_files:
            if _fnmatch.fnmatch(name, pattern):
                seen[label] = "file:%s" % name
                break
    if state.ci_paths and "GitHub Actions" not in seen:
        for rel in state.ci_paths:
            if rel.startswith(".github/workflows"):
                seen["GitHub Actions"] = "file:%s" % rel
                break
    return [{"name": name, "evidence": seen[name]} for name in sorted(seen)]


def detect_services(manifests, env_names, state):
    found = {}

    def add(name, evidence):
        entry = found.setdefault(name, {"kinds": set(), "evidence": []})
        entry["kinds"].add(evidence.split(":", 1)[0])
        if evidence not in entry["evidence"]:
            entry["evidence"].append(evidence)

    for label, dep in _dep_lookup(DEP_SERVICES, manifests.deps):
        add(label, "dep:%s" % dep)

    for name in env_names:
        upper = name.upper()
        for prefix, label in ENV_SERVICES:
            if upper.startswith(prefix) or upper == prefix:
                add(label, "env:%s" % name)
                break

    for suffix, label in FILE_SERVICES:
        for rel in state.rel_files:
            if rel == suffix or rel.endswith("/" + suffix):
                add(label, "file:%s" % rel)
                break

    out = []
    for name in sorted(found):
        entry = found[name]
        kinds = entry["kinds"]
        evidence = entry["evidence"]
        score = 0
        if "dep" in kinds:
            score += 2
        if "env" in kinds:
            score += 1
        if "file" in kinds:
            score += 1
        if len(evidence) >= 3:
            score += 1
        if score >= 3:
            confidence = "high"
        elif score == 2:
            confidence = "medium"
        else:
            confidence = "low"
        out.append({
            "name": name,
            "evidence": evidence[:6],
            "confidence": confidence,
        })
    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda item: (order[item["confidence"]], item["name"]))
    return out


def build_folders(state, frameworks=None, limit=140):
    """
    Depth-1..3 folders with RECURSIVE file counts, a zone guess, and a sample
    of what each holds.

    ZONES.  The deepest path segment with a known name wins (`app/api` is
    `api`, not `routes`), with three rules on top: anything under a
    dot-directory other than `.github` is `null` -- `.claude/hooks` is agent
    config, not a React hooks zone, and classifying it produced a rule
    candidate for it; `app` (or `src/app`) is `routes` only when a framework
    in ROUTES_FRAMEWORKS says that directory is the route tree; and a
    directory anywhere under a `jobs` zone stays `jobs`, so `trigger/tasks`
    is not demoted to `scripts` by its own basename.

    SAMPLES.  `sample_files` is up to six direct child basenames, sorted, and
    `subdirs` up to eight kept subdirectory names -- the migration naming
    pattern, the route groups, the component split, read off the tree instead
    of guessed.  Names only; nothing under a secret path.
    """
    names = set(frameworks or [])
    routes_fw = bool(names & ROUTES_FRAMEWORKS)
    agg = {}
    for rel_dir, count in state.dir_direct_files.items():
        if not rel_dir:
            continue
        parts = rel_dir.split("/")
        for depth in range(1, min(3, len(parts)) + 1):
            key = "/".join(parts[:depth])
            agg[key] = agg.get(key, 0) + count
    rows = []
    for path, count in agg.items():
        parts = path.split("/")
        zone = None
        if not (parts[0].startswith(".") and parts[0] != ".github"):
            for part in reversed(parts):
                low = part.lower()
                if low == "app" and routes_fw:
                    zone = "routes"
                    break
                zone = ZONE_NAMES.get(low)
                if zone:
                    break
            if zone != "jobs" and any(ZONE_NAMES.get(p.lower()) == "jobs" for p in parts):
                zone = "jobs"
        rows.append({
            "path": path,
            "files": count,
            "depth": len(parts),
            "zone": zone,
            "sample_files": sorted(state.dir_sample_files.get(path, []))[:6],
            "subdirs": (state.dir_subdirs.get(path) or [])[:8],
        })
    rows.sort(key=lambda row: (-row["files"], row["path"]))
    return rows[:limit]


def detect_tooling():
    """Binaries on PATH, by name only.  Environment evidence for phase 4's
    browser-driver and CLI choices; never repo evidence, never executed."""
    found = [name for name in TOOLING_PROBES if shutil.which(name)]
    return {
        "on_path": found,
        "note": "binaries found on this machine's PATH by name; environment evidence "
                "for choosing a browser driver or CLI in a generated skill, never repo "
                "evidence, and nothing was executed",
    }


def build_languages(state):
    total = sum(state.lang_loc.values())
    rows = []
    for name, files in state.lang_files.items():
        loc = state.lang_loc.get(name, 0)
        if files <= 0:
            continue
        rows.append({
            "name": name,
            "files": files,
            "loc": loc,
            "share": round(loc / float(total), 4) if total else 0.0,
        })
    rows.sort(key=lambda row: (-row["loc"], -row["files"], row["name"]))
    return rows, total


def read_ci(root, state, reader):
    out = []
    for rel in sorted(set(state.ci_paths))[:12]:
        full = os.path.join(root, rel.replace("/", os.sep))
        text = reader.text(full, 128 * 1024)
        runs = []
        env_hits = []
        for raw in text.splitlines()[:800]:
            match = CI_RUN_RE.match(raw)
            if match:
                cmd = _clean(match.group(1))[:120]
                if cmd and cmd not in runs:
                    runs.append(cmd)
            for name in CI_SECRET_RE.findall(raw):
                env_hits.append(name)
            if len(runs) >= 15:
                break
        out.append({"file": rel, "runs": runs})
        state.ci_env_names.extend(env_hits[:40])
    return out


def read_env_names(root, state, reader):
    names = []
    for rel, depth in sorted(state.env_paths)[:12]:
        if depth > 3:
            continue
        full = os.path.join(root, rel.replace("/", os.sep))
        names.extend(reader.env_var_names(full))
    names.extend(state.ci_env_names)

    unique = []
    seen = set()
    redacted = 0
    for name in names:
        if name in seen or not ENV_NAME_RE.match(name):
            continue
        seen.add(name)
        clean, hits = scrublib.scrub(name)
        if hits:
            redacted += 1
            continue
        unique.append(clean)
    if redacted:
        emitlib.warn(
            state.warnings,
            "%d env var name(s) looked like secret material and were dropped" % redacted,
        )
    unique.sort()
    return unique[:250]


#: A task runner is a LAYER ON TOP of a workspace system, never one itself:
#: turbo.json says how tasks run across packages, pnpm-workspace.yaml says what
#: the packages ARE.  Reporting turborepo in the same slot as pnpm is what let
#: `tool` and `workspaces` describe two different systems.
TASK_RUNNER_FILES = [
    ("turbo.json", "turborepo"), ("nx.json", "nx"), ("lerna.json", "lerna"),
    ("rush.json", "rush"), ("moon.yml", "moon"),
]

#: js workspaces carry no tool name in the manifest that declares them --
#: package.json and pnpm-workspace.yaml say THAT they exist, the lockfile says
#: who runs them.
JS_TOOL_BY_LOCKFILE = [
    ("bun.lock", "bun"), ("bun.lockb", "bun"), ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"), ("package-lock.json", "npm"),
]

#: stable ordering so `tool` (the back-compat single value) and `systems` do
#: not flip between runs: js first, then cargo, then go, then anything else
_SYSTEM_RANK = {"pnpm": 0, "bun": 0, "yarn": 0, "npm": 0,
                "cargo": 1, "go-work": 2}

_YAML_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\-]*|\"[^\"]+\"|'[^']+')\s*:(.*)$")


def _yaml_scalar(text):
    """One YAML scalar: quotes stripped, trailing comment dropped."""
    value = text.strip()
    if value[:1] in ("\"", "'"):
        quote = value[0]
        end = value.find(quote, 1)
        return value[1:end] if end > 0 else value[1:].strip()
    for marker in (" #", "\t#"):
        if marker in value:
            value = value.split(marker, 1)[0]
    value = value.strip()
    return "" if value.startswith("#") else value


def _yaml_flow_seq(text):
    """`["a", "b"]` -> `["a", "b"]`.  Bounded, and never a real YAML parser."""
    inner = text.strip().lstrip("[").split("]", 1)[0]
    return [item for item in
            (_yaml_scalar(part) for part in inner.split(",")[:MAX_WORKSPACE_GLOBS])
            if item]


def parse_pnpm_workspace(root, reader, warnings):
    """
    The list under the top-level `packages:` key of pnpm-workspace.yaml, and
    nothing else.

    The file is a full YAML document with sibling top-level keys, several of
    which are ALSO lists of package-ish strings (`minimumReleaseAgeExclude:`,
    `onlyBuiltDependencies:`, `neverBuiltDependencies:`).  Scanning the whole
    file for `- item` lines pulls those in as workspaces: on a real
    pnpm-workspace.yaml declaring 7 globs it reported 11, four of them npm
    package names that are not directories in this repo at all.

    So the key is tracked by indentation and only its block is read.  When the
    file's shape is not the common one, this warns and returns nothing rather
    than guessing -- an invented workspace list is worse than no workspace list,
    because phase 4 cannot tell the difference.
    """
    filename = None
    for candidate in ("pnpm-workspace.yaml", "pnpm-workspace.yml"):
        if os.path.exists(os.path.join(root, candidate)):
            filename = candidate
            break
    if filename is None:
        return None

    text = reader.text(os.path.join(root, filename), 32 * 1024)
    if not text:
        emitlib.warn(
            warnings,
            "%s is present but could not be read; its workspace globs were not "
            "parsed" % filename,
        )
        return None

    globs = []
    current = None
    saw_packages = False
    explicitly_empty = False
    odd_shape = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if stripped.startswith("- ") or stripped == "-":
            # A sequence entry belongs to the key that opened the block, at
            # whatever indent -- YAML allows it level with the key.
            if current == "packages":
                item = _yaml_scalar(stripped[1:])
                if item:
                    globs.append(item)
            continue
        if current == "packages" and indent > 0:
            # pnpm requires `packages:` to be a plain sequence.  Anything else
            # nested under it -- a mapping, an anchor -- is a file this parser
            # does not understand, and guessing a workspace list from it is
            # worse than admitting that.
            odd_shape = stripped[:40]
            current = None
            continue
        match = _YAML_KEY_RE.match(raw) if indent == 0 else None
        if match is not None:
            current = match.group(1).strip("\"'")
            if current == "packages":
                saw_packages = True
                inline = match.group(2).strip()
                if inline.startswith("["):
                    found = _yaml_flow_seq(inline)
                    globs.extend(found)
                    # `packages: []` is a deliberate, well-formed statement
                    # that this repo has no workspaces -- not a parse failure,
                    # and it must not be reported as one.
                    explicitly_empty = not found
                    current = None   # the block form cannot also follow
            continue
        if indent == 0:
            # top level, not a key and not a sequence entry: shape unknown
            current = None

    if not saw_packages:
        emitlib.warn(
            warnings,
            "%s has no top-level `packages:` key, so no workspace globs were "
            "taken from it; if this repo really is a pnpm workspace, say so "
            "and treat the root as the setup target" % filename,
        )
        return None
    if odd_shape:
        emitlib.warn(
            warnings,
            "%s nests something other than a list under `packages:` (%r); the "
            "file's shape is not one this parser understands, so no workspace "
            "globs were taken from it" % (filename, _printable(odd_shape)),
        )
        return None
    if not globs:
        if not explicitly_empty:
            emitlib.warn(
                warnings,
                "%s declares `packages:` but no list entries could be parsed "
                "from it (unusual YAML shape); no workspace globs were taken "
                "from it" % filename,
            )
        return None
    return build_workspace_system("pnpm", filename, globs)


def detect_monorepo(root, state, manifests, warnings):
    """
    A repo can run MORE THAN ONE workspace system at once, so this reports them
    all.  turborepo itself is the proof: pnpm-workspace.yaml over `apps/` and
    `packages/`, a cargo `[workspace]` over 64 crates, and turbo.json on top of
    both.  Collapsing that into one `tool` string produced `tool: "cargo"` next
    to a `workspaces` list parsed from the pnpm file -- two halves of the answer
    that contradicted each other.

    Schema (`monorepo`), stated plainly because it GREW here:
      is_monorepo   bool    unchanged
      tool          str     unchanged spelling, back-compat for single-value
                            consumers: the primary system, "+<runner>" appended
      workspaces    [str]   unchanged key, now the UNION of every system's
                            include globs with negations removed
      excludes      [str]   NEW: the negations, no longer inline in workspaces
      tools         [str]   NEW: every workspace system's tool, deduped
      systems       [obj]   NEW: {tool, manifest, workspaces, excludes} per
                            declaration -- globs stay with what declared them
      task_runners  [obj]   NEW: {name, file} for turbo.json / nx.json / ...
    """
    # pnpm-workspace.yaml was already parsed in `read_manifests`, with the
    # other root manifests, because the manifest-read cap needs its globs.
    systems = [dict(system) for system in manifests.workspace_systems]

    # Same precedence as `detect_package_managers`: what package.json DECLARES
    # beats a lockfile, and a lockfile only counts at the repo ROOT.  Reading
    # this name-only made vercel/turborepo -- a pnpm workspace -- report
    # `tool: "bun"`, on the strength of fixture lockfiles under
    # `lockfile-tests/fixtures/`.
    js_tool = declared_js_pm(manifests)[0]
    if not js_tool:
        for lockfile, name in JS_TOOL_BY_LOCKFILE:
            if lock_depth(state, lockfile) == 0:
                js_tool = name
                break
    for system in systems:
        if not system["tool"]:
            system["tool"] = js_tool or "npm"
    systems.sort(key=lambda s: _SYSTEM_RANK.get(s["tool"], 3))

    task_runners = []
    for filename, name in TASK_RUNNER_FILES:
        # marker_files is basenames at depth <= 2, so confirm it is the ROOT
        # file before calling the whole repo a turborepo.
        if filename in state.marker_files and os.path.exists(
                os.path.join(root, filename)):
            task_runners.append({"name": name, "file": filename})

    workspaces, excludes, tools = [], [], []
    for system in systems:
        for glob in system["workspaces"]:
            if glob not in workspaces:
                workspaces.append(glob)
        for glob in system["excludes"]:
            if glob not in excludes:
                excludes.append(glob)
        if system["tool"] and system["tool"] not in tools:
            tools.append(system["tool"])
    workspaces = workspaces[:MAX_WORKSPACE_GLOBS]
    excludes = excludes[:MAX_WORKSPACE_GLOBS]

    tool = tools[0] if tools else ""
    if task_runners:
        tool = (tool + "+" + task_runners[0]["name"]) if tool else task_runners[0]["name"]

    is_monorepo = bool(systems) or bool(task_runners)

    # Every warning below is computed AFTER detection finishes.  The old code
    # emitted the "no workspace globs were parsed" line from a helper that ran
    # before the pnpm file was read, so it fired on runs whose workspaces list
    # was populated -- a warning contradicting the payload it shipped with.
    if is_monorepo and not workspaces:
        emitlib.warn(
            warnings,
            "monorepo tooling detected (%s) but no workspace globs were "
            "parsed; treat the root as the setup target unless the user says "
            "otherwise" % (tool or "unknown"),
        )
    if len(systems) > 1:
        emitlib.warn(
            warnings,
            "%d workspace systems declared here (%s); monorepo.systems keeps "
            "each system's globs with the manifest that declared them and "
            "monorepo.workspaces is their union"
            % (len(systems),
               ", ".join("%s via %s" % (s["tool"], s["manifest"]) for s in systems)),
        )
    if manifests.nested_workspace_decls:
        emitlib.warn(
            warnings,
            "%d manifest(s) below the repo root declare workspace members of "
            "their own; only the root's declarations are reported here"
            % manifests.nested_workspace_decls,
        )

    return {
        "is_monorepo": bool(is_monorepo),
        "tool": tool or "",
        "workspaces": workspaces,
        "excludes": excludes,
        "tools": tools,
        "systems": systems,
        "task_runners": task_runners,
    }


# ---------------------------------------------------------------------------
# Existing agentic config
# ---------------------------------------------------------------------------

#: `AGENTS.override.md` outranks `AGENTS.md` at the same directory level on
#: Codex (verified 2026-09-05, codex-cli 0.152.1: discovery checks
#: `AGENTS.override.md` -> `AGENTS.md` -> `project_doc_fallback_filenames`, at
#: most one file per directory).  A repo that has one and is not told about it
#: gets an agentify section appended to a file Codex never reads.
INDEX_DOC_PATHS = ["CLAUDE.md", "AGENTS.md", "AGENTS.override.md", "CODEX.md",
                   ".cursorrules",
                   ".github/copilot-instructions.md", ".claude/CLAUDE.md"]

#: `.claude/skills/<name>/` counts as a skill only when it holds this file.
#: A directory there without one (docs, a scratch folder) is reported in
#: `warnings` rather than silently counted or silently dropped.
SKILL_ENTRYPOINT = "SKILL.MD"

# --- provenance: the team's own artifacts vs vendored third-party ones ------
#
# Measured failure this exists to fix: a real repo reported 17 skills, tripped
# the `>= 5` maturity threshold, and under the retired audit-only mode dropped to caps of
# 2/1/3/2 -- and all 17 were third-party library guides installed by
# `skills-lock.json` (Better Auth x5, Dodo Payments x7, AI SDK x2,
# agent-browser, create-auth).  The team had effectively no setup of its own
# and agentify refused to build one.  Vendored documentation is not evidence
# that a team has an agentic setup; it IS something a new artifact must be
# de-duplicated against, so it stays in `skills`/`agents`/`counts` and is
# excluded only from the maturity calculation.

#: Lockfiles / manifests that INSTALL third-party skills into this repo.  A
#: name listed here was fetched from somewhere else.
SKILLS_LOCK_PATHS = (
    "skills-lock.json", "skills.lock.json", "agent-skills.lock.json",
    ".claude/skills-lock.json", ".claude/skills.lock.json",
    ".agents/skills-lock.json", ".codex/skills-lock.json",
)

#: A path segment that means "this came from somewhere else".  Checked against
#: the RESOLVED target of an artifact, so a skill symlinked into a plugin
#: cache is recognised wherever the link starts.
#:
#: `.agents/` is deliberately NOT here.  A shared team store is the team's own
#: work: one measured repo keeps 27 hand-written skills symlinked out of
#: exactly that directory, and treating the layout as vendoring would erase
#: them.  The lockfile, not the link, is what says "third party".
VENDOR_PATH_SEGMENTS = frozenset([
    "node_modules", "bower_components", "jspm_packages",
    "vendor", "vendored", "third_party", "third-party", "3rdparty",
    "site-packages", "caches",
])
VENDOR_PATH_SUBSTRINGS = (
    "/plugins/cache/", "/plugins/marketplaces/", "/.claude/plugins/",
    "/library/caches/",
)

#: Frontmatter keys that name where an artifact came from.  A value that looks
#: external (a URL, `owner/repo`, `github:`) makes it vendored outright.
EXTERNAL_SOURCE_KEYS = frozenset([
    "source", "upstream", "origin", "vendor", "vendored_from", "vendored-from",
    "marketplace", "plugin", "installed_from", "installed-from",
])
#: Same idea, weaker: a team's own skill legitimately carries `repository` or
#: `author`, so an external-looking value here only marks the artifact
#: AMBIGUOUS -- which still counts toward maturity.
WEAK_SOURCE_KEYS = frozenset(["repository", "repo", "homepage", "author"])

#: Bounds on the provenance pass.  It opens artifact files, so it is capped
#: like every other read in this script.
MAX_PROVENANCE_READS = 200
PROVENANCE_READ_BYTES = 4096

#: Package-name tokens that identify nothing, so they never justify calling an
#: artifact third-party documentation.
_PKG_STOPWORD_TOKENS = frozenset([
    "latest", "beta", "alpha", "canary", "next", "cli", "core", "dev",
    "global", "install", "app", "js", "node", "npm", "run", "src",
])

#: Codex keeps its MCP servers in TOML.  `tomllib` is 3.11+ and this script
#: targets 3.9, and a dependency is forbidden, so `parse_codex_mcp_servers`
#: hand-rolls a bounded scan.
CODEX_CONFIG_RELS = (".codex/config.toml", ".codex/config.local.toml")
MAX_TOML_LINES = 4000

_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]{0,40})\s*:\s*(.*)$")
_EXTERNAL_VALUE_RE = re.compile(
    r"https?://|git@|github:|npm:|gh:"
    r"|^[A-Za-z0-9][A-Za-z0-9_.-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,38}$"
)
_INSTALL_CMD_RE = re.compile(
    r"\b(?:npm|pnpm|yarn|bun)\s+(?:install|add|i)\b(?:\s+-{1,2}[A-Za-z-]{1,20})*"
    r"\s+([@A-Za-z0-9][@A-Za-z0-9_./-]{1,60})"
    r"|\b(?:npx|bunx|dlx)\s+([@A-Za-z0-9][@A-Za-z0-9_./-]{1,60})"
    r"|\bpip\s+install\s+([A-Za-z0-9][A-Za-z0-9_.-]{1,60})"
    r"|\bgo\s+get\s+([A-Za-z0-9][A-Za-z0-9_./-]{1,60})"
    r"|\bcargo\s+add\s+([A-Za-z0-9][A-Za-z0-9_-]{1,60})"
)
_TOML_MCP_SUBTABLE_RE = re.compile(
    r"^\[\s*mcp_servers\s*\.\s*(\"[^\"]{1,80}\"|[A-Za-z0-9_.\-]{1,80})\s*\]$")
_TOML_MCP_TABLE_RE = re.compile(r"^\[\s*mcp_servers\s*\]$")
_TOML_ANY_HEADER_RE = re.compile(r"^\[{1,2}[^\[\]]{0,200}\]{1,2}$")
_TOML_ASSIGN_RE = re.compile(r"^(\"[^\"]{1,80}\"|[A-Za-z0-9_\-]{1,80})\s*=")
_TOML_STRING_RE = re.compile(r"\"\"\"|'''|\"[^\"]*\"|'[^']*'")


def parse_codex_mcp_servers(text):
    """
    MCP server names out of a Codex `config.toml`, without a TOML parser.

    `tomllib` is 3.11+ and this script targets 3.9, and adding a dependency is
    forbidden, so this is a bounded section-header scan and nothing more: it
    reads `[mcp_servers.<name>]` subtable headers, and top-level assignments
    directly under a bare `[mcp_servers]` table.  Quoted strings are removed
    before brackets are counted, so a multi-line `args = [ ... ]` array is
    never mistaken for a section header and a `[` inside a command string
    cannot unbalance the scan.

    Returns `(names, ok)`.  `ok` is False when the file mentions `mcp_servers`
    yet the scan found none, when brackets never closed, or when the file was
    longer than the line cap -- the caller warns rather than reporting a
    confident empty list.
    """
    names = []
    depth = 0
    in_mcp_root = False
    saw_token = "mcp_servers" in text
    truncated = False

    for index, raw in enumerate(text.splitlines()):
        if index >= MAX_TOML_LINES:
            truncated = True
            break
        line = _TOML_STRING_RE.sub("", raw)
        hash_at = line.find("#")
        if hash_at >= 0:
            line = line[:hash_at]
        line = line.strip()
        if not line:
            continue
        if depth == 0:
            match = _TOML_MCP_SUBTABLE_RE.match(line)
            if match:
                name = match.group(1).strip('"').split(".")[0].strip()
                if name:
                    names.append(name)
                in_mcp_root = False
            elif _TOML_MCP_TABLE_RE.match(line):
                in_mcp_root = True
            elif _TOML_ANY_HEADER_RE.match(line):
                in_mcp_root = False
            elif in_mcp_root:
                assign = _TOML_ASSIGN_RE.match(line)
                if assign:
                    name = assign.group(1).strip('"').split(".")[0].strip()
                    if name:
                        names.append(name)
        depth += (line.count("[") + line.count("{")
                  - line.count("]") - line.count("}"))
        if depth < 0:
            depth = 0
        if len(names) >= 80:
            break

    ok = not truncated and depth == 0 and not (saw_token and not names)
    return (names, ok)


# ---------------------------------------------------------------------------
# Codex target discovery
# ---------------------------------------------------------------------------
#
# Verified 2026-09-05 against codex-cli 0.152.1 (`/Applications/ChatGPT.app/
# Contents/Resources/codex`) and a real `~/.codex`.  Every path below was seen
# on disk or in the binary; the ones that were not are marked UNVERIFIED in the
# warning text they produce, never asserted.
#
#   repo scope      `<repo>/AGENTS.md`, `AGENTS.override.md`  index doc
#                   `<repo>/.agents/skills/<name>/SKILL.md`   skills  (NOT
#                                                             `.codex/skills`)
#                   `<repo>/.codex/agents/<name>.toml`        subagents
#                   `<repo>/.codex/rules/<name>.rules`        command policy
#                   `<repo>/.codex/hooks.json` + `.codex/hooks/`   hooks
#                   `<repo>/.codex/config.toml`               MCP + features
#                   `<repo>/.codex-plugin/plugin.json`        plugin manifest
#   user scope      `${CODEX_HOME:-~/.codex}/{skills,rules,agents}`,
#                   `hooks.json`, `plugins/cache/<market>/<plugin>/`,
#                   `config.toml`, plus `~/.agents/skills`
#
# Two rules govern everything here:
#
#   1. NEVER read a value out of `config.toml` that is not on the allowlist in
#      `parse_codex_config_facts`.  The real file on the verification machine
#      holds a live bearer token.  Section headers and three boolean/enum keys
#      are all this script is allowed to see, and `--selftest` proves it.
#   2. User-scope artifacts are reported for DE-DUPLICATION, never summed into
#      this repo's maturity.  A developer with 9 global skills does not have a
#      mature setup *for this repo*, and agentify builds repo-scoped files.

#: `${CODEX_HOME}` when set and non-empty, else `~/.codex`.
def codex_home_dir():
    value = (os.environ.get("CODEX_HOME") or "").strip()
    if value:
        return os.path.expanduser(value)
    return os.path.expanduser(os.path.join("~", ".codex"))


#: `${CLAUDE_CONFIG_DIR}` when set, else `~/.claude`.  Listed for exactly one
#: reason: a skill that exists in BOTH user trees is one artifact wearing two
#: names (53 of the 62 entries in the verification machine's `~/.codex/skills`
#: are symlinks into a repo's `.claude/skills`), and counting it twice would
#: overstate the setup and propose a de-duplication target that does not exist.
def claude_home_dir():
    value = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip()
    if value:
        return os.path.expanduser(value)
    return os.path.expanduser(os.path.join("~", ".claude"))


#: Repo-scoped Codex artifact homes, and what each one is.  `.codex/skills` is
#: deliberately absent: it is NOT a Codex skills root (the roots table Codex
#: 0.152.1 wrote into a live session lists `$CODEX_HOME/skills`,
#: `$HOME/.agents/skills`, `$CODEX_HOME/skills/.system` and the plugin caches;
#: the docs' repo row is `.agents/skills`).  A directory found there is still
#: counted as an existing artifact for de-duplication and warned about.
CODEX_REPO_SKILL_DIR = ".agents/skills"
CODEX_REPO_AGENT_DIR = ".codex/agents"
CODEX_REPO_RULES_DIR = ".codex/rules"
CODEX_HOOKS_RELS = (".codex/hooks.json", ".codex/hooks/hooks.json")
PLUGIN_MANIFEST_RELS = (
    (".claude-plugin/plugin.json", "claude-code"),
    (".codex-plugin/plugin.json", "codex"),
)

#: Bounds on the user-scope pass.  It runs outside the repo, so every one of
#: these is a refusal rather than a best effort.
CODEX_USER_MAX_SKILLS = 300
CODEX_USER_MAX_OTHER = 80
CODEX_USER_MAX_PLUGINS = 60

#: `config.toml` value allowlist.  A key not matched by one of these regexes is
#: never read, so no credential can reach stdout by any path.
_TOML_PROJECT_HEADER_RE = re.compile(
    r"^\[\s*projects\s*\.\s*\"([^\"]{1,400})\"\s*\]$")
_TOML_PLUGIN_HEADER_RE = re.compile(
    r"^\[\s*plugins\s*\.\s*\"([^\"]{1,120})\"\s*\]$")
_TOML_MARKETPLACE_HEADER_RE = re.compile(
    r"^\[\s*marketplaces\s*\.\s*(\"[^\"]{1,120}\"|[A-Za-z0-9_.\-]{1,120})\s*\]$")
_TOML_FEATURES_HEADER_RE = re.compile(r"^\[\s*features\s*\]$")
_TOML_HOOKS_HEADER_RE = re.compile(
    r"^\[{1,2}\s*hooks(\s*\.[^\[\]]{0,120})?\s*\]{1,2}$")
_TOML_TRUST_LEVEL_RE = re.compile(
    r"^trust_level\s*=\s*\"?(trusted|untrusted|verified)\"?\s*(?:#.*)?$")
_TOML_BOOL_FEATURE_RE = re.compile(
    r"^(hooks|multi_agent|plugins|memories)\s*=\s*(true|false)\s*(?:#.*)?$")
_TOML_FALLBACK_NAMES_RE = re.compile(
    r"^project_doc_fallback_filenames\s*=\s*\[(.{0,200})\]\s*(?:#.*)?$")


def parse_codex_config_facts(text, repo_root=""):
    """
    The handful of facts agentify needs out of a Codex `config.toml`, read
    under a strict allowlist.

    Returns a dict with `features`, `has_hooks_table`, `plugins`,
    `marketplaces`, `projects_declared`, `repo_trust_level`,
    `claude_md_fallback` and `lines_capped`.

    **Only** these are ever read out of the file:

      * section headers -- `[projects."<path>"]`, `[plugins."x@y"]`,
        `[marketplaces.<n>]`, `[features]`, `[hooks...]`;
      * `trust_level = "trusted"|"untrusted"|"verified"`;
      * `hooks|multi_agent|plugins|memories = true|false` inside `[features]`;
      * `project_doc_fallback_filenames = [ ... ]`, scanned for the literal
        `CLAUDE.md` and reduced to a boolean.

    Every other line is discarded before it can be stored, so a `bearer_token`,
    an `Authorization` header or an `env` table cannot reach the output no
    matter what the file contains.  `--selftest` asserts exactly that against a
    file built to look like the real one.
    """
    facts = {
        "features": {},
        "has_hooks_table": False,
        "plugins": [],
        "marketplaces": [],
        "projects_declared": 0,
        "repo_trust_level": "",
        "claude_md_fallback": False,
        "lines_capped": False,
    }
    if not text:
        return facts
    try:
        want_root = os.path.realpath(repo_root) if repo_root else ""
    except (IOError, OSError):
        want_root = repo_root or ""

    section = ""
    project_path = ""
    lines = text.splitlines()
    if len(lines) > MAX_TOML_LINES:
        lines = lines[:MAX_TOML_LINES]
        facts["lines_capped"] = True

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            project_path = ""
            match = _TOML_PROJECT_HEADER_RE.match(line)
            if match:
                section = "projects"
                facts["projects_declared"] += 1
                project_path = match.group(1)
                continue
            match = _TOML_PLUGIN_HEADER_RE.match(line)
            if match:
                section = "other"
                if len(facts["plugins"]) < CODEX_USER_MAX_PLUGINS:
                    facts["plugins"].append(match.group(1))
                continue
            match = _TOML_MARKETPLACE_HEADER_RE.match(line)
            if match:
                section = "other"
                name = match.group(1).strip('"')
                if len(facts["marketplaces"]) < CODEX_USER_MAX_PLUGINS:
                    facts["marketplaces"].append(name)
                continue
            if _TOML_FEATURES_HEADER_RE.match(line):
                section = "features"
                continue
            if _TOML_HOOKS_HEADER_RE.match(line):
                facts["has_hooks_table"] = True
                section = "other"
                continue
            section = "other"
            continue

        # Not a header.  Three allowlisted assignments, nothing else.
        if section == "projects" and project_path:
            match = _TOML_TRUST_LEVEL_RE.match(line)
            if match and want_root:
                try:
                    same = os.path.realpath(
                        os.path.expanduser(project_path)) == want_root
                except (IOError, OSError):
                    same = False
                if same:
                    facts["repo_trust_level"] = match.group(1)
            continue
        if section == "features":
            match = _TOML_BOOL_FEATURE_RE.match(line)
            if match:
                facts["features"][match.group(1)] = (match.group(2) == "true")
            continue
        if section == "" or section == "other":
            match = _TOML_FALLBACK_NAMES_RE.match(line)
            if match and "CLAUDE.md" in match.group(1):
                facts["claude_md_fallback"] = True
            continue

    return facts


def parse_hook_block(block, limit_events=24, limit_entries=20, limit_hooks=10):
    """
    `["<event>:<matcher>:<command>", ...]` out of a hooks mapping.

    Codex's `hooks.json` and Claude Code's `settings.json` `hooks` block are
    the SAME three-level shape -- event name, matcher group, handler list --
    confirmed against `~/.codex/hooks.json`, a repo-scoped `.codex/hooks.json`
    in production use, and a plugin `hooks/hooks.json` written once and read by
    both tools.  So one reader serves both.

    Codex adds a second handler type, `"type": "mcp_tool"`, which has no
    `command`; it is recorded by server and tool name instead of dropped.
    Commands run through `_clean`, so a token pasted into a hook command line
    is scrubbed before it can reach stdout.
    """
    out = []
    if not isinstance(block, dict):
        return out
    for event in list(block)[:limit_events]:
        entries = block.get(event)
        if not isinstance(entries, list):
            continue
        event_name = _clean(str(event))[:40]
        for entry in entries[:limit_entries]:
            if not isinstance(entry, dict):
                continue
            matcher = _clean(str(entry.get("matcher", "") or "*"))[:40]
            inner = entry.get("hooks")
            if not isinstance(inner, list) or not inner:
                out.append("%s:%s" % (event_name, matcher))
                continue
            for hook in inner[:limit_hooks]:
                if not isinstance(hook, dict):
                    continue
                kind = str(hook.get("type", "command"))
                if kind == "mcp_tool":
                    label = "mcp_tool %s.%s" % (
                        _clean(str(hook.get("server", "?")))[:30],
                        _clean(str(hook.get("tool", "?")))[:30])
                else:
                    label = _clean(str(hook.get("command", "")))[:80]
                out.append("%s:%s:%s" % (event_name, matcher, label))
    return out


def _codex_skill_dirs(base, max_entries):
    """
    `([(name, entry path, resolved dir), ...], [orphan name, ...], capped)`
    for a skills root.

    A directory counts only when it holds a `SKILL.md` -- the same entrypoint
    rule the repo-scoped scan uses.  Names beginning with `.` are skipped, which
    is how `$CODEX_HOME/skills/.system` (OpenAI's own bundled skills, marked by
    `.codex-system-skills.marker`) stays out of the count: they ship with the
    product and are not the user's setup.  Symlinks are followed and the
    RESOLVED directory is returned, because that is the identity two trees are
    de-duplicated on.
    """
    found = []
    orphans = []
    capped = False
    try:
        names = sorted(os.listdir(base))
    except (IOError, OSError):
        return (found, orphans, capped)
    if len(names) > max_entries:
        names = names[:max_entries]
        capped = True
    for name in names:
        if name.startswith(".") or name in ("Thumbs.db",):
            continue
        full = os.path.join(base, name)
        try:
            if not os.path.isdir(full):
                continue
        except (IOError, OSError):
            continue
        entry = ""
        for candidate in ("SKILL.md", "skill.md", "SKILL.MD"):
            probe = os.path.join(full, candidate)
            try:
                if os.path.isfile(probe):
                    entry = probe
                    break
            except (IOError, OSError):
                continue
        if not entry:
            orphans.append(name)
            continue
        try:
            resolved = os.path.realpath(full)
        except (IOError, OSError):
            resolved = full
        found.append((name, entry, resolved))
    return (found, orphans, capped)


def _codex_list_files(base, suffixes, max_entries):
    """`[(name, full path)]` for files in `base` ending in one of `suffixes`."""
    out = []
    try:
        names = sorted(os.listdir(base))
    except (IOError, OSError):
        return out
    for name in names[:max_entries]:
        if name.startswith("."):
            continue
        if not name.lower().endswith(tuple(suffixes)):
            continue
        full = os.path.join(base, name)
        try:
            if os.path.isfile(full):
                out.append((name, full))
        except (IOError, OSError):
            continue
    return out


#: Directory names that are an artifact ROOT rather than one artifact's own
#: folder, so `.claude/skills/deploy/SKILL.md` reports `.claude/skills` and not
#: a different path for every skill.
_ARTIFACT_ROOT_NAMES = frozenset([
    "skills", "agents", "rules", "hooks", "commands", "prompts",
])


def _artifact_home(path):
    """The directory an artifact lives under, collapsed to its root."""
    if not path:
        return ""
    home = path.rsplit("/", 1)[0] if "/" in path else path
    if "/" in home:
        parent = home.rsplit("/", 1)[0]
        if parent.rsplit("/", 1)[-1] in _ARTIFACT_ROOT_NAMES:
            return parent
    return home


def _group_artifact_rows(rows):
    """
    `artifacts_by_target` in its emitted form: one entry per
    `(target, kind)` pair rather than one per file.

    A repo can carry config for both agents at once, so "which target loads
    this?" has to be answerable per artifact.  The per-file form that answers
    it costs ~130 characters an artifact, which on a 60-skill repo crowded
    `folders` and `env_var_names` out of the output cap.  The grouped form
    answers the same question -- look the name up in the groups -- at about a
    quarter of the size.

    Targets: `claude-code`, `codex`, `shared` (`.agents/skills/`: loaded
    natively by Codex, and commonly symlinked into `.claude/skills/`), `cursor`,
    `copilot`, `git` (`.git/hooks` and `.husky` run for every agent and for the
    human, so they belong to no agent).
    """
    # Codex first, deliberately.  The emitter trims list TAILS round-robin
    # when the output exceeds its cap, and `.claude/...` groups are trivially
    # inferable from the paths already in `skills`/`agents`/`rules` -- the
    # Codex and `shared` groups are the only ones carrying information nothing
    # else in the payload carries, so they must survive a trim.
    order = ["codex", "shared", "claude-code", "cursor", "copilot", "git"]
    kinds = ["skills", "agents", "rules", "hooks", "plugin"]
    grouped = {}
    for row in rows:
        key = (row.get("target", ""), row.get("kind", ""))
        entry = grouped.setdefault(key, {"names": [], "paths": []})
        name = str(row.get("name", ""))[:60]
        if name and name not in entry["names"] and len(entry["names"]) < 40:
            entry["names"].append(name)
        home = _artifact_home(str(row.get("file", "")))
        if home and home not in entry["paths"] and len(entry["paths"]) < 6:
            entry["paths"].append(home)
    out = []
    for target in order + sorted(set(t for t, _k in grouped) - set(order)):
        for kind in kinds + sorted(set(k for t, k in grouped
                                       if t == target) - set(kinds)):
            entry = grouped.get((target, kind))
            if not entry:
                continue
            total = sum(1 for row in rows
                        if row.get("target") == target and row.get("kind") == kind)
            out.append({
                "target": target,
                "kind": kind,
                "count": total,
                "names": entry["names"],
                "paths": entry["paths"],
            })
    return out


def scan_codex_user_scope(repo_root, reader, warnings):
    """
    Codex's USER-scope config: `${CODEX_HOME:-~/.codex}` plus `~/.agents/skills`.

    Why this exists.  Everything agentify builds is repo-scoped, but Codex
    loads user-scope skills, rules, hooks and plugins into every session in
    this repo too.  Without this pass, phase 4 proposes a skill the user has
    had installed globally for months (anti-pattern A9 cannot de-duplicate
    against something it cannot see), and phase 6 promises a hook that a global
    `hooks.json` already covers.

    What it does NOT do: feed `maturity`.  A global setup is not this repo's
    setup, and folding 62 global entries into the `>= 5` threshold would drop
    every run into the retired audit-only mode.  The counts are reported, with the own /
    vendored split, so the model can raise it in the interview instead.

    Cross-target de-duplication is by RESOLVED path.  On the verification
    machine 53 of 62 `~/.codex/skills` entries are symlinks into one repo's
    `.claude/skills`, and three skills are byte-identical in both trees --
    Codex ships an external-agent config importer, so a Codex install can be a
    copy of the Claude Code one.  Counting those twice would invent a setup
    that does not exist.

    Never raises.  A missing `~/.codex` returns `scanned: False` and nothing
    else, which is the common case and not a warning.
    """
    home = codex_home_dir()
    block = {
        "codex_home": "",
        "scanned": False,
        "skills": [],
        "skills_shared_with_claude_code": [],
        "agents": [],
        "rules": [],
        "hooks": [],
        "plugins": [],
        "mcp_servers": [],
        "counts": {"skills": 0, "agents": 0, "rules": 0, "hooks": 0,
                   "plugins": 0},
        "own": {"skills": 0},
        "vendored": {"skills": 0},
        "notes": [],
    }
    try:
        exists = os.path.isdir(home)
    except (IOError, OSError):
        exists = False
    agents_skills = os.path.expanduser(os.path.join("~", ".agents", "skills"))
    try:
        alt_exists = os.path.isdir(agents_skills)
    except (IOError, OSError):
        alt_exists = False
    if not exists and not alt_exists:
        return block

    block["scanned"] = True
    if exists:
        block["codex_home"] = scrublib.collapse_home_paths(home)[0]
    else:
        # `${CODEX_HOME}` is absent but `~/.agents/skills` is not.  Say which
        # root was actually read rather than naming a directory that does not
        # exist -- the plan quotes this path back to the user.
        block["codex_home"] = scrublib.collapse_home_paths(agents_skills)[0]
        block["notes"].append(
            "no %s directory; only ~/.agents/skills was read"
            % scrublib.collapse_home_paths(home)[0])

    # -- skills, across both user roots, de-duplicated by resolved path ----
    seen_resolved = {}
    orphan_names = []
    for base, label in ((os.path.join(home, "skills"), "$CODEX_HOME/skills"),
                        (agents_skills, "~/.agents/skills")):
        try:
            if not os.path.isdir(base):
                continue
        except (IOError, OSError):
            continue
        found, orphans, capped = _codex_skill_dirs(base, CODEX_USER_MAX_SKILLS)
        orphan_names.extend(orphans)
        if capped:
            block["notes"].append(
                "%s holds more than %d entries; the list is a floor"
                % (label, CODEX_USER_MAX_SKILLS))
        for name, _entry, resolved in found:
            if resolved in seen_resolved:
                continue
            seen_resolved[resolved] = name

    # Claude Code's user tree, listed for identity comparison only.
    claude_resolved = {}
    claude_skills = os.path.join(claude_home_dir(), "skills")
    try:
        if os.path.isdir(claude_skills):
            found, _orphans, _capped = _codex_skill_dirs(
                claude_skills, CODEX_USER_MAX_SKILLS)
            for name, _entry, resolved in found:
                claude_resolved[resolved] = name
    except (IOError, OSError):
        pass

    shared = []
    for resolved in sorted(seen_resolved):
        name = seen_resolved[resolved]
        block["skills"].append(name)
        if resolved in claude_resolved:
            shared.append(name)
        if _is_vendor_path(resolved):
            block["vendored"]["skills"] += 1
        else:
            block["own"]["skills"] += 1
    block["skills"] = sorted(set(block["skills"]))[:CODEX_USER_MAX_SKILLS]
    block["skills_shared_with_claude_code"] = sorted(set(shared))[:CODEX_USER_MAX_SKILLS]

    if orphan_names:
        block["notes"].append(
            "%d user-scope director%s hold no SKILL.md and were not counted "
            "(%s)" % (len(orphan_names),
                      "y" if len(orphan_names) == 1 else "ies",
                      ", ".join(sorted(set(orphan_names))[:6])))

    # -- rules: `.rules`, a Starlark command-approval policy, not prose ----
    for name, _full in _codex_list_files(os.path.join(home, "rules"),
                                         (".rules",), CODEX_USER_MAX_OTHER):
        block["rules"].append(name)

    # -- subagents.  `.codex/agents` is a literal in the 0.152.1 binary and
    #    the documented project path; whether the USER-scope directory is read
    #    is UNVERIFIED (it was absent on the verification machine), so this is
    #    reported for de-duplication and never asserted as loaded.
    for name, _full in _codex_list_files(os.path.join(home, "agents"),
                                         (".toml",), CODEX_USER_MAX_OTHER):
        block["agents"].append(name[:-5])
    if block["agents"]:
        block["notes"].append(
            "whether Codex loads user-scope ~/.codex/agents/*.toml is "
            "UNVERIFIED (the documented path is <repo>/.codex/agents/); the "
            "names are listed so nothing proposes a duplicate")

    # -- hooks ------------------------------------------------------------
    hooks_json = os.path.join(home, "hooks.json")
    try:
        has_hooks_json = os.path.isfile(hooks_json)
    except (IOError, OSError):
        has_hooks_json = False
    if has_hooks_json:
        data = reader.json(hooks_json)
        if isinstance(data, dict):
            inner = data.get("hooks") if isinstance(data.get("hooks"), dict) else data
            block["hooks"].extend(parse_hook_block(inner))

    # -- plugins: `<home>/plugins/cache/<marketplace>/<plugin>/` -----------
    cache = os.path.join(home, "plugins", "cache")
    try:
        markets = sorted(os.listdir(cache))[:CODEX_USER_MAX_PLUGINS]
    except (IOError, OSError):
        markets = []
    for market in markets:
        if market.startswith("."):
            continue
        market_dir = os.path.join(cache, market)
        try:
            if not os.path.isdir(market_dir):
                continue
            plugins = sorted(os.listdir(market_dir))[:CODEX_USER_MAX_PLUGINS]
        except (IOError, OSError):
            continue
        for plugin in plugins:
            if plugin.startswith("."):
                continue
            if len(block["plugins"]) >= CODEX_USER_MAX_PLUGINS:
                break
            block["plugins"].append("%s@%s" % (plugin, market))

    # -- config.toml: section headers and the three allowlisted keys ------
    config_path = os.path.join(home, "config.toml")
    try:
        has_config = os.path.isfile(config_path)
    except (IOError, OSError):
        has_config = False
    if has_config:
        text = reader.text(config_path)
        if text:
            names, parsed_ok = parse_codex_mcp_servers(text)
            block["mcp_servers"] = sorted(set(_clean(str(n))[:80]
                                              for n in names if str(n).strip()))[:40]
            if not parsed_ok:
                block["notes"].append(
                    "the user-scope config.toml mentions mcp_servers but the "
                    "bounded scan could not read all of it; the list is a floor")
            facts = parse_codex_config_facts(text, repo_root)
            if facts["has_hooks_table"]:
                block["hooks"].append("config.toml:[hooks]")
            for plugin in facts["plugins"]:
                if plugin not in block["plugins"] and len(block["plugins"]) < CODEX_USER_MAX_PLUGINS:
                    block["plugins"].append(plugin)
            if facts["repo_trust_level"]:
                block["notes"].append(
                    "this repo is declared trust_level=%s in the user-scope "
                    "config.toml" % facts["repo_trust_level"])
            block["_facts"] = facts

    block["hooks"] = sorted(set(block["hooks"]))[:CODEX_USER_MAX_OTHER]
    block["rules"] = sorted(set(block["rules"]))[:CODEX_USER_MAX_OTHER]
    block["agents"] = sorted(set(block["agents"]))[:CODEX_USER_MAX_OTHER]
    block["plugins"] = sorted(set(block["plugins"]))[:CODEX_USER_MAX_PLUGINS]
    block["counts"] = {
        "skills": len(block["skills"]),
        "agents": len(block["agents"]),
        "rules": len(block["rules"]),
        "hooks": len(block["hooks"]),
        "plugins": len(block["plugins"]),
    }

    total = (block["counts"]["skills"] + block["counts"]["agents"]
             + block["counts"]["rules"] + block["counts"]["hooks"])
    if total:
        emitlib.warn(
            warnings,
            "Codex user scope (%s) already has %d skill(s), %d subagent(s), "
            "%d rules file(s), %d hook entr%s, %d plugin(s) and %d MCP "
            "server(s); these load in EVERY session on this machine and in no "
            "one else's clone, so they are NOT this repo's setup: not counted "
            "toward maturity and NOT coverage for any candidate (blueprint.md "
            "2.1) -- a same-name collision with a generated artifact is one "
            "report line, never a skip"
            % (block["codex_home"], block["counts"]["skills"],
               block["counts"]["agents"], block["counts"]["rules"],
               block["counts"]["hooks"],
               "y" if block["counts"]["hooks"] == 1 else "ies",
               block["counts"]["plugins"], len(block["mcp_servers"])),
        )
    if block["skills_shared_with_claude_code"]:
        emitlib.warn(
            warnings,
            "%d user-scope skill(s) resolve to the SAME files in both the "
            "Claude Code and Codex trees (%s); they are one artifact under two "
            "names -- count them once and never write a copy into the other "
            "tree" % (len(block["skills_shared_with_claude_code"]),
                      ", ".join(block["skills_shared_with_claude_code"][:5])),
        )
    return block


def read_skills_lock(root, reader, warnings):
    """
    `({skill name: source label}, [lockfile path, ...])` for every skill a
    lockfile installed into this repo.

    Tolerant of shape: `{"skills": {name: {...}}}`, `{"skills": [{...}]}`, and
    a bare list of names all parse.  An unparseable lockfile is reported and
    its skills stay classified as the team's own -- the conservative direction.
    """
    vendored = {}
    files = []
    for rel in SKILLS_LOCK_PATHS:
        full = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.exists(full):
            continue
        data = reader.json(full)
        if data is None:
            emitlib.warn(
                warnings,
                "%s could not be parsed; the skills it installs are counted as "
                "the team's own, so maturity may be overstated" % rel,
            )
            continue
        block = data.get("skills") if isinstance(data, dict) else data
        if block is None and isinstance(data, dict):
            block = data
        entries = []
        if isinstance(block, dict):
            entries = list(block.items())
        elif isinstance(block, list):
            for item in block:
                if isinstance(item, dict):
                    label = item.get("name") or item.get("skill") or item.get("id")
                    if label:
                        entries.append((label, item))
                elif isinstance(item, str):
                    entries.append((item, {}))
        found = 0
        for label, meta in entries[:400]:
            name = _clean(str(label))[:80]
            if not name or name in ("version", "schema", "lockfileVersion"):
                continue
            source = ""
            if isinstance(meta, dict):
                for key in ("source", "repository", "repo", "from", "url", "origin"):
                    if meta.get(key):
                        source = _clean(str(meta[key]))[:100]
                        break
            vendored[name] = source or rel
            found += 1
        if found:
            files.append(rel)
    return (vendored, files)


def _is_vendor_path(path):
    """True when a path runs through a vendor, plugin-cache or package store."""
    lowered = path.replace(os.sep, "/").lower()
    for needle in VENDOR_PATH_SUBSTRINGS:
        if needle in lowered:
            return True
    for segment in lowered.split("/"):
        if segment in VENDOR_PATH_SEGMENTS:
            return True
    return False


def _frontmatter_map(text, limit=40):
    """
    Top-level `key: value` pairs from a leading `---` block.  Hand-rolled and
    deliberately minimal -- pyyaml is not available and is not wanted.
    """
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for raw in lines[1:200]:
        if raw.strip() in ("---", "..."):
            break
        if not raw.strip() or raw[:1] in (" ", "\t", "-"):
            continue
        match = _FRONTMATTER_KEY_RE.match(raw.rstrip())
        if match:
            out[match.group(1).strip().lower()] = match.group(2).strip().strip("\"'")
        if len(out) >= limit:
            break
    return out


def _external_source_value(front, keys):
    """`"<key>: <value>"` for the first key in `keys` whose value looks external."""
    for key in sorted(front):
        if key not in keys:
            continue
        value = front[key]
        if value and _EXTERNAL_VALUE_RE.search(value):
            return "%s: %s" % (key, _clean(value)[:80])
    return ""


def _tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", str(text).lower()) if t]


def _third_party_doc_hint(name, text):
    """
    Weak signal: this artifact reads as documentation for a third-party
    library rather than for this repo.

    Deliberately NOT enough on its own to call something vendored -- it marks
    the artifact AMBIGUOUS, which still counts toward maturity.  The rule is
    two-part on purpose: the body installs an external package, AND the
    artifact's own name names that package.  A skill that merely mentions
    `npm install` while documenting this repo fails the second half.
    """
    name_tokens = [t for t in _tokens(name) if len(t) >= 4]
    if not name_tokens:
        return ""
    for match in _INSTALL_CMD_RE.finditer(text[:PROVENANCE_READ_BYTES]):
        raw = next((group for group in match.groups() if group), "")
        if not raw:
            continue
        pkg_tokens = [t for t in _tokens(raw)
                      if len(t) >= 3 and t not in _PKG_STOPWORD_TOKENS]
        if not pkg_tokens:
            continue
        compact = "".join(pkg_tokens)
        for token in name_tokens:
            if token in pkg_tokens or compact.startswith(token) or token.startswith(compact):
                return "documents the third-party package %s" % (_clean(raw)[:40],)
    return ""


def classify_provenance(root, reader, artifacts, lock_map, warnings):
    """
    Split the detected artifacts into the team's OWN work and VENDORED
    third-party documentation, so maturity is computed from the former.

    Conservative by construction: only an unambiguous signal (a lockfile
    entry, a resolved path through a vendor or plugin-cache directory, or a
    frontmatter key that names an external source) makes something vendored.
    Anything weaker lands in `ambiguous`, which is COUNTED AS OWN for the
    maturity threshold -- erring toward reporting a setup that exists -- and
    reported so the model can say the count is uncertain.
    """
    own = {"skills": 0, "agents": 0}
    vendored = {"skills": 0, "agents": 0}
    ambiguous = {"skills": 0, "agents": 0}
    vendored_rows = []
    ambiguous_rows = []
    reads = 0
    unclassified = 0

    for item in artifacts:
        kind = item["kind"]
        name = item["name"]
        signal = ""
        source = ""
        reason = ""

        if name in lock_map:
            signal = "lockfile"
            source = lock_map[name]
        else:
            rel_dir = item.get("dir") or item.get("entry") or ""
            real = ""
            if rel_dir:
                try:
                    real = os.path.realpath(
                        os.path.join(root, rel_dir.replace("/", os.sep)))
                except (IOError, OSError):
                    real = ""
            if (real and _is_vendor_path(real)) or _is_vendor_path(rel_dir):
                signal = "vendor-path"
                source = _link_label(root, os.path.join(
                    root, rel_dir.replace("/", os.sep))) if rel_dir else ""
            elif item.get("entry") and reads < MAX_PROVENANCE_READS:
                reads += 1
                text = reader.text(
                    os.path.join(root, item["entry"].replace("/", os.sep)),
                    PROVENANCE_READ_BYTES,
                )
                front = _frontmatter_map(text)
                strong = _external_source_value(front, EXTERNAL_SOURCE_KEYS)
                if strong:
                    signal = "frontmatter"
                    source = strong
                else:
                    reason = (_external_source_value(front, WEAK_SOURCE_KEYS)
                              or _third_party_doc_hint(name, text))
            elif item.get("entry"):
                unclassified += 1

        if signal:
            vendored[kind] += 1
            if len(vendored_rows) < 60:
                vendored_rows.append({
                    "name": name,
                    "kind": kind[:-1],
                    "signal": signal,
                    "source": source or "",
                })
        elif reason:
            ambiguous[kind] += 1
            if len(ambiguous_rows) < 40:
                ambiguous_rows.append({
                    "name": name, "kind": kind[:-1], "reason": reason,
                })
        else:
            own[kind] += 1

    if unclassified:
        emitlib.warn(
            warnings,
            "%d artifact(s) were past the provenance read cap (%d) and were "
            "counted as the team's own without being inspected"
            % (unclassified, MAX_PROVENANCE_READS),
        )

    return {
        "own": own,
        "vendored": vendored,
        "ambiguous": ambiguous,
        "vendored_artifacts": vendored_rows,
        "ambiguous_artifacts": ambiguous_rows,
        "lockfiles": [],
    }


class AgenticScan(object):
    """Result of `scan_agentic_dirs`."""

    def __init__(self):
        self.paths = set()      # repo-relative file paths, "/"-separated
        self.symlinks = {}      # repo-relative entry path -> target label
        self.children = {}      # config dir rel -> [immediate child dir names]
        self.entries = 0
        self.depth_capped = False
        self.volume_capped = False
        self.refused = 0        # links that resolved outside the allowed roots
        self.cycles = 0
        self.dangling = 0       # links whose target does not exist


def _under(real, allowed_roots):
    """True when `real` (an already-resolved path) sits under an allowed root."""
    for base in allowed_roots:
        if real == base or real.startswith(base + os.sep):
            return True
    return False


def _link_label(root, full):
    """
    Short, scrubbed description of where a symlink points.

    Repo-relative when the target is inside the repo (the common case: a
    shared store like `.agents/skills/`), otherwise the scrubbed absolute
    path, which turns `/Users/<name>` into `~`.
    """
    try:
        real = os.path.realpath(full)
    except (IOError, OSError):
        return "?"
    if _under(real, [os.path.realpath(root)]):
        return _rel(os.path.realpath(root), real) or "."
    return _clean(real) or "?"


def scan_agentic_dirs(root, warnings):
    """
    Enumerate the agentic-config directories, FOLLOWING symlinks.

    `walk()` deliberately never follows symlinks: on a general repo tree that
    invites cycles and lets a link walk the analyzer out of the repo.  Skill,
    agent and rule directories are the one place where that rule loses real
    data.  A shared store symlinked into `.claude/skills/` is a skill the
    agent genuinely loads, so missing it (a) hides it from the anti-pattern
    A9 de-duplication pass, which then proposes a duplicate of something it
    cannot see, and (b) undercounts the maturity classification that flips the
    reported `mature` at 5+ skills or agents.

    Following symlinks is therefore scoped to these directories only, and
    every way it could go wrong is bounded:

      * depth  -- AGENTIC_SCAN_MAX_DEPTH levels below each config dir,
      * volume -- AGENTIC_SCAN_MAX_ENTRIES files overall,
                  AGENTIC_SCAN_MAX_PER_DIR entries out of any one directory,
      * cycles -- a visited set of *resolved* real paths; a link that loops
                  back onto a directory already entered is skipped,
      * escape -- a link whose target resolves outside both the user's home
                  and the repo itself is refused outright, so no link can
                  walk this scan into `/etc` or a mounted volume.  (The repo
                  is allowed alongside home so that a checkout under `/tmp`
                  or `/srv` still scans its own config.)
      * secrets -- `is_secret_path` refuses the same paths it refuses in the
                  main walk; PRUNE_DIRS are skipped so a vendored
                  `node_modules` inside a skill cannot blow the budget.

    Returns an `AgenticScan`.  Never raises.
    """
    scan = AgenticScan()
    try:
        home = os.path.realpath(os.path.expanduser("~"))
    except (IOError, OSError):
        home = ""
    allowed = [p for p in (home, os.path.realpath(root)) if p]

    for rel_base in AGENTIC_CONFIG_DIRS:
        base = os.path.join(root, rel_base.replace("/", os.sep))
        if not os.path.isdir(base):
            continue
        visited = set()
        queue = [(base, rel_base, 0)]   # (absolute dir, repo-relative dir, depth)
        while queue:
            if scan.entries >= AGENTIC_SCAN_MAX_ENTRIES:
                scan.volume_capped = True
                break
            cur, rel_cur, depth = queue.pop(0)
            try:
                real = os.path.realpath(cur)
            except (IOError, OSError):
                continue
            if not _under(real, allowed):
                scan.refused += 1
                continue
            if real in visited:
                scan.cycles += 1
                continue
            visited.add(real)
            try:
                names = sorted(os.listdir(cur))
            except (IOError, OSError):
                continue
            if len(names) > AGENTIC_SCAN_MAX_PER_DIR:
                scan.volume_capped = True
                names = names[:AGENTIC_SCAN_MAX_PER_DIR]
            for name in names:
                if name in (".DS_Store", "Thumbs.db") or name in PRUNE_DIRS:
                    continue
                full = os.path.join(cur, name)
                rel_path = rel_cur + "/" + name
                if scrublib.is_secret_path(rel_path):
                    continue
                is_link = os.path.islink(full)
                # isdir/exists follow the link, which is the whole point here
                try:
                    if is_link and not os.path.exists(full):
                        scan.dangling += 1     # link with no target: not config
                        continue
                    is_dir = os.path.isdir(full)
                except (IOError, OSError):
                    continue
                if is_dir:
                    if depth == 0:
                        scan.children.setdefault(rel_base, []).append(name)
                    if is_link:
                        scan.symlinks[rel_path] = _link_label(root, full)
                    if depth + 1 <= AGENTIC_SCAN_MAX_DEPTH:
                        queue.append((full, rel_path, depth + 1))
                    else:
                        scan.depth_capped = True
                    continue
                if scan.entries >= AGENTIC_SCAN_MAX_ENTRIES:
                    scan.volume_capped = True
                    break
                if is_link:
                    scan.symlinks[rel_path] = _link_label(root, full)
                scan.paths.add(rel_path)
                scan.entries += 1

    if scan.refused:
        emitlib.warn(
            warnings,
            "%d symlink(s) under the agent config directories resolved outside "
            "the repo and your home directory and were not followed" % scan.refused,
        )
    if scan.cycles:
        emitlib.warn(
            warnings,
            "%d symlink cycle(s) detected while scanning the agent config "
            "directories; each was visited once" % scan.cycles,
        )
    if scan.dangling:
        emitlib.warn(
            warnings,
            "%d symlink(s) under the agent config directories point at a "
            "target that no longer exists and were skipped" % scan.dangling,
        )
    if scan.depth_capped:
        emitlib.warn(
            warnings,
            "agent config scan stopped at its depth cap (%d levels below a "
            "config directory); anything nested deeper was not counted"
            % AGENTIC_SCAN_MAX_DEPTH,
        )
    if scan.volume_capped:
        emitlib.warn(
            warnings,
            "agent config scan hit its volume cap (%d entries); the "
            "existing-config counts are a floor, not a total"
            % AGENTIC_SCAN_MAX_ENTRIES,
        )
    return scan


def _symlink_identity(rel_path):
    """
    `(bucket, name)` for a symlink that is an immediate child of a config
    directory, where `name` is spelled exactly the way the corresponding
    `existing_agentic_config` list spells it -- so membership can be checked
    directly, and only symlinks that produced a counted entry get reported.

    `("", "")` for a link nested deeper, or one under a directory that maps
    to no list.
    """
    for prefix, bucket in ((".claude/skills/", "skills"),
                           (".codex/skills/", "skills"),
                           (".claude/agents/", "agents"),
                           (".codex/agents/", "agents"),
                           (".claude/rules/", "rules"),
                           (".claude/hooks/", "hooks"),
                           (".claude/commands/", "commands")):
        if not rel_path.startswith(prefix):
            continue
        rest = rel_path[len(prefix):]
        if not rest or "/" in rest:
            return ("", "")
        if bucket in ("rules", "hooks"):
            return (bucket, rest)
        stem = rest[:-3] if rest.lower().endswith(".md") else rest
        if bucket == "commands":
            return ("skills", "command:" + stem)
        return (bucket, stem)
    if rel_path.startswith(".cursor/rules/"):
        return ("rules", rel_path)
    return ("", "")


def detect_agentic_config(root, state, reader, warnings):
    scan = scan_agentic_dirs(root, warnings)
    paths = set(state.agentic_paths) | scan.paths
    for extra in (list(INDEX_DOC_PATHS) + list(CODEX_CONFIG_RELS)
                  + list(CODEX_HOOKS_RELS)
                  + [rel for rel, _t in PLUGIN_MANIFEST_RELS]
                  + [".mcp.json", ".claude/settings.json",
                     ".claude/settings.local.json", ".cursor/mcp.json"]):
        full = os.path.join(root, extra.replace("/", os.sep))
        if os.path.exists(full):
            paths.add(extra)

    # -- index docs, de-duplicated by realpath -----------------------------
    # `CLAUDE.md -> AGENTS.md` is one file under two names.  Listing both (as
    # this did) makes phase 7 ask "which index doc do I write to?" and get two
    # answers, and appending the agentify section to each one appends it TWICE
    # to the same file.  One row per real file, the real file named as the
    # canonical path, the other names carried as `aliases`.
    doc_groups = []
    by_identity = {}
    for rel in INDEX_DOC_PATHS:
        if rel not in paths:
            continue
        full = os.path.join(root, rel.replace("/", os.sep))
        # `stat` follows the link, so `(device, inode)` is the file's real
        # identity and catches a HARD link too -- appending to either name
        # writes the same bytes.  Two files with identical *contents* are not
        # the same file and stay separate rows, which is the common case for a
        # copied CLAUDE.md/AGENTS.md pair.
        try:
            info = os.stat(full)
            identity = (info.st_dev, info.st_ino)
        except (IOError, OSError):
            try:
                identity = os.path.realpath(full)
            except (IOError, OSError):
                identity = full
        group = by_identity.get(identity)
        if group is None:
            group = {"rels": []}
            by_identity[identity] = group
            doc_groups.append(group)
        group["rels"].append(rel)

    index_docs = []
    for group in doc_groups:
        rels = group["rels"]
        canonical = ""
        for rel in rels:
            try:
                if not os.path.islink(os.path.join(root, rel.replace("/", os.sep))):
                    canonical = rel
                    break
            except (IOError, OSError):
                continue
        if not canonical:
            canonical = rels[0]
        aliases = [rel for rel in rels if rel != canonical]
        full = os.path.join(root, canonical.replace("/", os.sep))
        try:
            size = os.path.getsize(full)      # follows the link: real bytes
        except (IOError, OSError):
            size = 0
        has_section = False
        if 0 < size <= MAX_INDEX_DOC_BYTES:
            text = reader.text(full, MAX_INDEX_DOC_BYTES)
            has_section = AGENTIFY_MARKER in text
        try:
            is_link = os.path.islink(full)
        except (IOError, OSError):
            is_link = False
        index_docs.append({
            "path": canonical,
            "bytes": size,
            "has_agentify_section": has_section,
            "is_symlink": is_link,
            "link_target": _link_label(root, full) if is_link else "",
            "aliases": aliases,
        })
        if aliases:
            emitlib.warn(
                warnings,
                "%s and %s are the SAME file (%s %s a link to it); it is listed "
                "once, as %s -- write the index-doc section exactly once, to "
                "%s, or it lands in that file twice"
                % (", ".join(aliases), canonical, ", ".join(aliases),
                   "is" if len(aliases) == 1 else "are", canonical, canonical),
            )

    skills = []
    agents = []
    rules = []
    #: name -> {"kind", "name", "entry", "dir"} for the provenance pass.  The
    #: entrypoint path is what carries frontmatter; the directory is what a
    #: symlink resolves through.
    artifact_index = {}

    #: One row per discovered artifact, naming the target that loads it.  A
    #: repo can carry config for both agents at once (and on the verification
    #: machine several skills are physically the same file in both trees), so
    #: "which target is this for?" has to be answered per artifact, not per
    #: repo.  Targets: `claude-code`, `codex`, `shared` (loaded natively by
    #: Codex from `.agents/skills`, and commonly symlinked into
    #: `.claude/skills`), `cursor`, `copilot`.
    artifact_rows = []
    _artifact_row_seen = set()
    #: resolved path -> the name it was first counted under, so the same
    #: physical skill found under two roots is one artifact.
    _resolved_seen = {}

    def _add_row(kind, name, target, rel_path, scope="repo"):
        key = (kind, name, target, rel_path)
        if key in _artifact_row_seen or len(artifact_rows) >= 150:
            return
        _artifact_row_seen.add(key)
        artifact_rows.append({"kind": kind, "name": name, "target": target,
                              "scope": scope, "file": rel_path})

    def _record(kind, name, entry, directory, target="claude-code"):
        _add_row(kind, name, target, entry)
        key = (kind, name)
        if key in artifact_index:
            return
        artifact_index[key] = {
            "kind": kind, "name": name, "entry": entry, "dir": directory,
        }

    #: `(first path, duplicate path)` for every skill directory found under
    #: two roots.  Reported once, in aggregate: a repo that keeps its skills in
    #: `.agents/skills/` and symlinks them into `.claude/skills/` produces one
    #: of these per skill, and 30 warnings saying the same thing is noise.
    _dup_roots = []

    def _same_file_elsewhere(rel_dir):
        """
        True when `rel_dir` resolves to a directory already counted under
        another root -- one skill wearing two names, not two skills.

        This is the cross-target case that must not double-count: Codex's
        repo-level skills root is `.agents/skills/`, and `.claude/skills/`
        entries are commonly symlinks into it (and, at user scope, whole
        Codex skill trees are symlinks into a Claude Code one).  Identity is
        the RESOLVED directory, so the link direction does not matter.
        """
        try:
            resolved = os.path.realpath(
                os.path.join(root, rel_dir.replace("/", os.sep)))
        except (IOError, OSError):
            return False
        first = _resolved_seen.get(resolved)
        if first is not None and first != rel_dir:
            _dup_roots.append((first, rel_dir))
            return True
        _resolved_seen[resolved] = rel_dir
        return False

    #: `.codex/skills/` is NOT a Codex load path (§ the roots table Codex
    #: 0.152.1 wrote into a live session).  Anything found there is counted for
    #: de-duplication and the user is told it is inert.
    _codex_skills_dir_used = False

    for rel in sorted(paths):
        parts = rel.split("/")
        if rel.startswith(".claude/skills/") and len(parts) >= 3:
            if parts[-1].upper() == SKILL_ENTRYPOINT or (len(parts) == 3 and parts[2].endswith(".md")):
                name = parts[2].replace(".md", "")
                if not _same_file_elsewhere("/".join(parts[:3])):
                    skills.append(name)
                    _record("skills", name, rel, "/".join(parts[:3]))
        elif rel.startswith(".claude/agents/") and rel.endswith(".md"):
            agents.append(parts[-1][:-3])
            _record("agents", parts[-1][:-3], rel, rel)
        elif rel.startswith(".claude/rules/") and rel.endswith((".md", ".mdc")):
            rules.append("/".join(parts[2:]))
            _add_row("rules", "/".join(parts[2:]), "claude-code", rel)
        elif rel.startswith(".cursor/rules/"):
            rules.append(rel)
            _add_row("rules", rel, "cursor", rel)
        elif rel == ".cursorrules":
            rules.append(rel)
            _add_row("rules", rel, "cursor", rel)
        # -- Codex, repo scope ---------------------------------------------
        # `.agents/skills/<name>/SKILL.md` is the VERIFIED repo-level Codex
        # skills root (the docs' scope table; `$REPO/.agents/skills` and
        # `$CWD/.agents/skills`).  It is `.agents/`, not `.codex/`, and it is
        # also the shared store `.claude/skills` is commonly symlinked into --
        # hence target `shared` and the resolved-path de-duplication.
        elif rel.startswith(".agents/skills/") and len(parts) >= 3:
            if parts[-1].upper() == SKILL_ENTRYPOINT:
                name = parts[2]
                if not _same_file_elsewhere("/".join(parts[:3])):
                    skills.append(name)
                    _record("skills", name, rel, "/".join(parts[:3]), "shared")
        # `<repo>/.codex/agents/<name>.toml` -- the native Codex subagent
        # format.  Six keys in every real file measured: name, description,
        # model, model_reasoning_effort, sandbox_mode, developer_instructions.
        elif rel.startswith(".codex/agents/") and rel.endswith(".toml") and len(parts) == 3:
            agents.append(parts[-1][:-5])
            _record("agents", parts[-1][:-5], rel, rel, "codex")
        # `<repo>/.codex/rules/<name>.rules` -- Starlark command-approval
        # policy (`prefix_rule(...)`), NOT prose rules.  Counted as a rule
        # because it is a guardrail artifact and a de-duplication target; the
        # warning says what it actually is so nothing proposes prose here.
        elif rel.startswith(".codex/rules/") and rel.endswith(".rules"):
            rules.append(rel)
            _add_row("rules", rel, "codex", rel)
        elif rel.startswith(".codex/skills/") and len(parts) >= 3:
            # same entrypoint rule as .claude/skills: now that the scan
            # follows symlinks it also sees a skill's scripts/ and
            # references/, and every one of those would otherwise re-count
            # the directory as a skill even when it has no SKILL.md.
            if parts[-1].upper() == SKILL_ENTRYPOINT or (len(parts) == 3 and parts[2].endswith(".md")):
                name = parts[2].replace(".md", "")
                if not _same_file_elsewhere("/".join(parts[:3])):
                    skills.append(name)
                    _record("skills", name, rel, "/".join(parts[:3]), "codex")
                    _codex_skills_dir_used = True
        elif rel.startswith(".claude/commands/") and rel.endswith(".md"):
            name = "command:" + parts[-1][:-3]
            skills.append(name)
            _record("skills", name, rel, rel)

    if _dup_roots:
        emitlib.warn(
            warnings,
            "%d skill director%s exist under two roots and resolve to the same "
            "files (e.g. %s and %s); each is counted ONCE -- writing to either "
            "path changes both, and the artifact serves both targets"
            % (len(_dup_roots), "y" if len(_dup_roots) == 1 else "ies",
               _dup_roots[0][0], _dup_roots[0][1]),
        )

    hooks = []
    #: Codex-specific facts phase 6 and phase 8 need and cannot get anywhere
    #: else.  `repo_trust_level` is the big one: `[projects."<abs path>"]
    #: trust_level` gates AGENTS.md, `.codex/config.toml`, `.codex/hooks.json`
    #: and `.codex/rules/` all at once, so an untrusted repo makes every
    #: repo-scoped Codex artifact agentify writes inert.  That is the most
    #: likely silent failure of a generated Codex setup.
    codex_block = {
        "repo_trust_level": "",
        "trust_source": "",
        "features": {},
        "config_files": [],
        "hook_files": [],
        "hook_scripts": [],
        "plugin_manifests": [],
        "skills_root": "",
        "claude_md_fallback": False,
        "index_doc_chain_bytes": 0,
        "notes": [],
    }
    mcp_servers = []
    # Every MCP server is recorded with the target and file it came from.
    # `mapping-rules.md` gate 3 tells the model to check "the servers already
    # in `.mcp.json`" before proposing an MCP draft -- so a server configured
    # only on the OTHER target used to be invisible and agentify would propose
    # a draft for a server the user already has.
    mcp_rows = []
    mcp_seen = set()

    def _add_mcp(name, target, source_file, scope="repo"):
        label = _clean(str(name))[:80]
        if not label:
            return
        # `mcp_servers` is the REPO's server list and stays that way: a
        # user-scope Codex server is real and must be de-duplicated against,
        # but folding it into the repo list would make a machine's global
        # config change what a repo is reported to contain.  User-scope
        # servers live in the rows (with `scope`) and in `user_scope`.
        if scope == "repo":
            mcp_servers.append(label)
        key = (label, target, source_file)
        if key in mcp_seen or len(mcp_rows) >= 60:
            return
        mcp_seen.add(key)
        mcp_rows.append({"name": label, "target": target, "scope": scope,
                         "file": source_file})

    for settings_rel in (".claude/settings.json", ".claude/settings.local.json"):
        full = os.path.join(root, settings_rel.replace("/", os.sep))
        if not os.path.exists(full):
            continue
        data = reader.json(full)
        if not isinstance(data, dict):
            continue
        hook_block = data.get("hooks")
        if isinstance(hook_block, dict):
            for event, entries in hook_block.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries[:20]:
                    if not isinstance(entry, dict):
                        continue
                    matcher = str(entry.get("matcher", "") or "*")
                    inner = entry.get("hooks")
                    if isinstance(inner, list) and inner:
                        for hook in inner[:10]:
                            cmd = ""
                            if isinstance(hook, dict):
                                cmd = _clean(str(hook.get("command", "")))[:80]
                            hooks.append("%s:%s:%s" % (event, matcher, cmd))
                    else:
                        hooks.append("%s:%s" % (event, matcher))
        servers = data.get("mcpServers")
        if isinstance(servers, dict):
            for key in list(servers)[:60]:
                _add_mcp(key, "claude-code", settings_rel)

    for mcp_rel, mcp_target in ((".mcp.json", "claude-code"),
                                (".cursor/mcp.json", "cursor"),
                                (".vscode/mcp.json", "copilot")):
        full = os.path.join(root, mcp_rel.replace("/", os.sep))
        if not os.path.exists(full):
            continue
        data = reader.json(full)
        if isinstance(data, dict):
            block = data.get("mcpServers") or data.get("servers")
            if isinstance(block, dict):
                for key in list(block)[:60]:
                    _add_mcp(key, mcp_target, mcp_rel)

    # Codex declares its servers in TOML, in a file nothing used to open.
    # Measured: `.mcp.json` held `cloudflare-api` and `.codex/config.toml`
    # held `[mcp_servers.dodo-knowledge]`; only the first was reported.
    for codex_rel in CODEX_CONFIG_RELS:
        full = os.path.join(root, codex_rel.replace("/", os.sep))
        if not os.path.exists(full):
            continue
        text = reader.text(full)
        if not text:
            continue
        names, parsed_ok = parse_codex_mcp_servers(text)
        for name in names:
            _add_mcp(name, "codex", codex_rel)
        if not parsed_ok:
            emitlib.warn(
                warnings,
                "%s mentions mcp_servers but the bounded TOML scan could not "
                "read %s of it; the codex MCP list may be incomplete -- open "
                "the file before proposing an MCP draft"
                % (codex_rel, "any" if not names else "all"),
            )
        codex_facts = parse_codex_config_facts(text, root)
        codex_block["config_files"].append(codex_rel)
        if codex_facts["has_hooks_table"]:
            hooks.append("%s:[hooks]" % codex_rel)
            _add_row("hooks", "[hooks] table", "codex", codex_rel)
            codex_block["hook_files"].append(codex_rel)
        for key, value in sorted(codex_facts["features"].items()):
            codex_block["features"][key] = value
        if codex_facts["repo_trust_level"]:
            codex_block["repo_trust_level"] = codex_facts["repo_trust_level"]
            codex_block["trust_source"] = codex_rel
        if codex_facts["claude_md_fallback"]:
            codex_block["claude_md_fallback"] = True

    # -- Codex hooks: `<repo>/.codex/hooks.json` -------------------------------
    # Verified 2026-09-05 (codex-cli 0.152.1, official docs, and a repo-scoped
    # file in production use on the verification machine): Codex HAS a hook
    # engine -- 12 events, regex matchers over tool names, and the same
    # three-level JSON shape as Claude Code's `settings.json` hooks block.  A
    # repo that already has one must never be handed a duplicate.
    for hooks_rel in CODEX_HOOKS_RELS:
        full = os.path.join(root, hooks_rel.replace("/", os.sep))
        if not os.path.isfile(full):
            continue
        data = reader.json(full)
        if not isinstance(data, dict):
            emitlib.warn(
                warnings,
                "%s exists but could not be parsed as JSON; treat the Codex "
                "hook list as incomplete and open it before proposing a hook"
                % hooks_rel,
            )
            continue
        inner = data.get("hooks") if isinstance(data.get("hooks"), dict) else data
        found = parse_hook_block(inner)
        for entry in found:
            hooks.append(entry)
            _add_row("hooks", entry, "codex", hooks_rel)
        codex_block["hook_files"].append(hooks_rel)
        if not found:
            emitlib.warn(
                warnings,
                "%s exists but declared no hook entries this scan recognised"
                % hooks_rel,
            )

    # -- plugin manifests -----------------------------------------------------
    # Real cross-tool plugins dual-ship `.claude-plugin/plugin.json` and
    # `.codex-plugin/plugin.json` side by side; the Codex schema is the Claude
    # one plus `skills` (a path) and an `interface` block.
    for manifest_rel, manifest_target in PLUGIN_MANIFEST_RELS:
        full = os.path.join(root, manifest_rel.replace("/", os.sep))
        if not os.path.isfile(full):
            continue
        data = reader.json(full)
        name = ""
        if isinstance(data, dict):
            name = _clean(str(data.get("name", "")))[:80]
        codex_block["plugin_manifests"].append(manifest_rel)
        _add_row("plugin", name or manifest_rel, manifest_target, manifest_rel)

    # `.git/hooks` and `.husky` are listed rather than walked.  `isfile`
    # follows symlinks, so a hook installed as a link (lefthook, husky-init,
    # a shared hook store) is already counted here -- it is only recorded as
    # a symlink so the plan can name where it really lives.
    hook_links = {}
    for hook_dir, label in ((os.path.join(root, ".git", "hooks"), "git"),
                            (os.path.join(root, ".husky"), "husky")):
        try:
            for name in sorted(os.listdir(hook_dir))[:30]:
                if name.endswith(".sample") or name.startswith("_") or name.startswith("."):
                    continue
                full = os.path.join(hook_dir, name)
                if os.path.isfile(full):
                    hooks.append("%s:%s" % (label, name))
                    if os.path.islink(full):
                        hook_links["%s:%s" % (label, name)] = _link_label(root, full)
        except (IOError, OSError):
            pass

    # Every hook that has not already been rowed by the Codex pass above gets
    # a row here, so `artifacts_by_target` covers the whole hook list rather
    # than only the new half.  `.git/hooks` and `.husky` are target-neutral --
    # git runs them for every agent and for the human -- so they are labelled
    # `git`, not attributed to either agent.
    _rowed_hooks = set(row["name"] for row in artifact_rows
                       if row["kind"] == "hooks")
    for entry in sorted(set(hooks)):
        if entry in _rowed_hooks:
            continue
        head = entry.split(":")[0]
        if head in ("git", "husky"):
            _add_row("hooks", entry, "git",
                     ".git/hooks" if head == "git" else ".husky")
        else:
            _add_row("hooks", entry, "claude-code", ".claude/settings.json")

    targets = []
    if any(p == "CLAUDE.md" or p.startswith(".claude/") for p in paths):
        targets.append("claude-code")
    if any(p in ("AGENTS.md", "AGENTS.override.md", "CODEX.md")
           or p.startswith(".codex/") for p in paths):
        targets.append("codex")
    if any(p == ".cursorrules" or p.startswith(".cursor/") for p in paths):
        targets.append("cursor")
    if ".github/copilot-instructions.md" in paths:
        targets.append("copilot")

    skills = sorted(set(skills))
    agents = sorted(set(agents))
    rules = sorted(set(rules))
    hooks = sorted(set(hooks))
    mcp_servers = sorted(set(mcp_servers))

    # `mapping-rules.md` gate 3 names `.mcp.json` and only `.mcp.json`, so a
    # server the user already runs on the OTHER target reads as "not
    # configured" and agentify proposes a draft for something they have.
    # Name the divergence rather than relying on the reader to diff two lists.
    _claude_mcp = set(row["name"] for row in mcp_rows
                      if row["target"] == "claude-code")
    _elsewhere = sorted(set(row["name"] for row in mcp_rows
                            if row["target"] != "claude-code") - _claude_mcp)
    if _elsewhere:
        emitlib.warn(
            warnings,
            "%d MCP server(s) are configured on another target but are NOT in "
            ".mcp.json (%s); gate 3 in mapping-rules.md names .mcp.json only, "
            "so check mcp_servers_by_source before proposing an MCP draft"
            % (len(_elsewhere), ", ".join(_elsewhere[:6])),
        )

    # -- Codex facts the plan and phase 8 need --------------------------------
    if "codex" in targets or any(row["target"] in ("codex", "shared")
                                 for row in artifact_rows):
        # skills root
        if any(p.startswith(".agents/skills/") for p in paths):
            codex_block["skills_root"] = CODEX_REPO_SKILL_DIR
        if _codex_skills_dir_used:
            emitlib.warn(
                warnings,
                ".codex/skills/ holds skill directories, but it is NOT a Codex "
                "skills root -- the repo-level root is .agents/skills/ "
                "(verified 2026-09-05, codex-cli 0.152.1).  They are counted "
                "for de-duplication; say in the plan that they are inert where "
                "they are, and never write a new skill to .codex/skills/",
            )
        # hook scripts sitting beside a hooks.json
        for rel in sorted(paths):
            if rel.startswith(".codex/hooks/") and not rel.endswith("hooks.json"):
                if len(codex_block["hook_scripts"]) < 40:
                    codex_block["hook_scripts"].append(rel)
        if codex_block["features"].get("hooks") is False:
            emitlib.warn(
                warnings,
                "[features] hooks = false in a Codex config this repo carries; "
                "a generated .codex/hooks.json will not run until that is "
                "flipped -- state it in the plan, do not silently rely on it",
            )
        # AGENTS.md byte budget.  project_doc_max_bytes defaults to 32768 and
        # discovery STOPS adding files at the cap, so appending to a large
        # AGENTS.md can silently drop deeper nested instruction files.
        chain = 0
        for doc in index_docs:
            if doc["path"] in ("AGENTS.md", "AGENTS.override.md"):
                chain += int(doc.get("bytes") or 0)
        try:
            user_agents_md = os.path.join(codex_home_dir(), "AGENTS.md")
            if os.path.isfile(user_agents_md):
                chain += os.path.getsize(user_agents_md)
        except (IOError, OSError):
            pass
        codex_block["index_doc_chain_bytes"] = chain
        if chain > 24576:
            emitlib.warn(
                warnings,
                "the AGENTS.md instruction chain is already %d bytes against a "
                "32768-byte project_doc_max_bytes cap; Codex STOPS adding "
                "files at the cap, so appending an agentify section can "
                "silently truncate it or drop deeper AGENTS.md files -- "
                "measure the chain again in phase 8" % chain,
            )
        if not codex_block["claude_md_fallback"] and any(
                doc["path"] == "CLAUDE.md" and not doc.get("aliases")
                for doc in index_docs) and not any(
                doc["path"] in ("AGENTS.md", "AGENTS.override.md")
                for doc in index_docs):
            emitlib.warn(
                warnings,
                "this repo has CLAUDE.md and no AGENTS.md.  Codex does NOT "
                "read CLAUDE.md by default (project_doc_fallback_filenames "
                "defaults to an empty list), so the repo currently gives Codex "
                "no index doc at all -- write AGENTS.md, or symlink it, rather "
                "than assuming the existing file is read",
            )

    # -- Codex user scope: reported so a same-name collision can be named; it
    # covers no candidate and feeds no count (blueprint.md 2.1) -------------
    try:
        user_scope = scan_codex_user_scope(root, reader, warnings)
    except Exception:
        user_scope = {"codex_home": "", "scanned": False, "skills": [],
                      "skills_shared_with_claude_code": [], "agents": [],
                      "rules": [], "hooks": [], "plugins": [],
                      "mcp_servers": [],
                      "counts": {"skills": 0, "agents": 0, "rules": 0,
                                 "hooks": 0, "plugins": 0},
                      "own": {"skills": 0}, "vendored": {"skills": 0},
                      "notes": ["the user-scope scan failed and was skipped"]}
    _user_facts = user_scope.pop("_facts", None)
    if isinstance(_user_facts, dict):
        if not codex_block["repo_trust_level"] and _user_facts.get("repo_trust_level"):
            codex_block["repo_trust_level"] = _user_facts["repo_trust_level"]
            codex_block["trust_source"] = "%s/config.toml" % (
                user_scope.get("codex_home") or "~/.codex")
        for key, value in sorted((_user_facts.get("features") or {}).items()):
            codex_block["features"].setdefault(key, value)
        if _user_facts.get("claude_md_fallback"):
            codex_block["claude_md_fallback"] = True
    for name in user_scope.get("mcp_servers") or []:
        _add_mcp(name, "codex", "%s/config.toml"
                 % (user_scope.get("codex_home") or "~/.codex"), "user")
    # User-scope artifacts are NOT duplicated into `artifacts_by_target`: they
    # are already enumerated in `user_scope`, they all belong to the Codex
    # target by construction, and one row each for 60 global skills crowded out
    # the repo rows under the output cap.  Rows are repo scope; `user_scope` is
    # user scope; `mcp_servers_by_source` carries both because gate 3 in
    # `mapping-rules.md` reads that list directly.

    # Trust is checked LAST, because the declaration usually lives in the
    # user-scope config.toml rather than the repo's -- warning before that file
    # was read reported every trusted repo as untrusted.  This is the single
    # most likely silent failure of a generated Codex setup: one key gates
    # AGENTS.md, .codex/config.toml, .codex/hooks.json and .codex/rules/ at
    # once.
    if ("codex" in targets or any(row["target"] in ("codex", "shared")
                                  for row in artifact_rows)):
        if codex_block["repo_trust_level"] not in ("trusted", "verified"):
            emitlib.warn(
                warnings,
                "Codex project trust for this repo is %s.  "
                "[projects.\"<abs path>\"] trust_level gates AGENTS.md, "
                ".codex/config.toml, .codex/hooks.json and .codex/rules/ "
                "together -- every repo-scoped Codex artifact is inert without "
                "it.  Put trusting the project in the plan's capability notes "
                "and in the report's manual checklist; agentify never edits "
                "the user's config.toml to set it"
                % (("declared %s" % codex_block["repo_trust_level"])
                   if codex_block["repo_trust_level"]
                   else "not declared in any config.toml this scan read"),
            )
    counts = {
        "skills": len(skills),
        "agents": len(agents),
        "rules": len(rules),
        "hooks": len(hooks),
    }

    # -- symlinked entries -------------------------------------------------
    # Reported as a separate block, never folded into the name lists: the
    # names in `skills`/`agents`/`rules` are what the A9 de-duplication pass
    # matches on, so a "(symlink)" suffix there would break matching.  The
    # `counts` map keeps exactly its four contract keys for the same reason
    # `commands` keeps exactly seven -- consumers iterate both.
    symlinked = {"skills": [], "agents": [], "rules": [], "hooks": []}
    members = {"skills": set(skills), "agents": set(agents),
               "rules": set(rules), "hooks": set(hooks)}
    for rel_link in sorted(scan.symlinks):
        bucket, name = _symlink_identity(rel_link)
        if not bucket:
            continue
        if bucket == "hooks":
            # hook entries are spelled "<event>:<matcher>:<command>", so a
            # symlinked script matches by basename appearing in a command
            if not any(name in entry for entry in hooks):
                continue
        elif name not in members[bucket]:
            # a link that resolved to nothing countable (a cycle, a docs
            # folder, a target refused by the bounds) -- already reported by
            # the scan's own warnings; do not inflate this list with it
            continue
        symlinked[bucket].append("%s -> %s" % (rel_link, scan.symlinks[rel_link] or "?"))
    for hook_key in sorted(hook_links):
        symlinked["hooks"].append("%s -> %s" % (hook_key, hook_links[hook_key] or "?"))
    for bucket in ("skills", "agents", "rules", "hooks"):
        entries = symlinked[bucket]
        if not entries:
            continue
        symlinked[bucket] = entries[:60]
        emitlib.warn(
            warnings,
            "%d of %d %s are symlinks (e.g. %s); they were followed and "
            "counted once -- a symlink is never edited, and it covers a "
            "candidate only as its own type does (blueprint.md 2.1)"
            % (len(entries), counts.get(bucket, 0), bucket, entries[0]),
        )

    # A directory under a skills root with no SKILL.md is not a skill.
    # Say so, so the plan does not look like it lost one.  `.agents/skills`
    # belongs in this list: it is CODEX_REPO_SKILL_DIR, the repo-level Codex
    # skills root agentify itself writes to, so an orphan directory there is
    # exactly as invisible to Codex as a `.claude/skills` orphan is to Claude
    # Code -- and omitting it made a Codex-target run report the Claude Code
    # path for a directory that is orphaned under both.
    for dir_rel in (".claude/skills", CODEX_REPO_SKILL_DIR, ".codex/skills"):
        orphans = [
            name for name in scan.children.get(dir_rel, [])
            if name not in skills
        ]
        if orphans:
            one = len(orphans) == 1
            emitlib.warn(
                warnings,
                "%d director%s under %s/ %s no SKILL.md and %s not counted as "
                "%s: %s"
                % (len(orphans), "y" if one else "ies", dir_rel,
                   "holds" if one else "hold", "is" if one else "are",
                   "a skill" if one else "skills", ", ".join(sorted(orphans)[:8])),
            )
    # -- provenance: whose artifacts are these? ----------------------------
    # `maturity` gates NOTHING (references/coverage.md 6).  It used to flip the
    # run into an audit-only mode that cut the output, and that mode is gone:
    # measured on a 268k-line repo with 0 rules, 0 hooks and 0 subagents, 61
    # skill directories -- 48 of them installed third-party guides -- tripped
    # the threshold and throttled the run on the repo with the most missing.
    # What provenance is still for: one line of context in the plan, and better
    # de-duplication.  Vendored third-party documentation stays in
    # `skills`/`agents`/`counts` -- de-duplication needs it -- and is
    # subtracted only here.
    lock_map, lock_files = read_skills_lock(root, reader, warnings)
    provenance = classify_provenance(
        root, reader,
        [artifact_index[key] for key in sorted(artifact_index)],
        lock_map, warnings,
    )
    provenance["lockfiles"] = lock_files
    own_total = (provenance["own"]["skills"] + provenance["own"]["agents"]
                 + provenance["ambiguous"]["skills"]
                 + provenance["ambiguous"]["agents"])
    vendored_total = (provenance["vendored"]["skills"]
                      + provenance["vendored"]["agents"])
    total = counts["skills"] + counts["agents"]
    provenance["maturity_basis"] = (
        "maturity counts %d of %d skills+agents as the team's own "
        "(%d vendored, %d ambiguous and counted as own)"
        % (own_total, total, vendored_total,
           provenance["ambiguous"]["skills"] + provenance["ambiguous"]["agents"])
    )

    if own_total >= 5:
        maturity = "mature"
    elif index_docs or skills or agents or rules or hooks or mcp_servers or targets:
        maturity = "basic"
    else:
        maturity = "none"

    if vendored_total:
        example = provenance["vendored_artifacts"][0]
        emitlib.warn(
            warnings,
            "%d of %d existing skills/agents are third-party, installed rather "
            "than written here (e.g. %s, via %s%s); they do NOT count toward "
            "maturity and they do NOT cover any candidate -- a third-party guide "
            "is generic by construction, so a generated skill LINKS it as a "
            "reference from the step that needs it and is still built "
            "(blueprint.md 2.1); a same-name path collision is resolved by naming"
            % (vendored_total, total, example.get("name", "?"),
               example.get("signal", "?"),
               ": " + example["source"] if example.get("source") else ""),
        )
    if vendored_total and total >= 5 and own_total < 5:
        emitlib.warn(
            warnings,
            "%d skills+agents were found but only %d %s the team's own -- most "
            "of what is installed here was not written for this repo; say so in "
            "one line of the plan and build the full setup regardless"
            % (total, own_total, "is" if own_total == 1 else "are"),
        )
    if provenance["ambiguous_artifacts"]:
        emitlib.warn(
            warnings,
            "%d artifact(s) could not be classified as the team's own or "
            "third-party and were counted as the team's own (the conservative "
            "direction): %s"
            % (len(provenance["ambiguous_artifacts"]),
               ", ".join("%s (%s)" % (row["name"], row["reason"])
                         for row in provenance["ambiguous_artifacts"][:5])),
        )

    if maturity == "mature":
        emitlib.warn(
            warnings,
            "this repo already has an agentic setup (%d of %d skills+agents are "
            "the team's own): de-duplicate against the team's own artifacts of "
            "the same type (blueprint.md 2.1), testing each against this repo's "
            "commands and paths rather than trusting it; never restructure or "
            "rewrite what is there; build the rest of the setup normally -- "
            "`maturity` limits nothing"
            % (own_total, total),
        )

    return {
        "maturity": maturity,
        "targets_detected": targets,
        "index_docs": index_docs,
        "skills": skills[:60],
        "agents": agents[:60],
        "rules": rules[:60],
        "hooks": hooks[:60],
        "mcp_servers": mcp_servers[:40],
        "mcp_servers_by_source": mcp_rows,
        "artifacts_by_target": _group_artifact_rows(artifact_rows),
        "counts": counts,
        "provenance": provenance,
        "symlinked": symlinked,
        "codex": codex_block,
        "user_scope": user_scope,
    }


# ---------------------------------------------------------------------------
# git (read-only, short timeouts, degrades to is_repo=false)
# ---------------------------------------------------------------------------

def _git(root, args, timeout):
    try:
        proc = subprocess.Popen(
            ["git", "--no-optional-locks"] + args,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, ValueError):
        return None
    try:
        out, _err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.communicate(timeout=1)
        except Exception:  # pragma: no cover - defensive
            pass
        return None
    if proc.returncode != 0:
        return None
    try:
        return out.decode("utf-8", "replace")
    except Exception:  # pragma: no cover - defensive
        return None


def collect_git(root, warnings, budget_s):
    block = {
        "is_repo": False,
        "branch": "",
        "dirty": False,
        "age_days": 0,
        "contributors": 0,
        "commits_90d": 0,
    }
    per_call = max(1.0, min(3.0, budget_s / 4.0))

    inside = _git(root, ["rev-parse", "--is-inside-work-tree"], per_call)
    if inside is None or inside.strip() != "true":
        emitlib.warn(warnings, "not a git repository (or git unavailable): "
                               "git evidence unavailable, mine_git.py will be a no-op")
        return block
    block["is_repo"] = True

    branch = _git(root, ["rev-parse", "--abbrev-ref", "HEAD"], per_call)
    block["branch"] = branch.strip() if branch else ""

    status = _git(root, ["status", "--porcelain"], per_call)
    if status is None:
        block["dirty"] = True
        emitlib.warn(warnings, "git status did not complete; assuming a dirty tree "
                               "(confirm with the user before building)")
    else:
        block["dirty"] = bool(status.strip())

    first = _git(root, ["log", "--max-parents=0", "--format=%ct", "HEAD"], per_call)
    if first:
        stamps = [int(s) for s in first.split() if s.isdigit()]
        if stamps:
            import time as _time
            block["age_days"] = max(0, int((_time.time() - min(stamps)) / 86400.0))

    shortlog = _git(root, ["shortlog", "-sn", "--all", "--no-merges"], per_call)
    if shortlog is not None:
        block["contributors"] = len([l for l in shortlog.splitlines() if l.strip()])

    count = _git(root, ["rev-list", "--count", "--since=90.days", "HEAD"], per_call)
    if count and count.strip().isdigit():
        block["commits_90d"] = int(count.strip())

    return block


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_parser():
    parser = emitlib.base_parser(
        TOOL,
        "agentify phase 1: walk a repository once and emit discovery.json.",
    )
    parser.add_argument(
        "--timeout-s", type=float, default=10.0, dest="timeout_s", metavar="N",
        help="soft wall-clock budget in seconds (default: 10). The walk stops "
             "and emits partial results rather than overrunning it.",
    )
    parser.add_argument(
        "--max-files", type=int, default=60000, dest="max_files", metavar="N",
        help="stop walking after this many files (default: 60000)",
    )
    return parser


def empty_agentic_config():
    """
    `existing_agentic_config` with every value empty.

    One definition, used by `empty_payload` and by the degraded path in
    `main()`, so a new key can never land in one and be missed in the other --
    which is exactly how `symlinked` and `provenance` would drift.
    """
    return {
        "maturity": "none",
        "targets_detected": [],
        "index_docs": [],
        "skills": [], "agents": [], "rules": [], "hooks": [], "mcp_servers": [],
        "mcp_servers_by_source": [],
        "artifacts_by_target": [],
        "counts": {"skills": 0, "agents": 0, "rules": 0, "hooks": 0},
        "provenance": {
            "own": {"skills": 0, "agents": 0},
            "vendored": {"skills": 0, "agents": 0},
            "ambiguous": {"skills": 0, "agents": 0},
            "vendored_artifacts": [],
            "ambiguous_artifacts": [],
            "lockfiles": [],
            "maturity_basis": "no existing artifacts were found",
        },
        "symlinked": {"skills": [], "agents": [], "rules": [], "hooks": []},
        "codex": {
            "repo_trust_level": "", "trust_source": "", "features": {},
            "config_files": [], "hook_files": [], "hook_scripts": [],
            "plugin_manifests": [], "skills_root": "",
            "claude_md_fallback": False, "index_doc_chain_bytes": 0,
            "notes": [],
        },
        "user_scope": {
            "codex_home": "", "scanned": False,
            "skills": [], "skills_shared_with_claude_code": [], "agents": [],
            "rules": [], "hooks": [], "plugins": [], "mcp_servers": [],
            "counts": {"skills": 0, "agents": 0, "rules": 0, "hooks": 0,
                       "plugins": 0},
            "own": {"skills": 0}, "vendored": {"skills": 0}, "notes": [],
        },
    }


def empty_payload(root, warnings=None):
    """
    The full discovery schema with every value empty.

    A degraded run returns THIS, not a `fail()` object: the consumer gets the
    same 19 keys it gets from a successful run, so every downstream reader
    (`discovery["commands"]["test"]`, `discovery["repo"]["size_bucket"]`) works
    without a shape check.  The `warnings` array carries what was lost.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "repo": {
            "root": root,
            "name": os.path.basename(str(root).rstrip(os.sep)) or str(root),
            "loc_estimate": 0,
            "file_count": 0,
            "size_bucket": "small",
        },
        "languages": [],
        "package_managers": [],
        "manifests": [],
        "commands": {
            "install": "", "dev": "", "build": "", "test": "",
            "lint": "", "typecheck": "", "format": "",
        },
        "raw_scripts": {},
        "frameworks": [],
        "external_services": [],
        "folders": [],
        "docs": [],
        "ci": [],
        "env_var_names": [],
        "monorepo": {
            "is_monorepo": False, "tool": "", "workspaces": [],
            "excludes": [], "tools": [], "systems": [], "task_runners": [],
        },
        "existing_agentic_config": empty_agentic_config(),
        "tooling": {"on_path": [], "note": ""},
        "git": {
            "is_repo": False, "branch": "", "dirty": False,
            "age_days": 0, "contributors": 0, "commits_90d": 0,
        },
        "warnings": list(warnings or []),
        "timing_ms": 0,
    }


def main(argv=None):
    args = build_parser().parse_args(argv)
    if getattr(args, "selftest", False):
        return selftest()

    root = emitlib.resolve_repo(args.repo)
    cap = args.cap_chars if args.cap_chars else DEFAULT_CAP_CHARS

    # Not a directory: missing, deleted, a plain file, /dev/null, or a
    # directory we lack permission to stat.  All of these are DEGRADED, not
    # fatal -- see the exit-code contract in lib/emit.py.  Emit the full
    # schema with empty values so phase 3 can keep going on repo-free
    # evidence (transcripts and git may still have plenty to say).
    if not os.path.isdir(root):
        if not os.path.exists(root):
            reason = "path does not exist"
        elif os.path.isfile(root):
            reason = "path is a file, not a directory"
        else:
            reason = "path is not a readable directory"
        payload = empty_payload(root)
        emitlib.warn(
            payload["warnings"],
            "repo path unusable (%s): %s -- discovery returned an empty "
            "result; continue the run on transcript and git evidence only and "
            "say so in the plan" % (reason, root),
        )
        emitlib.emit(payload, cap_chars=cap, trim_keys=TRIM_KEYS)
        return 0

    warnings = []
    timer = emitlib.Timer()
    timer.__enter__()

    reader = Reader(warnings)
    state = State(root, warnings)

    matcher = GitignoreMatcher()
    gitignore = os.path.join(root, ".gitignore")
    if os.path.exists(gitignore):
        matcher.add_file(gitignore)
        matcher.add_file(os.path.join(root, ".git", "info", "exclude"))
        matcher.compile()
        if matcher.skipped:
            emitlib.warn(
                warnings,
                "%d .gitignore pattern(s) were too exotic to interpret and were "
                "skipped (e.g. %s)" % (len(matcher.skipped), _printable(matcher.skipped[0])),
            )
        if matcher.has_negation:
            emitlib.warn(
                warnings,
                "negated .gitignore patterns are honored per-file but ignored "
                "directories are still pruned, so re-includes under them are missed",
            )
        emitlib.warn(warnings, "nested .gitignore files below the repo root are not applied")

    deadline_ms = int(max(0.05, args.timeout_s) * 1000 * 0.80)
    try:
        walk(root, state, reader, matcher, deadline_ms, timer, max(1, args.max_files))
    except Exception as exc:  # never let a walk error kill the run
        emitlib.warn(warnings, "walk aborted: %s" % type(exc).__name__)
        if args.debug:
            emitlib.eprint("walk error: %r" % (exc,))

    manifests = Manifests()
    try:
        read_manifests(root, state, reader, manifests)
    except Exception as exc:
        emitlib.warn(warnings, "manifest parsing degraded: %s" % type(exc).__name__)
        if args.debug:
            emitlib.eprint("manifest error: %r" % (exc,))

    ci = read_ci(root, state, reader)
    env_names = read_env_names(root, state, reader)
    package_managers, js_pm_decision = detect_package_managers(
        state, manifests, warnings)
    commands, command_provenance = resolve_commands(
        state, manifests, package_managers, warnings, js_pm_decision, ci)
    frameworks = detect_frameworks(state, manifests)
    services = detect_services(manifests, env_names, state)
    languages, loc_total = build_languages(state)
    folders = build_folders(state, [f.get("name") for f in frameworks])
    monorepo = detect_monorepo(root, state, manifests, warnings)

    try:
        agentic = detect_agentic_config(root, state, reader, warnings)
    except Exception as exc:
        emitlib.warn(warnings, "existing-config detection degraded: %s" % type(exc).__name__)
        agentic = empty_agentic_config()

    git_budget = max(1.0, args.timeout_s - (timer.elapsed_ms() / 1000.0))
    git_block = collect_git(root, warnings, git_budget)

    if loc_total < 10000:
        bucket = "small"
    elif loc_total <= 80000:
        bucket = "medium"
    else:
        bucket = "large"

    docs = []
    for rel, kind, size, _depth in sorted(state.doc_paths, key=lambda d: (d[3], d[0]))[:40]:
        docs.append({"path": rel, "kind": kind, "bytes": size})

    # The listing leads with the manifests that were actually PARSED, then
    # fills up with the rest in (depth, path) order.  Truncating a monorepo's
    # 235 manifests in raw walk order showed 54 crate Cargo.toml files and not
    # one workspace package.json -- a listing that contradicted the payload's
    # own raw_scripts.  Anything dropped here is accounted for in `warnings`.
    kinds = dict((rel, kind) for rel, kind, _d in state.manifest_paths)
    order = list(getattr(manifests, "read_paths", []))
    seen = set(order)
    for rel, _kind, _depth in sorted(state.manifest_paths, key=lambda m: (m[2], m[0])):
        if rel not in seen:
            seen.add(rel)
            order.append(rel)
    manifest_rows = [{"path": rel, "kind": kinds.get(rel, "")} for rel in order[:60]]

    # Provenance for `commands` rides inside `raw_scripts` under a reserved key
    # that cannot collide with a repo-relative manifest path (paths never start
    # with "#").  The value keeps raw_scripts' str -> {str: str} shape, so a
    # consumer walking it as {manifest: {name: cmd}} still walks cleanly.
    raw_scripts = dict(manifests.raw_scripts)
    if any(command_provenance.values()):
        raw_scripts[COMMAND_PROVENANCE_KEY] = command_provenance

    emitlib.warn(
        warnings,
        "loc figures are ESTIMATES: newline counts, per-file read capped at "
        "%d MB, code files only (markdown, json, yaml and toml excluded)"
        % (MAX_LOC_READ_BYTES // (1024 * 1024)),
    )
    if reader.refused:
        emitlib.warn(
            warnings,
            "%d path(s) matching secret patterns were never opened" % reader.refused,
        )
    if not state.env_paths:
        emitlib.warn(warnings, "no .env files found; env var names come from CI references only")

    timer.__exit__(None, None, None)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "repo": {
            "root": root,
            "name": os.path.basename(root.rstrip(os.sep)) or root,
            "loc_estimate": loc_total,
            "file_count": state.file_count,
            "size_bucket": bucket,
        },
        "languages": languages,
        "package_managers": package_managers,
        "manifests": manifest_rows,
        "commands": commands,
        "raw_scripts": raw_scripts,
        "frameworks": frameworks,
        "external_services": services,
        "folders": folders,
        "docs": docs,
        "ci": ci,
        "env_var_names": env_names,
        "monorepo": monorepo,
        "existing_agentic_config": agentic,
        "tooling": detect_tooling(),
        "git": git_block,
        "warnings": warnings,
        "timing_ms": timer.ms,
    }

    emitlib.emit(payload, cap_chars=cap, trim_keys=TRIM_KEYS)
    return 0


# ---------------------------------------------------------------------------
# --selftest
# ---------------------------------------------------------------------------

def selftest():
    """
    Fast internal sanity check for contributors and the release checklist:
    imports resolve, emit round-trips, the module's regexes compile, and a
    synthetic repo walks end to end into the full schema.  Sub-second; touches
    only a temp directory and never the user's machine.
    """
    import io
    import shutil
    import tempfile
    import time as _time

    started = int(_time.time() * 1000)
    checks = []

    def add(name, ok, detail=""):
        checks.append((name, bool(ok), str(detail)))

    add(
        "imports resolve",
        hasattr(scrublib, "scrub") and hasattr(emitlib, "emit") and hasattr(emitlib, "selftest_report"),
        "lib.emit, lib.scrub",
    )

    ok, detail = emitlib.check_regexes(sys.modules[__name__])
    add("regexes compile and match", ok, detail)

    buffer = io.StringIO()
    probe = empty_payload("/nonexistent")
    text = emitlib.emit(probe, cap_chars=DEFAULT_CAP_CHARS, trim_keys=TRIM_KEYS, stream=buffer)
    try:
        parsed = json.loads(text)
    except ValueError as exc:
        parsed = {}
        add("emit round-trips", False, str(exc))
    else:
        add(
            "emit round-trips",
            parsed.get("tool") == TOOL and isinstance(parsed.get("warnings"), list),
            "%d keys" % len(parsed),
        )
    add(
        "empty_payload carries every contract key",
        all(
            k in parsed
            for k in (
                "repo", "languages", "package_managers", "manifests", "commands",
                "raw_scripts", "frameworks", "external_services", "folders", "docs",
                "ci", "env_var_names", "monorepo", "existing_agentic_config", "tooling",
                "git", "warnings", "timing_ms",
            )
        )
        and sorted(parsed.get("commands", {}).keys())
        == ["build", "dev", "format", "install", "lint", "test", "typecheck"],
        str(sorted(parsed.get("commands", {}).keys())),
    )

    # -- synthetic repo, walked end to end -----------------------------------
    fixture = tempfile.mkdtemp(prefix="agentify-discover-selftest-")
    try:
        with open(os.path.join(fixture, "package.json"), "w") as handle:
            handle.write(
                '{"name":"fx","packageManager":"pnpm@9.0.0",'
                '"scripts":{"test":"vitest run","build":"tsc -p ."},'
                '"dependencies":{"next":"14.0.0"}}'
            )
        os.makedirs(os.path.join(fixture, "src", "api"))
        with open(os.path.join(fixture, "src", "api", "users.ts"), "w") as handle:
            handle.write("export const users = [];\n" * 20)
        with open(os.path.join(fixture, "README.md"), "w") as handle:
            handle.write("# fx\n")
        with open(os.path.join(fixture, ".env"), "w") as handle:
            handle.write("STRIPE_SECRET_KEY=sk_live_should_never_be_read\n")

        # Agent config with a symlinked skill store, a cycle and an escape.
        # This is the regression guard for the undercount that shipped: the
        # general walk does not follow symlinks, so a linked skill was
        # invisible to de-duplication and to the maturity classification.
        os.makedirs(os.path.join(fixture, ".claude", "skills", "local"))
        with open(os.path.join(fixture, ".claude", "skills", "local", "SKILL.md"), "w") as handle:
            handle.write("---\nname: local\n---\n")
        os.makedirs(os.path.join(fixture, "store", "shared"))
        with open(os.path.join(fixture, "store", "shared", "SKILL.md"), "w") as handle:
            handle.write("---\nname: shared\n---\n")
        os.makedirs(os.path.join(fixture, ".claude", "skills", "docs-only"))
        with open(os.path.join(fixture, ".claude", "skills", "docs-only", "README.md"), "w") as handle:
            handle.write("no SKILL.md here\n")
        links_made = True
        try:
            os.symlink(os.path.join("..", "..", "store", "shared"),
                       os.path.join(fixture, ".claude", "skills", "linked"))
            os.symlink(os.path.join("..", ".."),
                       os.path.join(fixture, ".claude", "skills", "loop"))
            os.symlink(os.sep, os.path.join(fixture, ".claude", "skills", "escape"))
        except (OSError, NotImplementedError, AttributeError):
            links_made = False

        buffer = io.StringIO()
        saved = sys.stdout
        try:
            sys.stdout = buffer
            code = main(["--repo", fixture, "--timeout-s", "5"])
        finally:
            sys.stdout = saved
        raw = buffer.getvalue()
        add("synthetic repo run exits 0", code == 0, str(code))
        try:
            result = json.loads(raw)
        except ValueError as exc:
            result = {}
            add("synthetic repo emits one JSON object", False, "%s | %r" % (exc, raw[:120]))
        else:
            add("synthetic repo emits one JSON object", raw.count("\n") == 1, str(raw.count("\n")))
        add(
            "manifest scripts are resolved into commands",
            result.get("commands", {}).get("test") != "",
            str(result.get("commands", {})),
        )
        add(
            "env var NAMES are captured, values never are",
            "STRIPE_SECRET_KEY" in (result.get("env_var_names") or [])
            and "sk_live_should_never_be_read" not in raw,
            str(result.get("env_var_names")),
        )
        add(
            "walk counts files and language lines",
            result.get("repo", {}).get("file_count", 0) >= 3
            and any(l.get("name") for l in (result.get("languages") or [])),
            "files=%s langs=%s"
            % (result.get("repo", {}).get("file_count"), [l.get("name") for l in (result.get("languages") or [])]),
        )
        config = result.get("existing_agentic_config") or {}
        found_skills = config.get("skills") or []
        joined_warnings = " | ".join(result.get("warnings") or [])
        add(
            "symlinked skills are followed and counted",
            (not links_made)
            or (sorted(found_skills) == ["linked", "local"]
                and config.get("counts", {}).get("skills") == 2),
            "skills=%s" % (sorted(found_skills),),
        )
        add(
            "symlinked skills are marked so the plan can name them",
            (not links_made)
            or any(entry.startswith(".claude/skills/linked ->")
                   for entry in (config.get("symlinked") or {}).get("skills") or []),
            str((config.get("symlinked") or {}).get("skills")),
        )
        add(
            "symlink cycles and out-of-tree targets are refused",
            (not links_made)
            or ("symlink cycle" in joined_warnings
                and "resolved outside the repo" in joined_warnings),
            joined_warnings[:160],
        )
        add(
            "a skill directory with no SKILL.md is reported, not counted",
            "docs-only" not in found_skills and "docs-only" in joined_warnings,
            joined_warnings[:160],
        )
    finally:
        shutil.rmtree(fixture, ignore_errors=True)

    # -- provenance, index-doc de-duplication, codex MCP ---------------------
    # Three measured defects, each with its own regression guard.  Pure
    # functions first (cheap and exact), then one fixture that exercises all
    # three end to end.
    names, parsed_ok = parse_codex_mcp_servers(
        "project_doc_max_bytes = 32768\n"
        "\n[features]\nhooks = true\n"
        "\n[mcp_servers.dodo-knowledge]\n"
        'command = "npx"\n'
        "args = [\n"
        '    "-y",\n'
        '    "mcp-remote@latest",\n'
        '    "https://knowledge.example.com/mcp",\n'
        "]\n"
        "\n[mcp_servers.linear]\nurl = \"https://mcp.linear.app/mcp\"\n"
        "\n[mcp_servers.linear.tools.create_issue]\nenabled = true\n"
    )
    add(
        "codex config.toml MCP servers are read, arrays are not section headers",
        names == ["dodo-knowledge", "linear", "linear"] and parsed_ok,
        "%s ok=%s" % (names, parsed_ok),
    )
    bad_names, bad_ok = parse_codex_mcp_servers("mcp_servers = { a = { url = 1 } }\n")
    add(
        "an unparseable mcp_servers block reports itself instead of empty",
        bad_ok is False,
        "%s ok=%s" % (bad_names, bad_ok),
    )
    add(
        "vendor and plugin-cache paths are recognised, a shared store is not",
        _is_vendor_path("/x/node_modules/y")
        and _is_vendor_path("/h/.claude/plugins/cache/acme/skills/s")
        and not _is_vendor_path("/repo/.agents/skills/own-skill"),
        "",
    )
    add(
        "a third-party doc hint needs the name to match the installed package",
        _third_party_doc_hint("better-auth-best-practices", "run npm install better-auth now")
        and not _third_party_doc_hint("landing-page-genius", "run npm install better-auth now"),
        "",
    )

    fixture2 = tempfile.mkdtemp(prefix="agentify-discover-provenance-")
    try:
        with open(os.path.join(fixture2, "package.json"), "w") as handle:
            handle.write('{"name":"fx2","scripts":{"test":"vitest run"}}')
        with open(os.path.join(fixture2, "AGENTS.md"), "w") as handle:
            handle.write("# index\n")
        with open(os.path.join(fixture2, "skills-lock.json"), "w") as handle:
            handle.write('{"version":1,"skills":{"vendor-a":{"source":"acme/skills"},'
                         '"vendor-b":{"source":"acme/skills"}}}')
        os.makedirs(os.path.join(fixture2, ".codex"))
        with open(os.path.join(fixture2, ".codex", "config.toml"), "w") as handle:
            handle.write('[mcp_servers.only-on-codex]\ncommand = "npx"\n'
                         'args = [\n  "-y",\n  "x",\n]\n')
        with open(os.path.join(fixture2, ".mcp.json"), "w") as handle:
            handle.write('{"mcpServers":{"only-on-claude":{"url":"https://e.co/mcp"}}}')
        for skill, body in (
            ("vendor-a", "---\nname: vendor-a\n---\n# a\n"),
            ("vendor-b", "---\nname: vendor-b\n---\n# b\n"),
            ("vendor-c", "---\nname: vendor-c\nsource: https://github.com/acme/skills\n---\n# c\n"),
            ("ours", "---\nname: ours\ndescription: deploy this repo\n---\n# ours\n"),
        ):
            os.makedirs(os.path.join(fixture2, ".claude", "skills", skill))
            with open(os.path.join(fixture2, ".claude", "skills", skill, "SKILL.md"), "w") as handle:
                handle.write(body)
        index_linked = True
        try:
            os.symlink("AGENTS.md", os.path.join(fixture2, "CLAUDE.md"))
        except (OSError, NotImplementedError, AttributeError):
            index_linked = False

        buffer = io.StringIO()
        saved = sys.stdout
        try:
            sys.stdout = buffer
            code2 = main(["--repo", fixture2, "--timeout-s", "5"])
        finally:
            sys.stdout = saved
        try:
            result2 = json.loads(buffer.getvalue())
        except ValueError:
            result2 = {}
        config2 = result2.get("existing_agentic_config") or {}
        prov = config2.get("provenance") or {}
        warn2 = " | ".join(result2.get("warnings") or [])
        add(
            "provenance run exits 0",
            code2 == 0 and bool(config2),
            str(code2),
        )
        add(
            "vendored skills are excluded from maturity but kept for de-duplication",
            (prov.get("vendored", {}).get("skills") == 3
             and prov.get("own", {}).get("skills") == 1
             and config2.get("counts", {}).get("skills") == 4
             and len(config2.get("skills") or []) == 4),
            "vendored=%s own=%s counts=%s"
            % (prov.get("vendored"), prov.get("own"), config2.get("counts")),
        )
        add(
            "four skills that are three vendored are not reported as mature",
            config2.get("maturity") != "mature",
            str(config2.get("maturity")),
        )
        docs2 = config2.get("index_docs") or []
        add(
            "a symlinked index doc is listed once, under the real file",
            (not index_linked)
            or (len(docs2) == 1 and docs2[0].get("path") == "AGENTS.md"
                and docs2[0].get("aliases") == ["CLAUDE.md"]
                and "SAME file" in warn2),
            str(docs2),
        )
        by_source = config2.get("mcp_servers_by_source") or []
        add(
            "MCP servers are read from both targets and carry their source",
            (sorted(config2.get("mcp_servers") or []) == ["only-on-claude", "only-on-codex"]
             and any(r.get("target") == "codex"
                     and r.get("file") == ".codex/config.toml"
                     and r.get("name") == "only-on-codex" for r in by_source)
             and "NOT in .mcp.json" in warn2),
            str(by_source),
        )
    finally:
        shutil.rmtree(fixture2, ignore_errors=True)

    # -- Codex target discovery ---------------------------------------------
    # Every claim below was verified against codex-cli 0.152.1 on 2026-09-05.
    # The first two checks are the security property: `config.toml` on a real
    # machine holds a live bearer token, and the ONLY thing this script may
    # take out of that file is names, section headers and three allowlisted
    # keys.  `_FAKE_TOKEN` stands in for the real one so the guard runs
    # anywhere.
    _FAKE_TOKEN = "phx_" + ("Z9" * 14)
    _hostile_toml = (
        'model = "gpt-5.1-codex-max"\n'
        'notify = ["say", "done"]\n'
        "\n[features]\nhooks = true\nmulti_agent = true\n"
        "\n[hooks]\n[[hooks.PreToolUse]]\nmatcher = \"^Bash$\"\n"
        "\n[mcp_servers.posthog]\n"
        'url = "https://mcp.posthog.com/mcp"\n'
        'http_headers = { Authorization = "Bearer %s" }\n'
        "\n[mcp_servers.node_repl]\n"
        'command = "node_repl"\n'
        "\n[mcp_servers.node_repl.env]\n"
        'OPENAI_API_KEY = "sk-%s"\n'
        '\n[projects."/tmp/agentify-fixture"]\ntrust_level = "trusted"\n'
        '\n[projects."/tmp/other"]\ntrust_level = "untrusted"\n'
        '\n[plugins."posthog@claude-plugins-official"]\nenabled = true\n'
        "\n[marketplaces.caveman]\n"
        'source = "https://github.com/example/caveman"\n'
        'project_doc_fallback_filenames = ["CLAUDE.md"]\n'
    ) % (_FAKE_TOKEN, _FAKE_TOKEN)

    _facts = parse_codex_config_facts(_hostile_toml, "/tmp/agentify-fixture")
    _facts_text = emitlib.serialize(_facts)
    _names, _names_ok = parse_codex_mcp_servers(_hostile_toml)
    add(
        "no config.toml value outside the allowlist can reach the output",
        (_FAKE_TOKEN not in _facts_text
         and "Bearer" not in _facts_text
         and "sk-" not in _facts_text
         and "OPENAI_API_KEY" not in _facts_text
         and "mcp.posthog.com" not in _facts_text
         and _FAKE_TOKEN not in " ".join(str(n) for n in _names)),
        _facts_text[:200],
    )
    add(
        "the allowlisted Codex facts ARE read: trust, features, hooks, plugins",
        (_facts["repo_trust_level"] == "trusted"
         and _facts["features"].get("hooks") is True
         and _facts["features"].get("multi_agent") is True
         and _facts["has_hooks_table"] is True
         and _facts["projects_declared"] == 2
         and _facts["claude_md_fallback"] is True
         and "posthog@claude-plugins-official" in _facts["plugins"]
         and "caveman" in _facts["marketplaces"]),
        _facts_text[:240],
    )
    add(
        "a repo that is NOT the one named in [projects.*] gets no trust_level",
        parse_codex_config_facts(_hostile_toml, "/tmp/somewhere-else")["repo_trust_level"] == "",
        "",
    )
    add(
        "Codex hooks.json parses on the same three-level shape as Claude Code",
        parse_hook_block({
            "PreToolUse": [{"matcher": "^Bash$", "hooks": [
                {"type": "command", "command": ".codex/hooks/guard.sh",
                 "timeout": 5}]}],
            "PostToolUse": [{"matcher": "^(apply_patch|Edit|Write)$", "hooks": [
                {"type": "mcp_tool", "server": "scanner", "tool": "scan_patch"}]}],
        }) == ["PreToolUse:^Bash$:.codex/hooks/guard.sh",
               "PostToolUse:^(apply_patch|Edit|Write)$:mcp_tool scanner.scan_patch"],
        str(parse_hook_block({"PreToolUse": [{"hooks": [{"command": "x"}]}]})),
    )

    fixture4 = tempfile.mkdtemp(prefix="agentify-discover-codex-")
    try:
        with open(os.path.join(fixture4, "package.json"), "w") as handle:
            handle.write('{"name":"fx4","scripts":{"test":"bun test"}}')
        with open(os.path.join(fixture4, "AGENTS.md"), "w") as handle:
            handle.write("# index\n")
        os.makedirs(os.path.join(fixture4, ".codex", "agents"))
        os.makedirs(os.path.join(fixture4, ".codex", "rules"))
        os.makedirs(os.path.join(fixture4, ".codex", "hooks"))
        os.makedirs(os.path.join(fixture4, ".codex", "skills", "stale-skill"))
        os.makedirs(os.path.join(fixture4, ".agents", "skills", "deploy-api"))
        os.makedirs(os.path.join(fixture4, ".codex-plugin"))
        with open(os.path.join(fixture4, ".codex", "config.toml"), "w") as handle:
            handle.write(_hostile_toml)
        with open(os.path.join(fixture4, ".codex", "hooks.json"), "w") as handle:
            handle.write(json.dumps({"hooks": {"PreToolUse": [
                {"matcher": "^Bash$", "hooks": [
                    {"type": "command",
                     "command": ".codex/hooks/block-destructive.sh"}]}]}}))
        with open(os.path.join(fixture4, ".codex", "hooks",
                               "block-destructive.sh"), "w") as handle:
            handle.write("#!/bin/sh\nexit 0\n")
        with open(os.path.join(fixture4, ".codex", "rules",
                               "agentify.rules"), "w") as handle:
            handle.write('prefix_rule(pattern=["npm"], decision="forbidden")\n')
        with open(os.path.join(fixture4, ".codex", "agents",
                               "pr-reviewer.toml"), "w") as handle:
            handle.write('name = "pr-reviewer"\ndescription = "review"\n'
                         'developer_instructions = "review the diff"\n')
        with open(os.path.join(fixture4, ".codex", "skills", "stale-skill",
                               "SKILL.md"), "w") as handle:
            handle.write("---\nname: stale-skill\ndescription: x\n---\n# x\n")
        with open(os.path.join(fixture4, ".agents", "skills", "deploy-api",
                               "SKILL.md"), "w") as handle:
            handle.write("---\nname: deploy-api\ndescription: deploy\n---\n# d\n")
        with open(os.path.join(fixture4, ".codex-plugin", "plugin.json"), "w") as handle:
            handle.write('{"name":"fx4-plugin","version":"1.0.0","skills":"./skills/"}')

        buffer = io.StringIO()
        saved = sys.stdout
        try:
            sys.stdout = buffer
            code4 = main(["--repo", fixture4, "--timeout-s", "10"])
        finally:
            sys.stdout = saved
        raw4 = buffer.getvalue()
        try:
            result4 = json.loads(raw4)
        except ValueError:
            result4 = {}
        config4 = result4.get("existing_agentic_config") or {}
        rows4 = config4.get("artifacts_by_target") or []
        codex4 = config4.get("codex") or {}
        warn4 = " | ".join(result4.get("warnings") or [])

        def _row(kind, name):
            return [r for r in rows4
                    if r.get("kind") == kind and name in (r.get("names") or [])]

        add(
            "a repo carrying a live-shaped config.toml leaks no credential",
            (code4 == 0 and bool(config4)
             and _FAKE_TOKEN not in raw4
             and "Bearer" not in raw4
             and "OPENAI_API_KEY" not in raw4
             and "sk-" not in raw4),
            str(code4),
        )
        add(
            "Codex repo artifacts are found: skill, subagent, rules, hooks, plugin",
            (bool(_row("skills", "deploy-api"))
             and bool(_row("agents", "pr-reviewer"))
             and bool(_row("rules", ".codex/rules/agentify.rules"))
             and any(r.get("kind") == "hooks" and r.get("target") == "codex"
                     for r in rows4)
             and bool(_row("plugin", "fx4-plugin"))),
            str(sorted((r["kind"], r["target"]) for r in rows4)),
        )
        add(
            "every artifact names the target that loads it",
            (all(r.get("target") in ("claude-code", "codex", "shared", "cursor",
                                     "copilot", "git") for r in rows4)
             and _row("agents", "pr-reviewer")[0]["target"] == "codex"
             and _row("skills", "deploy-api")[0]["target"] == "shared"
             and _row("plugin", "fx4-plugin")[0]["target"] == "codex"
             and all(r.get("count", 0) >= len(r.get("names") or [])
                     for r in rows4)),
            str([(r["kind"], r["target"], r["count"]) for r in rows4][:6]),
        )
        add(
            ".agents/skills is the repo skills root and .codex/skills is inert",
            (codex4.get("skills_root") == ".agents/skills"
             and "stale-skill" in (config4.get("skills") or [])
             and "NOT a Codex skills root" in warn4),
            "%s %s" % (codex4.get("skills_root"), config4.get("skills")),
        )
        add(
            "project trust and the hooks feature flag are reported",
            (codex4.get("repo_trust_level") in ("", "trusted", "untrusted")
             and codex4.get("features", {}).get("hooks") is True
             and codex4.get("hook_files")
             and codex4.get("hook_scripts")),
            emitlib.serialize(codex4)[:200],
        )
        add(
            "an untrusted repo is warned about, because every artifact is inert",
            ("trust_level gates AGENTS.md" in warn4
             or codex4.get("repo_trust_level") in ("trusted", "verified")),
            warn4[:160],
        )
        add(
            "user-scope Codex config is reported but never fed into maturity",
            (isinstance(config4.get("user_scope"), dict)
             and config4["counts"]["skills"] == 2
             and config4.get("maturity") in ("basic", "mature")
             and all(r.get("scope") == "user"
                     for r in (config4.get("mcp_servers_by_source") or [])
                     if str(r.get("file", "")).endswith("~/.codex/config.toml"))),
            "counts=%s user=%s" % (config4.get("counts"),
                                   (config4.get("user_scope") or {}).get("counts")),
        )
    finally:
        shutil.rmtree(fixture4, ignore_errors=True)

    # -- commands are resolved, never synthesized ----------------------------
    # The measured regression: `typescript` in devDependencies produced
    # `commands.typecheck = "npx tsc --noEmit"`, a string absent from the repo,
    # while two real `check:type:*` scripts went unreported.  This fixture is
    # that repo in miniature.
    add(
        "a dependency alone never fills a slot",
        _score_name("typecheck", ["ci"], SLOT_NAME_TOKENS[2][1], SLOT_NAME_TOKENS[2][2]) == 0
        and _body_slot("tsc -p tsconfig.ts.json")[0] == "typecheck"
        and _body_slot("npm run other")[0] is None,
        str(_body_slot("tsc -p tsconfig.ts.json")),
    )
    add(
        "the first token owns the name: build:types is a build, not a typecheck",
        _STRONG_OWNER.get("build") == "build" and _STRONG_OWNER.get("types") == "typecheck",
        "",
    )
    fixture3 = tempfile.mkdtemp(prefix="agentify-discover-commands-")
    try:
        with open(os.path.join(fixture3, "package.json"), "w") as handle:
            handle.write(
                '{"name":"fx3","scripts":{'
                '"check:type":"npm run check:type:js && npm run check:type:ts",'
                '"check:type:ts":"tsc -p tsconfig.ts.json",'
                '"check:type:js":"tsc -p tsconfig.js.json",'
                '"test":"node --test"},'
                '"devDependencies":{"typescript":"5.4.0","prettier":"3.0.0"}}'
            )
        with open(os.path.join(fixture3, "index.js"), "w") as handle:
            handle.write("module.exports = 1;\n")
        buffer = io.StringIO()
        saved = sys.stdout
        try:
            sys.stdout = buffer
            main(["--repo", fixture3, "--timeout-s", "5"])
        finally:
            sys.stdout = saved
        raw3 = buffer.getvalue()
        result3 = json.loads(raw3)
        cmds3 = result3.get("commands") or {}
        prov3 = (result3.get("raw_scripts") or {}).get(COMMAND_PROVENANCE_KEY) or {}
        warn3 = " | ".join(result3.get("warnings") or [])
        add(
            "typecheck resolves to the real script, and --noEmit is never invented",
            cmds3.get("typecheck") == "npm run check:type" and "noEmit" not in raw3,
            str(cmds3),
        )
        add(
            "a slot with no manifest entry stays empty and says so",
            cmds3.get("build") == "" and cmds3.get("lint") == ""
            and "commands.build" in warn3 and "never invent a command" in warn3,
            warn3[:160],
        )
        add(
            "prettier is a dependency with no entry, so it is reported not run",
            "no command was derived from them: prettier" in warn3,
            warn3[:200],
        )
        add(
            "every filled slot cites its manifest and key",
            all(prov3.get(slot) and "package.json" in prov3[slot]
                for slot in cmds3 if cmds3[slot]),
            str(prov3),
        )
        add(
            "both other typecheck scripts are reported, not silently dropped",
            "check:type:js" in prov3.get("typecheck", "")
            and "check:type:ts" in prov3.get("typecheck", ""),
            prov3.get("typecheck", ""),
        )
    finally:
        shutil.rmtree(fixture3, ignore_errors=True)

    # -- the package manager, and the install slot ---------------------------
    # Three measured misses, each one reaching a generated CLAUDE.md as an
    # instruction to the user's agent:
    #   vercel/turborepo            packageManager "pnpm@12.0.0", root
    #                               pnpm-lock.yaml, 20+ fixture bun.locks ->
    #                               resolved as bun, `bun install`.
    #   anthropics/claude-code-action
    #                               `install-hooks` scored 78 for the install
    #                               slot on its first token -> `bun run
    #                               install-hooks` as the dependency install.
    #   hostshare/ravisojitra       bun.lock at the root, package-lock.json in
    #                               a nested package.
    def _score(slot, name):
        for row_slot, strong, weak in SLOT_NAME_TOKENS:
            if row_slot == slot:
                return _score_name(slot, _name_tokens(name), strong, weak)
        return None

    add(
        "an arbitrary noun after a slot token rejects the name outright",
        _score("install", "install-hooks") == 0
        and _score("build", "build-docs") == 0
        and _score("test", "test-setup") == 0
        and _score("lint", "lint-staged") == 0
        and _score("build", "build:turbo") == 0,
        "install-hooks=%s build-docs=%s test-setup=%s lint-staged=%s build:turbo=%s"
        % (_score("install", "install-hooks"), _score("build", "build-docs"),
           _score("test", "test-setup"), _score("lint", "lint-staged"),
           _score("build", "build:turbo")),
    )
    add(
        "a recognized qualifier still matches, so real variants survive",
        _score("test", "test:watch") > 0
        and _score("typecheck", "check:type:ts") > 0
        and _score("format", "fix:format") > 0
        and _score("lint", "lint:fix") > 0
        and _score("test", "test") == 100,
        "test:watch=%s check:type:ts=%s fix:format=%s lint:fix=%s"
        % (_score("test", "test:watch"), _score("typecheck", "check:type:ts"),
           _score("format", "fix:format"), _score("lint", "lint:fix")),
    )

    def _pm_fixture(label, files):
        """Build a throwaway repo, run main(), return (payload, provenance)."""
        base = tempfile.mkdtemp(prefix="agentify-discover-pm-")
        try:
            for rel, body in files.items():
                full = os.path.join(base, rel.replace("/", os.sep))
                parent = os.path.dirname(full)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent)
                with open(full, "w") as handle:
                    handle.write(body)
            buf = io.StringIO()
            keep = sys.stdout
            try:
                sys.stdout = buf
                main(["--repo", base, "--timeout-s", "5"])
            finally:
                sys.stdout = keep
            payload = json.loads(buf.getvalue())
            return payload, (payload.get("raw_scripts") or {}).get(
                COMMAND_PROVENANCE_KEY) or {}
        finally:
            shutil.rmtree(base, ignore_errors=True)

    declared, declared_prov = _pm_fixture("declared", {
        "package.json": '{"name":"fx4","packageManager":"pnpm@12.0.0",'
                        '"scripts":{"install-hooks":"bun run hooks.sh"}}',
        "bun.lock": '{"lockfileVersion":1}\n',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'\n",
        "index.js": "module.exports = 1;\n",
    })
    add(
        "packageManager outranks every lockfile, stray ones included",
        (declared.get("package_managers") or [""])[0] == "pnpm"
        and declared["commands"]["install"] == "pnpm install"
        and "packageManager" in declared_prov.get("install", ""),
        "%s | %s" % (declared.get("package_managers"),
                     declared_prov.get("install", "")),
    )
    add(
        "no script named install-* can fill the install slot",
        "install-hooks" not in declared_prov.get("install", "")
        and "install-hooks" not in declared["commands"]["install"],
        declared_prov.get("install", ""),
    )

    nested, nested_prov = _pm_fixture("nested", {
        "package.json": '{"name":"fx5","scripts":{"test":"vitest run"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'\n",
        "lockfile-tests/fixtures/bun-basic/bun.lock": '{"lockfileVersion":1}\n',
        "lockfile-tests/fixtures/bun-basic/package.json": '{"name":"fixture"}',
        "examples/with-yarn/yarn.lock": "# yarn lockfile v1\n",
        "index.js": "module.exports = 1;\n",
    })
    add(
        "a lockfile under a fixture or example tree never decides",
        nested["commands"]["install"] == "pnpm install"
        and "bun" not in (nested.get("package_managers") or [])
        and "yarn" not in (nested.get("package_managers") or [])
        and nested["commands"]["test"] == "pnpm run test",
        "%s | %s" % (nested.get("package_managers"), nested["commands"]["install"]),
    )

    ambiguous, _ambiguous_prov = _pm_fixture("ambiguous", {
        "package.json": '{"name":"fx6","scripts":{"test":"vitest run"}}',
        "pnpm-lock.yaml": "lockfileVersion: '9.0'\n",
        "package-lock.json": '{"lockfileVersion":3}\n',
        "index.js": "module.exports = 1;\n",
    })
    add(
        "two root lockfiles and no declaration leaves install EMPTY, not guessed",
        ambiguous["commands"]["install"] == ""
        and any("ambiguous" in w for w in ambiguous.get("warnings") or []),
        "install=%r" % ambiguous["commands"]["install"],
    )

    add(
        "a chained body characterizes nothing and matches nothing",
        _body_slot("deno task lint && deno fmt --check && deno task test")[0] is None
        and _body_slot("rm -rf dist && tsc -p .")[0] is None
        and _body_slot("cargo build --package turbo")[0] == "build"
        and _body_slot("python -m pytest --cov=src tests")[0] == "test",
        "chain=%s single=%s" % (
            _body_slot("deno task lint && deno fmt --check")[0],
            _body_slot("cargo build --package turbo")[0]),
    )

    deno_repo, deno_prov = _pm_fixture("deno", {
        "deno.json": '{"tasks":{"test":"deno test -A",'
                     '"lint":"deno lint && deno task lint:x",'
                     '"lint:tools-types":"deno check _tools/*.ts",'
                     '"build:crypto":"deno task --cwd crypto wasmbuild"}}',
        "crypto/_wasm/Cargo.toml": '[package]\nname = "w"\n',
        "mod.ts": "export const x = 1;\n",
    })
    add(
        "a nested sub-crate never fills a slot with a root toolchain command",
        "cargo" not in deno_repo["commands"]["test"]
        and deno_repo["commands"]["test"] == "deno task test"
        and deno_repo["commands"]["install"] == "deno install"
        and deno_repo["commands"]["build"] == "",
        str(deno_repo["commands"]),
    )
    add(
        "a body match may confirm the name's slot, never overrule it",
        deno_repo["commands"]["typecheck"] == ""
        and "lint:tools-types" not in str(deno_prov),
        "typecheck=%r" % deno_repo["commands"]["typecheck"],
    )

    # -- justfiles: a detected manifest that used to parse to nothing -------
    # Measured on a fresh clone of simonw/llm: `manifests` listed
    # {"path": "Justfile", "kind": "justfile"}, `raw_scripts` had no entry for
    # it, and commands.test / lint / typecheck came back empty on a repo whose
    # Justfile defines exactly those recipes -- because every one of its nine
    # recipes opens with `@`, which the old signature pattern did not allow.
    just_text = "\n".join([
        "# comment",
        'set shell := ["bash", "-uc"]',
        'version := "1.0"',
        "alias t := test",
        "",
        "@default: test lint",
        "",
        "@test *options:",
        "  uv run pytest {{options}}",
        "",
        "lint: build",
        "  #!/usr/bin/env bash",
        "  set -euo pipefail",
        "  @ruff check .",
        "",
        "[private]",
        "helper:",
        "  echo hidden",
        "",
        "_fmt:",
        "  black .",
        "",
        "deploy target:",
        "  ./deploy.sh {{target}}",
        "",
        'docs port="8000": lint',
        "\tcd docs && make html",
        "",
        "build:",
        "\ttsc -p .",
        "",
        "test-setup:",
        "  ./fixtures.sh",
        "",
    ])
    just_repo, just_prov = _pm_fixture("just", {
        "Justfile": just_text,
        "pyproject.toml": '[project]\nname = "fx7"\nversion = "0.1"\n',
        "main.py": "x = 1\n",
    })
    just_cmds = just_repo.get("commands") or {}
    just_raw = (just_repo.get("raw_scripts") or {}).get("Justfile") or {}
    just_warn = " | ".join(just_repo.get("warnings") or [])
    add(
        "a justfile fills slots -- `@` prefix, parameters and dependencies included",
        just_cmds.get("test") == "just test"
        and just_cmds.get("lint") == "just lint"
        and just_cmds.get("build") == "just build"
        and "Justfile#test" in just_prov.get("test", ""),
        "%s | %s" % (just_cmds, just_prov.get("test", "")),
    )
    add(
        "a recipe that cannot run bare is never offered as a command",
        "deploy" not in just_raw and "just deploy" not in str(just_repo)
        and "required parameters (deploy)" in just_warn,
        "raw=%s" % sorted(just_raw),
    )
    add(
        "a private recipe is skipped, and the skip is reported not dropped",
        "_fmt" not in just_raw and "helper" not in just_raw
        and just_cmds.get("format") == ""
        and "private recipe(s) (helper, _fmt)" in just_warn,
        just_warn[-260:],
    )
    add(
        "a shebang recipe reports its first real command, not its `#!` line",
        just_raw.get("lint") == "ruff check ."
        and just_raw.get("docs") == "cd docs && make html"
        and just_raw.get("default") == "",
        str(just_raw)[:200],
    )
    add(
        "a justfile recipe obeys the qualifier gate like every other name",
        "test-setup" in just_raw and "test-setup" not in just_prov.get("test", ""),
        just_prov.get("test", ""),
    )

    both, both_prov = _pm_fixture("just+package.json", {
        "package.json": '{"name":"fx8","scripts":{"test":"node --test"}}',
        "package-lock.json": '{"lockfileVersion":3}\n',
        "justfile": "@test:\n  pytest\n\n@build:\n  tsc -p .\n",
        "index.js": "module.exports = 1;\n",
    })
    add(
        "package.json outranks the justfile, which still fills what it leaves empty",
        both["commands"]["test"] == "npm run test"
        and both["commands"]["build"] == "just build"
        and "package.json" in both_prov.get("test", "")
        and "justfile#build" in both_prov.get("build", ""),
        "%s | %s" % (both["commands"]["test"], both["commands"]["build"]),
    )

    # -- degraded paths all exit 0 -------------------------------------------
    degraded_ok = True
    degraded_detail = []
    for label, path in (
        ("missing", os.path.join(fixture, "gone")),
        ("file", os.path.abspath(__file__)),
        ("devnull", os.devnull),
    ):
        buffer = io.StringIO()
        saved = sys.stdout
        try:
            sys.stdout = buffer
            code = main(["--repo", path])
        except SystemExit as exit_error:  # pragma: no cover - must not happen
            code = exit_error.code
        finally:
            sys.stdout = saved
        try:
            parsed = json.loads(buffer.getvalue())
        except ValueError:
            parsed = {}
        if code != 0 or not parsed.get("warnings"):
            degraded_ok = False
        degraded_detail.append("%s=%s" % (label, code))
    add("degraded repo paths exit 0 with warnings", degraded_ok, " ".join(degraded_detail))

    # -- monorepo: two workspace systems, scoped YAML, honest cap ------------
    # Every check below is a defect that shipped, measured on a real clone of
    # vercel/turborepo: sibling YAML keys leaking into the workspace list, a
    # `tool` naming a different system from the `workspaces` beside it, a
    # "no globs were parsed" warning on a run that parsed eleven, and a read
    # cap spent in walk order that left every workspace package.json unparsed.
    mono = tempfile.mkdtemp(prefix="agentify-discover-mono-")
    try:
        def write(rel, body):
            full = os.path.join(mono, rel.replace("/", os.sep))
            parent = os.path.dirname(full)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent)
            with open(full, "w") as handle:
                handle.write(body)

        write("pnpm-workspace.yaml",
              'packages:\n'
              '  - apps/*\n'
              '  - packages/*\n'
              '  - "!packages/private"\n'
              '\n'
              'minimumReleaseAgeExclude:\n'
              '  - next\n'
              '  - "@vercel/geistdocs"\n'
              '\n'
              'onlyBuiltDependencies:\n'
              '  - esbuild\n')
        write("Cargo.toml",
              '[workspace]\n'
              'resolver = "2"\n'
              'members = [\n'
              '  "crates/one",\n'
              '  "crates/two*",\n'
              ']\n')
        write("turbo.json", '{"tasks": {"build": {}}}\n')
        write("pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
        write("package.json", '{"name":"root","scripts":{"test":"vitest run"}}')
        # 70 crates in an alphabetically EARLY directory against 8 workspace
        # packages in a late one, together past MAX_MANIFEST_READS: walk order
        # alone hands every slot to crates and parses no package.json at all.
        for index in range(70):
            write("crates/two%02d/Cargo.toml" % index,
                  '[package]\nname = "two%02d"\n' % index)
        for index in range(8):
            write("packages/p%d/package.json" % index,
                  '{"name":"p%d","scripts":{"build":"tsc -p ."}}' % index)
        write("packages/private/package.json", '{"name":"private"}')

        buffer = io.StringIO()
        saved = sys.stdout
        try:
            sys.stdout = buffer
            mono_code = main(["--repo", mono, "--timeout-s", "10"])
        finally:
            sys.stdout = saved
        try:
            mono_out = json.loads(buffer.getvalue())
        except ValueError as exc:
            mono_out = {}
            add("monorepo fixture emits one JSON object", False, str(exc))
        block = mono_out.get("monorepo", {})
        globs = block.get("workspaces", [])
        systems = block.get("systems", [])
        by_tool = dict((s.get("tool"), s) for s in systems)
        scripts = mono_out.get("raw_scripts", {})

        add("monorepo fixture run exits 0", mono_code == 0, str(mono_code))
        add("pnpm `packages:` is read without its sibling YAML keys",
            "apps/*" in globs and "packages/*" in globs
            and not [g for g in globs if g in ("next", "@vercel/geistdocs", "esbuild")],
            str(globs))
        add("a negated glob becomes an exclude, never an include",
            "packages/private" in block.get("excludes", [])
            and not [g for g in globs if g.startswith("!")],
            str(block.get("excludes")))
        add("both workspace systems are reported, each with its own globs",
            sorted(block.get("tools", [])) == ["cargo", "pnpm"]
            and by_tool.get("pnpm", {}).get("manifest") == "pnpm-workspace.yaml"
            and by_tool.get("cargo", {}).get("manifest") == "Cargo.toml",
            str([(s.get("tool"), s.get("manifest")) for s in systems]))
        add("a multi-line cargo `members = [` array is parsed",
            by_tool.get("cargo", {}).get("workspaces") == ["crates/one", "crates/two*"],
            str(by_tool.get("cargo", {}).get("workspaces")))
        add("the task runner is its own layer, not the workspace tool",
            [t.get("name") for t in block.get("task_runners", [])] == ["turborepo"]
            and block.get("tool") == "pnpm+turborepo",
            "%s %s" % (block.get("tool"), block.get("task_runners")))
        add("no 'globs were not parsed' warning on a run that parsed them",
            not [w for w in mono_out.get("warnings", [])
                 if "no workspace globs were parsed" in w],
            str([w for w in mono_out.get("warnings", []) if "workspace" in w])[:160])
        add("the read cap does not let one prolific kind starve another",
            len([k for k in scripts if k.startswith("packages/p")]) == 8,
            "%d of 8 workspace package.json parsed"
            % len([k for k in scripts if k.startswith("packages/p")]))
        add("what the cap skipped is reported, not silently dropped",
            bool([w for w in mono_out.get("warnings", [])
                  if "manifest reads capped at" in w]),
            str([w for w in mono_out.get("warnings", [])
                 if "manifest reads capped" in w])[:200])

        # A nested declaration must never inflate the root block.
        write("packages/p0/package.json",
              '{"name":"p0","workspaces":["sub/*","other/*"]}')
        buffer = io.StringIO()
        saved = sys.stdout
        try:
            sys.stdout = buffer
            main(["--repo", mono, "--timeout-s", "10"])
        finally:
            sys.stdout = saved
        try:
            nested_out = json.loads(buffer.getvalue())
        except ValueError:
            nested_out = {}
        nested_globs = nested_out.get("monorepo", {}).get("workspaces", [])
        add("a nested package.json's workspaces never reach the root block",
            "sub/*" not in nested_globs and "other/*" not in nested_globs
            and bool([w for w in nested_out.get("warnings", [])
                      if "below the repo root declare workspace members" in w]),
            str(nested_globs))
    finally:
        shutil.rmtree(mono, ignore_errors=True)

    # -- the 2026-09-07 riffads shape: services, zones, docs and samples the
    # old tables left invisible, so phase 4 had nothing to walk against ------
    shape, _shape_prov = _pm_fixture("shape", {
        "package.json": '{"name":"fx7","scripts":{"dev":"next dev"},'
                        '"dependencies":{"next":"14.0.0","@dodopayments/better-auth":"1.0.0",'
                        '"@trigger.dev/sdk":"4.0.0","@fal-ai/client":"1.0.0"}}',
        "trigger.config.ts": "export default {};\n",
        "components.json": '{"style":"new-york"}',
        ".env.example": "TRIGGER_SECRET_KEY=\nDODO_PAYMENTS_API_KEY=\nFAL_KEY=\nR2_BUCKET_NAME=\n",
        "app/layout.tsx": "export default function L(){return null}\n",
        "app/(protected)/page.tsx": "export default function P(){return null}\n",
        "app/api/health/route.ts": "export const GET = () => new Response('ok');\n",
        "trigger/tasks/render.ts": "export const render = {};\n",
        ".claude/hooks/guard.sh": "#!/bin/sh\nexit 0\n",
        "components/ui/button.tsx": "export const Button = () => null;\n",
        "components/composer/dock.tsx": "export const Dock = () => null;\n",
        "db/migrations/0001_init.sql": "select 1;\n",
        "db/migrations/0002_users.sql": "select 2;\n",
        "DESIGN.md": "# Design\n\n## Anti-patterns\n- no raw hex\n",
        "CONTEXT.md": "# Glossary\n",
        "docs/guides/adding-a-capability.md": "# Adding a capability\n1. do\n2. verify\n",
        "docs/roadmap.md": "# Roadmap\n",
    })
    svc = dict((row["name"], row) for row in shape.get("external_services") or [])
    add(
        "dodo, trigger.dev and fal are services in their own right (dep + env + config file)",
        "dodo" in svc and "trigger.dev" in svc and "fal" in svc
        and svc["trigger.dev"]["confidence"] == "high"
        and any(e.startswith("file:trigger.config") for e in svc["trigger.dev"]["evidence"])
        and "cloudflare" in svc,
        str(sorted(svc.keys())),
    )
    fw = set(f["name"] for f in shape.get("frameworks") or [])
    add("components.json marks shadcn/ui", "shadcn/ui" in fw and "Next.js" in fw, str(sorted(fw)))
    zones = dict((row["path"], row) for row in shape.get("folders") or [])
    add(
        "app is `routes` under Next.js, app/api stays `api`, trigger/tasks is `jobs`, "
        ".claude/hooks is null",
        zones.get("app", {}).get("zone") == "routes"
        and zones.get("app/api", {}).get("zone") == "api"
        and zones.get("trigger/tasks", {}).get("zone") == "jobs"
        and zones.get("trigger", {}).get("zone") == "jobs"
        and zones.get(".claude/hooks", {}).get("zone") is None
        and zones.get("components", {}).get("zone") == "components",
        str([(p, r.get("zone")) for p, r in sorted(zones.items())][:12]),
    )
    add(
        "folders carry sample_files and subdirs read off the tree",
        zones.get("db/migrations", {}).get("sample_files") == ["0001_init.sql", "0002_users.sql"]
        and "ui" in (zones.get("components", {}).get("subdirs") or [])
        and "(protected)" in (zones.get("app", {}).get("subdirs") or []),
        "%s | %s" % (zones.get("db/migrations", {}).get("sample_files"),
                     zones.get("components", {}).get("subdirs")),
    )
    kinds = dict((d["path"], d["kind"]) for d in shape.get("docs") or [])
    add(
        "DESIGN.md, CONTEXT.md and docs/guides/* get their own doc kinds",
        kinds.get("DESIGN.md") == "design" and kinds.get("CONTEXT.md") == "context"
        and kinds.get("docs/guides/adding-a-capability.md") == "guide"
        and kinds.get("docs/roadmap.md") == "other",
        str(sorted(kinds.items())),
    )
    add(
        "tooling.on_path is a list of PATH binaries, names only",
        isinstance((shape.get("tooling") or {}).get("on_path"), list)
        and all(isinstance(n, str) and "/" not in n for n in shape["tooling"]["on_path"]),
        str((shape.get("tooling") or {}).get("on_path")),
    )
    warn_text = " ".join(shape.get("warnings") or [])
    add(
        "no warning tells the model to de-duplicate against vendored or user-scope entries",
        "DO count for de-duplication" not in warn_text
        and "de-duplicate against them (A9)" not in warn_text,
        warn_text[:120],
    )

    return emitlib.selftest_report(TOOL, checks, started_ms=started)


if __name__ == "__main__":
    sys.exit(emitlib.main_guard(main, TOOL))
