#!/bin/bash
# Avvia il Sistema Ausili
cd "$(dirname "$0")"

# Attiva ambiente virtuale se esiste
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Chiudi eventuali processi precedenti sulla porta 5001
PIDS=$(lsof -ti:5001 2>/dev/null)
if [ -n "$PIDS" ]; then
  echo "Chiudo processo precedente sulla porta 5001..."
  kill $PIDS 2>/dev/null
  sleep 1
fi

echo "=== Sistema Ausili SAPIO LIFE ==="
echo "Avvio in corso..."
echo ""
echo "  Apri nel browser: http://localhost:5001"
echo ""
echo "(premi Ctrl+C per fermare)"
echo ""

python3 app.py
