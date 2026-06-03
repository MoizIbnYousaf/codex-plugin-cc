---
description: Create, list, or send follow-up prompts to native Codex app-server threads
argument-hint: '<new|send|list> [--write] [--model <model|spark>] [--effort <none|minimal|low|medium|high|xhigh>] [--name <title>] [thread-id] [prompt]'
disable-model-invocation: true
allowed-tools: Bash(node:*)
---

Create and steer native Codex app-server threads through the shared plugin runtime.

Raw slash-command arguments:
`$ARGUMENTS`

Actions:
- `new [prompt]`: create a persistent Codex thread in the current repository and send the first prompt.
- `send <thread-id> [prompt]`: send a follow-up prompt to an existing Codex thread.
- `list`: show recent Codex app-server threads for the current repository.

Rules:
- Run the companion command exactly once.
- Return the command stdout verbatim, exactly as-is.
- Do not paraphrase, summarize, or add commentary before or after it.
- Use `--write` only when the user explicitly wants Codex to make edits. Otherwise the thread runs read-only.
- Leave `--model` and `--effort` unset unless the user explicitly asks for them.
- If the user asks for `spark`, pass it through as `--model spark`; the companion maps it to `gpt-5.3-codex-spark`.
- If the user asks to create a native Codex thread and gives no action, use `new`.
- If the user asks to continue an existing thread, use `send` with the thread id they provided.
- If the user asks what native Codex threads exist, use `list`.

Run:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" thread "$ARGUMENTS"
```
