from __future__ import annotations
import argparse
from studyforge.backup import import_backup, inspect_backup


def main():
    parser=argparse.ArgumentParser(description='Ripristina un backup Tutor LLM. Eseguire a servizi fermati.')
    parser.add_argument('archive')
    parser.add_argument('--replace', action='store_true', help='Sostituisce i dati esistenti.')
    args=parser.parse_args()
    print(inspect_backup(args.archive))
    print(import_backup(args.archive, replace=args.replace))

if __name__=='__main__':
    main()
