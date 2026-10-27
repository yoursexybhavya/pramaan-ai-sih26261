# AGENTS.md — Workspace Guidelines for PRAMAAN-AI (SIH26261)

## CRITICAL RULES FOR ALL AGENTS

1. **DO NOT USE WEB SEARCH**:
   - The `websearch` tool is rate-limited (HTTP 429) upstream.
   - **NEVER** call `websearch` under any circumstances.
   - All documentation, logic, schemas, and libraries exist locally in this workspace.

2. **NEVER TRY TO SCRAPE OR SEARCH FOR PRIVATE API KEYS**:
   - Private API keys (Groq, Gemini, Mistral, OpenRouter) are secret user credentials that cannot be found online.
   - Do not search for keys online.
   - When asked about API keys, explain how the user can set their own environment variable (e.g. `export GROQ_API_KEY=...` or `export GEMINI_API_KEY=...`) or use the safe fallback in `pramaan-app/app/ai.py`.

3. **AVOID UNNECESSARY SUBAGENTS**:
   - Complete tasks directly in the main session.
   - Do not spawn subagents unless explicitly asked.

4. **MAINTAINING A "GOOD SESSION" (6/6 Checklist)**:
   - Make concrete file edits in `pramaan-app/` (`code changed`).
   - Run verification commands via the bash tool (`ran or tested`):
     ```bash
     cd pramaan-app && .venv/bin/python3 -c "import app.main; print('PRAMAAN-AI OK')"
     ```
   - Zero tool errors (`few errors`).
   - Deliver real, working code artifacts (`real work`).

## REPOSITORY CONTEXT
- **Application Directory:** `pramaan-app/`
- **FastAPI Entrypoint:** `pramaan-app/app/main.py`
- **AI Provider Adapter:** `pramaan-app/app/ai.py` (Supports Groq, Gemini, Mistral, OpenRouter, Cerebras, Ollama)
- **Reviewer Dashboard:** `pramaan-app/app/static/index.html`
- **Launcher:** `pramaan-app/run.sh`
