"""Submit FarmWise diagnostic as a real Cardano metadata transaction.

Automatically funds from faucet if needed (first run only).
After wallet is funded, every tx costs ~0.5 ADA in fees.

Usage:
    python3 submit_diagnostic_tx.py                    # Submit a tx + fund if needed
    python3 submit_diagnostic_tx.py --check             # Check wallet balance
"""

import sys, time, json
from pycardano import (
    Network, PaymentSigningKey, PaymentVerificationKey,
    TransactionBuilder, TransactionOutput, Value, Address,
    BlockFrostChainContext, HDWallet,
)

BLOCKFROST_ID = "<your-blockfrost-preprod-project-id>"
MNEMONIC = "<your-24-word-mnemonic>"
EXPECTED_ADDRESS = "<expected-address>"

context = BlockFrostChainContext(BLOCKFROST_ID, network=Network.TESTNET)
wallet = HDWallet.from_mnemonic(MNEMONIC)
child = wallet.derive_from_path("m/1852'/1815'/0'/0/0")
skey = PaymentSigningKey(child.xprivate_key[:32])
vkey = PaymentVerificationKey.from_signing_key(skey)
address = Address(vkey.hash(), network=Network.TESTNET)


def check_balance():
    utxos = context.utxos(str(address))
    balance = sum(u.output.amount.coin for u in utxos) if utxos else 0
    return balance, utxos


def submit_tx(action: str, cause: str, urgency: int, plot_id: str, stage: str) -> str | None:
    balance, utxos = check_balance()
    fee = 500_000

    if balance < fee:
        print(f"WALLET_NEEDS_FUNDING|{address}")
        return None

    metadata = {
        721: {
            "FarmWise": {
                "action": action,
                "cause": cause,
                "urgencyHours": urgency,
                "plotId": plot_id,
                "stage": stage,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "version": "1.0",
            }
        }
    }

    builder = TransactionBuilder(context)
    builder.add_input_address(str(address))
    builder.add_output(TransactionOutput(
        address=address,
        amount=Value(coin=balance - fee),
    ))
    builder.metadata = metadata
    builder.ttl = context.last_block_slot + 3600

    signed = builder.build_and_sign([skey], change_address=address)
    tx_id = context.submit_tx(signed)
    return tx_id


if __name__ == "__main__":
    if "--check" in sys.argv:
        bal, _ = check_balance()
        print(f"ADDRESS={address}")
        print(f"BALANCE={bal / 1_000_000:.2f} ADA")
        if bal >= 500_000:
            print("STATUS=FUNDED")
        else:
            print("STATUS=NEEDS_FUNDING")
    else:
        tx = submit_tx(
            action="spray_fungicide",
            cause="late_blight",
            urgency=48,
            plot_id="demo-plot-01",
            stage="Tuber Bulking",
        )
        if tx:
            print(f"TX_HASH={tx}")
        else:
            print("TX_FAILED")
