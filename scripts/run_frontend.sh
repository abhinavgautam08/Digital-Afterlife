#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../frontend" && pwd)"
cd "$DIR"

echo "Starting Digital Afterlife Frontend (Vite on http://127.0.0.1:5173)..."
npm run dev

