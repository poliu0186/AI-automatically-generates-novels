#!/usr/bin/env python3
import argparse
import sys

from cryptography.fernet import Fernet


def build_parser():
    parser = argparse.ArgumentParser(description='Encrypt secrets for .env using Fernet')
    parser.add_argument('--generate-key', action='store_true', help='Generate a new Fernet key')
    parser.add_argument('--key', help='Fernet key used for encryption')
    parser.add_argument('--value', help='Plaintext value to encrypt')
    parser.add_argument('--stdin', action='store_true', help='Read plaintext from stdin')
    return parser


def main():
    args = build_parser().parse_args()

    if args.generate_key:
        print(Fernet.generate_key().decode('utf-8'))
        return 0

    if not args.key:
        print('ERROR: --key is required unless --generate-key is used', file=sys.stderr)
        return 1

    plaintext = args.value
    if args.stdin:
        plaintext = sys.stdin.read()

    if plaintext is None:
        print('ERROR: provide --value or --stdin', file=sys.stderr)
        return 1

    token = Fernet(args.key.encode('utf-8')).encrypt(plaintext.encode('utf-8')).decode('utf-8')
    print(f'ENC:{token}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
