from sys import argv

import requests


def load_all_state_changes(node, address, max_height):
    all_script_invocations = []
    loaded_transactions = requests.get(
        f'http://{node}/transactions/address/{address}/limit/1000'
    ).json()[0]

    while loaded_transactions:
        print(f'Loaded {len(loaded_transactions)} more transaction(s), total: {len(all_script_invocations)}')
        all_script_invocations.extend(t for t in loaded_transactions if int(t['height']) <= max_height and t['type'] == 16)
        loaded_transactions = requests.get(
            f'http://{node}/transactions/address/{address}/limit/1000?after={loaded_transactions[-1]["id"]}'
        ).json()[0]

    print(f'Loaded a total of {len(all_script_invocations)} transaction(s)')


if __name__ == '__main__':
    load_all_state_changes(argv[1], argv[2], int(argv[3]))
