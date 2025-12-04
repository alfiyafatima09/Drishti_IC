# Wails Desktop App (Frontend Only)

This folder contains the full desktop application: **Go + Wails + React + Vite + TypeScript**, all isolated inside `frontend/`.

## Prerequisites

- **Go** 1.21+ installed
- **Wails CLI** installed
- **Bun** installed

```bash
# Check versions
go version
wails version
bun --version
```

## Install Wails CLI

```bash
go install github.com/wailsapp/wails/v2/cmd/wails@latest
export PATH="$PATH:$(go env GOPATH)/bin"
```

## Setup (from frontend folder)

```bash
cd frontend

# Install React/Vite/TS dependencies
bun install

# Download Go dependencies
go mod tidy
```

## Development

Run from inside `frontend/`:

```bash
cd frontend
wails dev
```

This will:
- Start the Vite dev server on port 34115 (configured in `vite.config.ts`)
- Launch the Wails desktop window
- Enable HMR for the React UI

## Build

```bash
cd frontend

# Build frontend assets
bun run build

# Build desktop binary
wails build
```

The built binary will appear under `build/bin` relative to `frontend/`.

## Key Files

- `frontend/app.go` — Go entrypoint for the Wails app
- `frontend/go.mod` — Go module for the desktop app
- `frontend/wails.json` — Wails configuration (points to this folder)
- `frontend/vite.config.ts` — Vite config (port + HMR)
- `frontend/src` — React + TypeScript UI


