#!/bin/bash
# Usage: set-mode.sh [deep-work|available|transit]
MODE="${1:-available}"
if [[ "$MODE" != "deep-work" && "$MODE" != "available" && "$MODE" != "transit" ]]; then
    echo "Usage: $0 [deep-work|available|transit]"
    exit 1
fi
echo "{\"mode\": \"$MODE\"}" > /home/jared/marlin/state.json
echo "Marlin mode: $MODE"
