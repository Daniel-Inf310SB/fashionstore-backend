"""Ejecutar: python -m app.scripts.train_ml_demo [--output ruta.json]."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.ml.experiment import run_demo


def main():
    parser = argparse.ArgumentParser(description='Evaluación ML con datos sintéticos (sin usar PostgreSQL)')
    parser.add_argument('--output', default=None, help='Archivo JSON opcional de resultados')
    args = parser.parse_args()
    result = run_demo()
    output = json.dumps(result, indent=2, ensure_ascii=False)
    print(output)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output + '\n', encoding='utf-8')
        print(f'Resultados escritos en: {target}')


if __name__ == '__main__':
    main()
