#!/bin/bash
# Setup iniziale del Sistema Ausili
echo "=== Setup Sistema Ausili ==="

# Controlla se Python è disponibile
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON="$cmd"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo ""
  echo "❌ Python non trovato. Installa Python con:"
  echo "   brew install python"
  echo ""
  echo "Se Homebrew non è configurato, esegui prima:"
  echo '   eval "$(/opt/homebrew/bin/brew shellenv)"'
  echo ""
  exit 1
fi

echo "✅ Python trovato: $PYTHON ($($PYTHON --version))"

# Crea ambiente virtuale
if [ ! -d "venv" ]; then
  echo "Creo ambiente virtuale..."
  $PYTHON -m venv venv
fi

# Attiva venv e installa dipendenze
source venv/bin/activate
echo "Installo dipendenze..."
pip install -q --upgrade pip
pip install flask pypdf reportlab pdfrw pillow

echo ""
echo "✅ Setup completato!"
echo "Per avviare: bash avvia.sh"
