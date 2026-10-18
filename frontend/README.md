# Compass frontend

Vue 3 + Vite, with Pinia (state), vue-router (every screen has a URL), vue-i18n (all interface text in `src/locales/en.json`) and [Wikimedia Codex](https://doc.wikimedia.org/codex/) components and design tokens.

```bash
npm install
npm run dev      # http://localhost:5173, expects the backend on :5000
npm test         # vitest: store, URL sync, message keys
npm run build    # dist/; set VITE_API_BASE for a separate backend ("" = same origin)
```

How the store, router and API layer fit together: [Frontend State](../wiki/Frontend-State.md).
