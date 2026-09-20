#!/usr/bin/env python3
"""
Gerador de Dados Sintéticos para DyraSQL
Gera dados de teste para tabelas Apache Iceberg com volume configurável
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta


def generate_tenant_id():
    """Gera um tenant_id no formato T1, T2, ..., T50"""
    return f"T{random.randint(1, 50)}"


def generate_status():
    """Gera status ATIVO (90%) ou INATIVO (10%)"""
    return "ATIVO" if random.random() > 0.1 else "INATIVO"


def generate_valor():
    """Gera valor monetário entre 10.0 e 1000.0"""
    return round(random.uniform(10.0, 1000.0), 2)


def generate_date(start_date, num_days):
    """Gera uma data aleatória dentro do range especificado"""
    days_offset = random.randint(0, num_days - 1)
    date = start_date + timedelta(days=days_offset)
    return date.strftime("%Y-%m-%d")


def generate_document():
    """Gera um documento JSON sintético"""
    doc = {
        "origem": "sintetico",
        "versao": "1.0",
        "metadados": {
            "gerado_em": datetime.now().isoformat(),
            "tipo": random.choice(["A", "B", "C"]),
        },
    }
    return json.dumps(doc)


def generate_surrogate_key(index):
    """Gera uma chave única"""
    return f"SK{index:08d}"


def generate_insert_statements(
    num_records=180000,
    start_date="2024-01-01",
    num_days=90,
    batch_size=1000,
    output_file="load-iceberg-generated.sql",
):
    """
    Gera statements INSERT para a tabela dados

    Args:
        num_records: Número total de registros a gerar
        start_date: Data inicial para geração
        num_days: Número de dias no range de datas
        batch_size: Número de registros por batch INSERT
        output_file: Arquivo de saída
    """

    start = datetime.strptime(start_date, "%Y-%m-%d")

    print(f"Gerando {num_records:,} registros...")
    print(
        f"Range de datas: {start_date} até {(start + timedelta(days=num_days-1)).strftime('%Y-%m-%d')}"
    )
    print(f"Batch size: {batch_size:,} registros por INSERT")
    print(f"Arquivo de saída: {output_file}")
    print()

    with open(output_file, "w") as f:
        # Cabeçalho
        f.write("-- ======================================================================\n")
        f.write("-- Dados Sintéticos Gerados Automaticamente\n")
        f.write(f"-- Total de registros: {num_records:,}\n")
        f.write(
            f"-- Range de datas: {start_date} a {(start + timedelta(days=num_days-1)).strftime('%Y-%m-%d')}\n"
        )
        f.write(f"-- Gerado em: {datetime.now().isoformat()}\n")
        f.write("-- ======================================================================\n\n")

        # INSERT para tenant_info (50 registros)
        f.write("-- Inserindo dados de tenant_info\n")
        f.write("INSERT INTO iceberg.analytics.tenant_info VALUES\n")
        tenant_values = []
        for i in range(1, 51):
            categoria = ["A", "B", "C"][i % 3]
            nivel = (i % 10) + 1
            tenant_values.append(f"  ('T{i}', '{categoria}', {nivel})")
        f.write(",\n".join(tenant_values) + ";\n\n")

        # INSERT para dados (em batches)
        num_batches = (num_records + batch_size - 1) // batch_size

        for batch in range(num_batches):
            start_idx = batch * batch_size
            end_idx = min(start_idx + batch_size, num_records)
            print(
                f"Batch {batch + 1}/{num_batches}: Gerando registros {start_idx + 1:,} a {end_idx:,}...",
                end="\r",
            )

            f.write(f"-- Batch {batch + 1}/{num_batches}: Registros {start_idx + 1} a {end_idx}\n")
            f.write("INSERT INTO iceberg.analytics.dados VALUES\n")

            values = []
            for i in range(start_idx, end_idx):
                tenant_id = generate_tenant_id()
                status = generate_status()
                valor = generate_valor()
                date = generate_date(start, num_days)
                document = generate_document()
                surrogate_key = generate_surrogate_key(i + 1)

                # Formato: (tenant_id, status, valor, date, created_at, updated_at, document, surrogate_key)
                values.append(
                    f"  ('{tenant_id}', '{status}', {valor}, "
                    f"TIMESTAMP '{date} 00:00:00', "
                    f"localtimestamp, localtimestamp, "
                    f"'{document}', '{surrogate_key}')"
                )

            f.write(",\n".join(values) + ";\n\n")

        print()  # Nova linha após progresso
        print(f"\n✓ Arquivo gerado: {output_file}")
        print(f"✓ Total de registros: {num_records:,}")
        print(f"✓ Tamanho aproximado: ~{(num_records * 200) / (1024**2):.1f} MB")


def generate_large_dataset(output_file="load-iceberg-large.sql", size_gb=10):
    """
    Gera um dataset grande baseado no tamanho em GB

    Args:
        output_file: Arquivo de saída
        size_gb: Tamanho desejado em GB
    """
    # Estimativa: ~200 bytes por registro
    # 10 GB ≈ 52.428.800 registros
    bytes_per_gb = 1024**3
    bytes_per_record = 200
    num_records = int((size_gb * bytes_per_gb) / bytes_per_record)

    print(f"Gerando dataset de ~{size_gb} GB...")
    print(f"Estimativa de registros: {num_records:,}")
    print()

    generate_insert_statements(
        num_records=num_records,
        start_date="2024-01-01",
        num_days=365,
        batch_size=5000,
        output_file=output_file,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Gerador de Dados Sintéticos para DyraSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Gerar dataset padrão (180k registros)
  python generate_data.py

  # Gerar dataset customizado
  python generate_data.py --records 500000 --days 180 --batch 2000

  # Gerar dataset grande (10 GB)
  python generate_data.py --size-gb 10

  # Gerar dataset de 1 ano de dados
  python generate_data.py --records 1000000 --days 365 --start-date 2023-01-01
        """,
    )

    parser.add_argument(
        "--records",
        type=int,
        default=180000,
        help="Número total de registros a gerar (padrão: 180000)",
    )

    parser.add_argument(
        "--start-date",
        type=str,
        default="2024-01-01",
        help="Data inicial (formato YYYY-MM-DD, padrão: 2024-01-01)",
    )

    parser.add_argument(
        "--days", type=int, default=90, help="Número de dias no range de datas (padrão: 90)"
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=1000,
        help="Número de registros por batch INSERT (padrão: 1000)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="load-iceberg-generated.sql",
        help="Arquivo de saída (padrão: load-iceberg-generated.sql)",
    )

    parser.add_argument(
        "--size-gb", type=float, help="Gerar dataset baseado no tamanho em GB (ex: 10 para 10GB)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("DyraSQL - Gerador de Dados Sintéticos")
    print("=" * 70)
    print()

    if args.size_gb:
        generate_large_dataset(output_file=args.output, size_gb=args.size_gb)
    else:
        generate_insert_statements(
            num_records=args.records,
            start_date=args.start_date,
            num_days=args.days,
            batch_size=args.batch,
            output_file=args.output,
        )

    print()
    print("=" * 70)
    print("Para carregar os dados:")
    print(f"  trino --server http://localhost:8080 --user admin --file {args.output}")
    print("=" * 70)


if __name__ == "__main__":
    main()
