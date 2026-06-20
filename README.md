# AI Backend — How It Works

This backend has two jobs:

1. **Avatar Chat** — the avatar in the app listens to what the child says/does and replies with something appropriate (in English or Urdu).

It's live and always-on at:

**`https://aibackend-production-35c9.up.railway.app/health`**

You can see and test every available endpoint here, with no setup needed:
**`https://aibackend-production-35c9.up.railway.app/docs`**

---

## How a request flows through the system

```
Flutter App  →  Backend  →  AI Service (Groq)
     ↑                              |
     └──────────────────────────────┘
            (response comes back)
```

The app never talks to Groq  directly — it always goes through this backend first. That's intentional: it keeps API keys and credentials private, and lets us change the AI logic without ever touching the app.

---

## The two features, explained simply

### 1. Avatar Chat (`/avatar/respond`)

**What happens:** the app sends what the child said or did → the backend figures out what they meant → asks Groq's AI to generate a reply in the avatar's voice → sends that reply (plus an Urdu version) back to the app.

**Why it's split into pieces internally** (for context, not something you need to touch):
- `intent_parser.py` — figures out *what kind of thing* the child is asking ("are they answering a game question? just saying hi? confused?")
- `prompt_builder.py` — builds the exact instructions sent to the AI so it stays in character
- `ai_service.py` — actually calls Groq and gets the reply back

---

## What's needed for this to keep running

| Requirement | Why |
|---|---|
| `GROQ_API_KEY` | Powers the avatar's replies. Without it, `/avatar/respond` fails. |
| Hosting (currently Railway) | Keeps the backend always-on, so the app works over normal wifi/data without needing a cable to a laptop. |

These are all set as private environment variables on Railway — never stored in the code itself, so they can't leak if the code is shared.

---


- **Railway dashboard → Deployments → click the latest one → Deploy Logs** shows exactly what error happened and when.
- `/health` endpoint should always return `{"status": "running"}` if the server itself is up. If that fails, the whole server is down.
- If only `/check`, `/content`, or `/progress` fail but everything else works, it's almost always a Firebase configuration issue, not a code issue.
