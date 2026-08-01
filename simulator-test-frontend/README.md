# KnowAct Simulator Test Standalone Frontend

[中文](README.zh-CN.md)

This is the participant-facing React/Vite application. It deliberately excludes
Knowledge Graph authoring, Episodes, Run Queue, agent scoring, and internal
result-inspection navigation.

## Participant flow

```text
enter, revise, and confirm Profile
  -> confirm personal Knowledge Map node by node
  -> sample 20 items from the backend-provided bilingual bank
  -> submit the human answer before revealing the Simulator answer
  -> complete five personal-fidelity ratings
  -> save or resume with a session code
```

At startup, the app reads the available domains, reviewed graphs, and bilingual
question banks from the backend and automatically selects the first compatible
set with at least 20 questions. The selected identities are persisted in the
session by the backend. The app never requests the collection of all sessions;
resume uses only a random `session_id` stored in the browser or entered by the
participant.

## Local development

From the repository root:

```bash
make simulator-test
```

The app defaults to `http://127.0.0.1:5174`, proxying `/api` to the backend at
`http://127.0.0.1:8000`. No local frontend environment file is required for
same-origin development. Copy `.env.example` to `.env.local` only when
overriding the public API origin, study title, provider, or default language.

## Independent build

```bash
npm --prefix simulator-test-frontend ci
npm --prefix simulator-test-frontend run build
```

Deploy the generated `simulator-test-frontend/dist/` as a standalone static
site, or use the supplied Dockerfile.

All `VITE_*` values are embedded in the browser bundle. Never put API keys or
other secrets in them.

## Backend connection

For same-origin deployment, leave `VITE_API_BASE_URL` empty and proxy `/api` to
the KnowAct backend.

For cross-origin deployment, set the public backend origin in
`VITE_API_BASE_URL` and add the exact participant-site origin to the backend
`KNOWACT_CORS_ORIGINS`. Wildcard CORS is rejected.

CORS is not authentication. A public backend should also use an API gateway or
reverse-proxy allowlist. Deny runtime, tested-agent, candidate-graph, and
session-collection routes; expose only the narrow Profile/Map calls used by
this app and the required single-session Simulator Test routes.

## Data boundary

- Provider API keys stay only in the backend `.env`.
- Participant code, Profile, Map, answers, and ratings are restricted data.
- Sessions and Map revisions are written under
  `experiments/02_simulator_human_validity/results/private/`.
- The browser stores only the random session resume code, not full answers.
- Expert blind rating remains a later, separate stage.
