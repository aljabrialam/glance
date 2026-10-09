# Glance: setup (do this first)

## 1. Create the folder and repo

```bash
mkdir glance && cd glance
git init
mkdir -p docs design backend frontend scripts
```

If you unzipped glance-starter.zip, the folder, docs/ and design/ already
exist: `cd glance && git init && mkdir -p backend frontend scripts`.

## 2. Files and where they go

```
glance/
├── SETUP.md
├── docs/
│   ├── context.md              # product + Reap/Kwal API facts
│   ├── scope-lock.md           # what is in and out today, timeline
│   ├── sdd-runsheet.md         # how we build: per-spec workflow, gates
│   └── constitution-prompt.md  # the /speckit-constitution paste block
├── design/
│   ├── glance-app-mockup.html     # UI reference, becomes the frontend
│   └── glance-product-film.html   # glasses concept film
├── backend/
├── frontend/                   # React Native (Expo) app
└── scripts/
```

## 3. Keep secrets out of git

```bash
cat > .gitignore <<'EOT'
.env
.env.*
!.env.example
__pycache__/
.venv/
node_modules/
credentials.json
EOT

cat > .env.example <<'EOT'
REAP_API_KEY=
REAP_VERSION=
REAP_BASE_URL=https://sandbox.api.reap.global
REAP_ENROLLMENT_ID=
OPENAI_API_KEY=
PUBLIC_BASE_URL=
VAULT_BALANCE=250.00
EOT

cp .env.example .env   # then fill in the real values
```

## 4. Install Spec Kit for Devin

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify integration list            # confirm "devin" is listed
specify init . --integration devin
```

Run `specify init` once only. Re-running it overwrites files.

## 5. First commit

```bash
git add -A && git commit -m "chore: initialize glance with docs, design and spec kit"
```

## 6. First message to Devin

```
Read docs/context.md, docs/scope-lock.md and docs/sdd-runsheet.md.
The scope lock overrides the other two. Follow the run sheet: run the
constitution block in docs/constitution-prompt.md, then Spec 001, and
stop at G1 for my approval. Do not write code before G2 is approved.
```

## 7. Human job while Devin reads

Get the card enrollment to ACTIVE (docs/context.md, "One-time setup") and
put its id in REAP_ENROLLMENT_ID. Nothing else works without it.
