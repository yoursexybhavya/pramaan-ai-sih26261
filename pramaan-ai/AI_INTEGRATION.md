# Safe AI integration

PRAMAAN-AI does not use copied or hard-coded API keys. The supported modes
are:

| Mode | Configuration | Key | Role |
|---|---|---|---|
| Rules-only | `AI_PROVIDER=disabled` | None | Default and always available |
| Local Ollama | `AI_PROVIDER=ollama` | None for local server | Advisory claim suggestions |
| Groq hosted | `AI_PROVIDER=groq`, `GROQ_API_KEY` | User-owned Groq key | Advisory claim suggestions |
| OpenRouter free router | `AI_PROVIDER=openrouter`, `OPENROUTER_API_KEY` | User-owned OpenRouter key | Advisory claim suggestions |
| Cerebras hosted | `AI_PROVIDER=cerebras`, `CEREBRAS_API_KEY` | User-owned Cerebras key | Advisory claim suggestions |
| Any OpenAI-compatible endpoint | `AI_PROVIDER=openai_compatible` plus `PRAMAAN_AI_BASE_URL`, `PRAMAAN_AI_MODEL`, `PRAMAAN_AI_API_KEY` | User-owned server secret | Advisory claim suggestions |

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

## Online provider setup

Choose one provider and add its key only to the server environment:

```bash
# Groq: free developer access, fast open-weight models
export AI_PROVIDER=groq
export GROQ_API_KEY='your-key-from-console.groq.com'

# Or OpenRouter: use the free-model router; keep the key budget-limited
export AI_PROVIDER=openrouter
export OPENROUTER_API_KEY='your-key-from-openrouter.ai'

# Or Cerebras: trial credits may be available for a new account
export AI_PROVIDER=cerebras
export CEREBRAS_API_KEY='your-key-from-cloud.cerebras.ai'
```

The names and free quotas are provider-controlled and can change. Do not
paste keys into the browser, GitHub, screenshots or this repository. For
official issuer integrations, use DigiLocker/API Setu partner onboarding and
sandbox credentials; those are separate from an LLM key.
