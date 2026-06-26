#!/bin/bash
# FarmWise Cardano Wallet Setup
# Automates funding the FarmWise wallet from the Cardano Preprod faucet.
#
# Usage:
#   bash setup_wallet.sh          # Check status + show funding instructions
#   bash setup_wallet.sh --fund   # Attempt automated funding via Blockfrost faucet
#   bash setup_wallet.sh --check  # Check balance only

set -e

BLOCKFROST_ID="<REDACTED_BLOCKFROST_ID>"
ADDRESS="<REDACTED_TESTNET_ADDRESS>"
FAUCET_URL="https://docs.cardano.org/cardano-testnet/tools/faucet"

check_balance() {
  local result
  result=$(curl -s "https://cardano-preprod.blockfrost.io/api/v0/addresses/$ADDRESS" \
    -H "project_id: $BLOCKFROST_ID" 2>/dev/null)
  
  local ada
  ada=$(echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
amounts = d.get('amount', [])
lovelace = next((a for a in amounts if a['unit'] == 'lovelace'), {'quantity': '0'})
print(f\"{int(lovelace['quantity']) / 1000000:.2f}\")
" 2>/dev/null || echo "0.00")
  
  echo "$ada"
}

case "${1:-}" in
  --check)
    BALANCE=$(check_balance)
    echo "Wallet: $ADDRESS"
    echo "Balance: $BALANCE ADA"
    ;;
  --fund)
    echo "Attempting to fund wallet via faucet..."
    echo "Note: The official Cardano faucet requires a captcha."
    echo "Opening the faucet website for you..."
    if command -v xdg-open &>/dev/null; then
      xdg-open "$FAUCET_URL" 2>/dev/null || true
    elif command -v open &>/dev/null; then
      open "$FAUCET_URL" 2>/dev/null || true
    fi
    echo ""
    echo "Manual steps:"
    echo "  1. Paste this address: $ADDRESS"
    echo "  2. Select 'Preprod Testnet'"
    echo "  3. Complete the captcha"
    echo "  4. Wait 30 seconds"
    echo ""
    echo "Then run: bash setup_wallet.sh --check"
    ;;
  *)
    BALANCE=$(check_balance)
    echo "==========================================="
    echo "  FarmWise Cardano Wallet"
    echo "==========================================="
    echo ""
    echo "  Address: $ADDRESS"
    echo "  Balance: $BALANCE ADA"
    echo ""
    
    if (( $(echo "$BALANCE >= 1.0" | bc -l 2>/dev/null || echo 0) )); then
      echo "  ✅ Wallet is funded! Real tx hashes will work."
      echo ""
      echo "  Next: Run the diagnostic endpoint to get a real Cardano tx hash."
    else
      echo "  ❌ Wallet needs funding from the Cardano faucet."
      echo ""
      echo "  To fund:"
      echo "    bash setup_wallet.sh --fund"
      echo ""
      echo "  Or visit:"
      echo "    $FAUCET_URL"
      echo "    Address: $ADDRESS"
    fi
    echo "==========================================="
    ;;
esac
