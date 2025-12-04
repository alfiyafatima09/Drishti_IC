# Drishti IC Frontend

Desktop application frontend built with React, Vite, and TypeScript for Wails.

## Tech Stack

- **React 19** - UI framework
- **Vite 7** - Build tool and dev server
- **TypeScript 5** - Type safety
- **Bun** - Package manager and runtime

## Development

### Prerequisites

- [Bun](https://bun.sh) installed
- [Wails CLI](https://wails.io/docs/gettingstarted/installation) installed

### Setup

```bash
# Install dependencies
bun install

# Start development server (for Wails)
# Run from project root: wails dev

# Or run Vite dev server standalone
bun run dev
```

### Build

```bash
# Build for production
bun run build
```

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx          # Main app component
│   ├── App.css          # App styles
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── index.html           # HTML template
├── vite.config.ts       # Vite configuration
├── tsconfig.json        # TypeScript configuration
└── package.json         # Dependencies and scripts
```

## Wails Integration

This frontend is configured to work with Wails desktop application framework. The Vite dev server is configured to run on port 34115 for Wails development mode.
