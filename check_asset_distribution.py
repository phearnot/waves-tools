import sys

import requests


def current_height(node):
    response = requests.get(f'{node}/blocks/height').json()

    if response and 'height' in response:
        return response['height']
    else:
        return 0


def asset_info(node, asset):
    response = requests.get(f'{node}/assets/details/{asset}').json()
    if response:
        if 'decimals' in response and 'quantity' in response and 'name' in response:
            return response['name'], response['quantity'], response['decimals']


def load_distribution(node, asset, height):
    balances = {}
    response = requests.get(
        f'{node}/assets/{asset}/distribution/{height}/limit/999'
    ).json()

    while response:
        if 'items' in response:
            items = response['items']
            print(f'Loaded {len(items)} more balance(s)')
            balances.update(items)
        if 'hasNext' in response and response['hasNext'] is True:
            response = requests.get(
                f'{node}/assets/{asset}/distribution/{height}/limit/999?after={response["lastItem"]}'
            ).json()
        else:
            break
    print(f'Loaded a total of {len(balances)} balance(s)')

    return balances


def arrange(n, decimals):
    return n / pow(10, decimals)


def align(balance, decimals):
    print(balance)
    for key, value in balance.items():
        return key, arrange(value, decimals)
    return


def check_asset_distribution():
    node = sys.argv[1]
    asset = sys.argv[2]
    info = asset_info(node, asset)
    h = current_height(node) - 1
    decimals = info[2]
    quantity = arrange(info[1], decimals)
    distribution = load_distribution(node, asset, h)
    if distribution:
        total = 0
        print()
        print('Height\t\t: {:<8d}'.format(h))
        print('Asset\t\t: {}'.format(info[0]))
        print('Quantity\t: {:<24,.8f}'.format(quantity))
        print('Decimals\t: {:<1d}'.format(decimals))
        print()
        print('Account                                  '
              '                  Amount ')
        for account, balance in distribution.items():
            ab = arrange(balance, decimals)
            total += ab
            print('{:40} {:24,.8f}'.format(account, ab))

        print()
        print('Total                                    {:24,.8f}'.format(total))
        print('Quantity                                 {:24,.8f}'.format(quantity))
        diff = quantity - total
        print('Difference                               {:24,.8f}'.format(diff))
        print()
        if diff != 0:
            print('ERROR!!!')
        else:
            print('OK')
    else:
        print(distribution)


if __name__ == '__main__':
    check_asset_distribution()
