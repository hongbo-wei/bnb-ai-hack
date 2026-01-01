#!/usr/bin/env python
import argparse

from eth_abi import encode
from web3 import Web3


def build_transfer_call_data(to_address: str, amount: int) -> str:
    if amount < 0:
        raise ValueError("amount must be >= 0")
    if not Web3.is_address(to_address):
        raise ValueError("invalid recipient address")
    selector = Web3.keccak(text="transfer(address,uint256)")[:4]
    encoded_args = encode(["address", "uint256"], [Web3.to_checksum_address(to_address), amount])
    return "0x" + (selector + encoded_args).hex()


def main() -> None:
    parser = argparse.ArgumentParser(description="Encode ERC20 transfer calldata.")
    parser.add_argument("--to", required=True, help="Recipient address (0x...)")
    parser.add_argument("--amount", required=True, help="Token amount in base units")
    args = parser.parse_args()

    amount = int(args.amount)
    call_data = build_transfer_call_data(args.to, amount)
    print(call_data)


if __name__ == "__main__":
    main()
