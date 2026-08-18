from __future__ import annotations
import argparse
from studyforge.backup import export_backup, inspect_backup


def main():
    parser=argparse.ArgumentParser(description='Esporta un backup portabile di Tutor LLM.')
    parser.add_argument('destination', nargs='?', default=None)
    args=parser.parse_args()
    path=export_backup(args.destination)
    print(path)
    print(inspect_backup(path))

if __name__=='__main__':
    main()
