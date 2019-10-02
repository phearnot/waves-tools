import sys

import base58
import pywaves.crypto as crypto
import requests


def pubkey_to_address(pubkey):
    pubkey_bytes = base58.b58decode(pubkey)
    unhashed_address = chr(1) + str('L') + crypto.hashChain(pubkey_bytes)[0:20]
    address_hash = crypto.hashChain(crypto.str2bytes(unhashed_address))[0:4]
    return base58.b58encode(crypto.str2bytes(unhashed_address + address_hash))


def is_waves_pair(tx):
    return (tx['order1']['assetPair']['amountAsset'] is None
            or tx['order2']['assetPair']['priceAsset'] is None)


KNOWN_LEASES = {}

PRICE_CONSTANT = 100000000


def balance_change(tx, address):
    is_sender = tx['type'] != 1 and tx['sender'] == address
    is_fee_in_waves = ('feeAsset' not in tx) or (tx['feeAsset'] is None)
    fee_in_waves = is_sender and (is_fee_in_waves and tx['fee'] or 0) or 0
    # print('{}: is_fee_in_waves={}, feeAsset={}, fee={}'.format(tx['id'], is_fee_in_waves,
    #    'feeAsset' in tx and tx['feeAsset'] or None, fee_in_waves))
    lease_out = 0
    amount = 0
    if tx['type'] == 4 and tx['assetId'] is None:
        if tx['sender'] == address:
            amount = -tx['amount']
        else:
            amount = tx['amount']
    elif tx['type'] == 7 and is_waves_pair(tx):
        our_order = pubkey_to_address(tx['order1']['senderPublicKey']) == address and tx['order1'] or tx['order2']
        if our_order['orderType'] == 'buy':
            fee_in_waves = tx['buyMatcherFee']
            if our_order['assetPair']['priceAsset'] is None:
                amount = -int(tx['price'] * tx['amount'] / PRICE_CONSTANT)
            else:
                amount = tx['amount']
        else:
            fee_in_waves = tx['sellMatcherFee']
            if our_order['assetPair']['priceAsset'] is None:
                amount = int(tx['price'] * tx['amount'] / PRICE_CONSTANT)
            else:
                amount = -tx['amount']
    elif tx['type'] == 8 and tx['sender'] == address:
        lease_out = tx['amount']
        KNOWN_LEASES[tx['id']] = tx
    elif tx['type'] == 9 and tx['leaseId'] in KNOWN_LEASES:
        lease_out = -KNOWN_LEASES[tx['leaseId']]['amount']
    elif tx['type'] == 1:
        amount = tx['amount']
    else:
        amount = 0
    return tx['height'], tx['timestamp'], tx['id'], is_sender and '[>' or '>]', fee_in_waves, tx[
        'type'], amount - fee_in_waves, lease_out


def total_balance(txs):
    total_lease = 0
    total_amount = 0
    for height, ts, tx_id, sender, fee_in_waves, tx_type, amount, lease_out in txs:
        total_lease += lease_out
        total_amount += amount
        yield height, tx_id, tx_type, fee_in_waves, sender, amount, total_amount, lease_out, total_lease, total_amount - lease_out


def load_all_transactions(address):
    all_transactions = []
    loaded_transactions = requests.get(
        f'http://nodes.wavesnodes.com/transactions/address/{address}/limit/1000'
    ).json()[0]

    while loaded_transactions:
        print(f'Loaded {len(loaded_transactions)} more transaction(s)')
        all_transactions.extend(loaded_transactions)
        loaded_transactions = requests.get(
            f'http://nodes.wavesnodes.com/transactions/address/{address}/limit/1000?after={loaded_transactions[-1]["id"]}'
        ).json()[0]

    print(f'Loaded a total of {len(all_transactions)} transaction(s)')

    return all_transactions


def calculate_balance_changes():
    address = sys.argv[1]
    transactions = load_all_transactions(address)
    if transactions:
        balance_chages = [balance_change(t, address) for t in sorted(transactions, key=lambda x: x['height'])]
        for bc in total_balance(balance_chages):
            print('{:6} {:45} {} {:8d} {} {:12d} {:12d} {:12d} {:12d}'.format(*bc))
    else:
        print(transactions)


if __name__ == '__main__':
    calculate_balance_changes()
