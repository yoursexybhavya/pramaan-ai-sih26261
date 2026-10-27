# Safe AI integration

PRAMAAN-AI does not use copied or hard-coded API keys. The supported modes
are:

| Mode | Configuration | Key | Role |
|---|---|---|---|
| Rules-only | `AI_PROVIDER=disabled` | None | Default and always available |
| Local Ollama | `AI_PROVIDER=ollama` | None for local server | Advisory claim suggestions |
| Hosted compatible endpoint | `AI_PROVIDER=openai_compatible` plus `PRAMAAN_AI_BASE_URL`, `PRAMAAN_AI_MODEL`, `PRAMAAN_AI_API_KEY` | User-owned server secret | Advisory claim suggestions |

Check the current mode after login at `GET /api/ai/status`. The API never
returns secret values. Model suggestions are marked advisory and do not alter
APH hard gates or human decisions.

## Local example

```bash
ollama pull gemma3:4b
export AI_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=gemma3:4b
cd pramaan-app && ./run.sh
```

For official issuer integrations, use DigiLocker/API Setu partner onboarding
and sandbox credentials. Do not use anonymous keys found online.
