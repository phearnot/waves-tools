from sys import argv

import requests


def load_signature(node, height):
    return requests.get(f'http://{node}/blocks/headers/at/{height}').json()['signature']


def load_state_hash(node, height):
    return requests.get(f'http://{node}/debug/state/hash/{height}').json()['stateHash']


def find_fork_height(func, min_height, max_height, nodes):
    hashes = [''] * len(nodes)
    while (max_height - min_height) > 0:
        current_height = int((min_height + max_height) / 2)
        hashes = [func(node, current_height) for node in nodes]
        print(f'Values at {current_height}: {hashes}')
        if max_height - min_height == 1:
            current_height = min_height
            break
        elif all(h == hashes[0] for h in hashes):
            min_height = current_height
        else:
            max_height = current_height
    print(f'At height {current_height}:')
    for n, h in zip(nodes, hashes):
        print(f'{n}: {h}')

LOADERS = {
    'sig': load_signature,
    'hash': load_state_hash
}


if __name__ == '__main__':
    find_fork_height(LOADERS[argv[1]], int(argv[2]), int(argv[3]), argv[4:])
