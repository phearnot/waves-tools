import sys

import requests


def is_asset_pair(tx, asset):
    return (tx['order1']['assetPair']['amountAsset'] == asset
            or tx['order2']['assetPair']['priceAsset'] == asset)


PRICE_CONSTANT = 100000000
ALIASES = []
DECIMALS = 8


def is_alias(alias):
    for a in ALIASES:
        if a in alias:
            return True
    return False


def balance_change(tx, address, asset, sponsor):
    direction = ""
    amount = 0
    fee = 0
    if ('feeAsset' in tx and tx['feeAsset'] == asset) or ('feeAssetId' in tx and tx['feeAssetId'] == asset):
        fee = tx['fee']
    if tx['type'] == 3 and tx['id'] == asset:
        amount = tx['quantity']
    elif tx['type'] == 4 and tx['assetId'] == asset:
        if tx['sender'] == address:
            amount -= tx['amount']
        if tx['recipient'] == address or is_alias(tx['recipient']):
            amount += tx['amount']
    elif tx['type'] == 5 and tx['amount'] == asset:
        amount = tx['quantity']
    elif tx['type'] == 6 and tx['amount'] == asset:
        amount = -tx['quantity']
    elif tx['type'] == 7 and is_asset_pair(tx, asset):
        if tx['order1']['sender'] == address:
            order = tx['order1']
            if order['orderType'] == 'buy':
                direction = '+'
                if order['assetPair']['priceAsset'] == asset:
                    amount += -int(tx['price'] * tx['amount'] / PRICE_CONSTANT)
                else:
                    amount += tx['amount']
            else:
                direction = '-'
                if order['assetPair']['priceAsset'] == asset:
                    amount += int(tx['price'] * tx['amount'] / PRICE_CONSTANT)
                else:
                    amount += -tx['amount']
        if tx['order2']['sender'] == address:
            order = tx['order2']
            if order['orderType'] == 'buy':
                if direction == '':
                    direction = '+'
                else:
                    direction = '='
                if order['assetPair']['priceAsset'] == asset:
                    amount += -int(tx['price'] * tx['amount'] / PRICE_CONSTANT)
                else:
                    amount += tx['amount']
            else:
                if direction == '':
                    direction = '-'
                else:
                    direction = '='
                if order['assetPair']['priceAsset'] == asset:
                    amount += int(tx['price'] * tx['amount'] / PRICE_CONSTANT)
                else:
                    amount += -tx['amount']
    elif tx['type'] == 10 and tx['sender'] == address:  # create alias
        ALIASES.append(tx['alias'])
    elif tx['type'] == 11 and tx['assetId'] == asset:
        if tx['sender'] == address:
            amount = -tx['totalAmount']
        else:
            for t in tx['transfers']:
                if t['recipient'] == address or is_alias(t['recipient']):
                    amount += t['amount']
    elif tx['type'] == 14 and tx['assetId'] == asset:
        sponsor = True
    elif tx['type'] == 16:
        if tx['payment'] and tx['payment'][0]['assetId'] == asset:
            if tx['sender'] == address:
                amount -= tx['payment'][0]['amount']
            if tx['dApp'] == address:
                amount += tx['payment'][0]['amount']
        for p in tx['stateChanges']['transfers']:
            if p['address'] == address and p['asset'] == asset:
                amount += p['amount']
            if tx['dApp'] == address and p['asset'] == asset:
                amount -= p['amount']

    if sponsor:
        if 'sender' in tx and tx['sender'] == address:
            fee = 0
    else:
        if 'sender' in tx and tx['sender'] != address:
            fee = 0

    if 'sender' in tx and tx['sender'] == address:
        direction = '-'
        total = amount - fee
    elif 'recipient' in tx and (tx['recipient'] == address or is_alias(tx['recipient'])):
        direction = '+'
        total = amount + fee
    else:
        total = fee

    return \
        tx['timestamp'], \
        tx['height'], \
        tx['id'], \
        direction, \
        amount, \
        fee, \
        tx['type'], \
        total, \
        sponsor


def arrange(n):
    return n / pow(10, DECIMALS)


def total_balance(txs):
    balance = 0
    for ts, height, tx_id, direction, amount, fee, tx_type, total, sponsor in txs:
        balance += total
        yield height, tx_id, tx_type, arrange(amount), arrange(fee), direction, arrange(total), arrange(
            balance), sponsor


def load_all_transactions(node, address):
    all_transactions = []
    loaded_transactions = requests.get(
        f'{node}/debug/stateChanges/address/{address}/limit/1000'
    ).json()

    while loaded_transactions:
        print(f'Loaded {len(loaded_transactions)} more transaction(s)')
        all_transactions.extend(loaded_transactions)
        loaded_transactions = requests.get(
            f'{node}/debug/stateChanges/address/{address}/limit/1000?after={loaded_transactions[-1]["id"]}'
        ).json()

    print(f'Loaded a total of {len(all_transactions)} transaction(s)')

    return all_transactions


def transfer_asset(transfers, asset):
    for t in transfers:
        if t['asset'] == asset:
            return True
    return False


def has_asset(tx, asset):
    return 'feeAsset' in tx and tx['feeAsset'] == asset or 'feeAssetId' in tx and tx['feeAssetId'] == asset \
           or tx['id'] == asset or 'assetId' in tx and tx['assetId'] == asset \
           or tx['type'] == 7 and is_asset_pair(tx, asset) \
           or tx['type'] == 16 and tx['payment'] and tx['payment'][0]['assetId'] == asset \
           or tx['type'] == 16 and transfer_asset(tx['stateChanges']['transfers'], asset)


def calculate_balance_changes():
    node = sys.argv[1]
    address = sys.argv[2]
    asset = sys.argv[3]
    transactions = load_all_transactions(node, address)
    if transactions:
        balance_changes = []
        sponsor = False
        for t in sorted(transactions, key=lambda x: (x['height'], x['timestamp'])):
            if has_asset(t, asset) or t['type'] == 10:
                ch = balance_change(t, address, asset, sponsor)
                sponsor = ch[8]
                balance_changes.append(ch)

        print('  Height ID                                            TX '
              '                  Amount '
              '                     Fee '
              'D '
              '                   Total '
              '                 Balance S')

        count = 0
        for bc in total_balance(balance_changes):
            print('{:8} {:45} {:2} {:24,.8f} {:24,.8f} {:1} {:24,.8f} {:24,.8f} {:1}'.format(*bc))
            count += 1

        print("Transactions: ", count)
    else:
        print(transactions)


if __name__ == '__main__':
    calculate_balance_changes()
