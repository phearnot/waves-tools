import sys

import requests


def is_asset_pair(tx, asset):
    return (tx['order1']['assetPair']['amountAsset'] == asset
            or tx['order1']['assetPair']['priceAsset'] == asset)


PRICE_CONSTANT = 100000000
ALIASES = []


def is_alias(alias):
    for a in ALIASES:
        if a in alias:
            return True
    return False


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


def list_asset_transactions():
    node = sys.argv[1]
    address = sys.argv[2]
    asset = sys.argv[3]
    transactions = load_all_transactions(node, address)
    count = 0
    if transactions:
        for t in sorted(transactions, key=lambda x: (x['height'], x['timestamp'])):
            if has_asset(t, asset):
                count += 1
                print(t)
    else:
        print(transactions)
    print("Asset transaction: ", count)

if __name__ == '__main__':
    list_asset_transactions()
