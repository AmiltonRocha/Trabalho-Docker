#!/usr/bin/env python3
"""
Trabalho 3 - Gera os graficos das execucoes do Locust.

Le os CSVs gerados com --csv (locust/resultados/*_stats.csv), no padrao:
    <cenario>_u<usuarios>_i<instancias>_stats.csv
Ex: cenario1_u100_i3_stats.csv

Gera, por cenario, 2 figuras (PNG):
  - usuarios_no_eixo_x.png : eixo X = usuarios, 1 linha por n. de instancias
  - instancias_no_eixo_x.png: eixo X = instancias, 1 linha por n. de usuarios
Cada figura tem 3 subplots: tempo medio de resposta (ms), RPS e taxa de erro (%).

Dependencia: pip install matplotlib
Uso:
  python3 gerar_graficos.py
  python3 gerar_graficos.py --pasta locust/resultados
"""
import argparse
import csv
import glob
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_PADRAO = os.path.join(AQUI, "locust", "resultados")

METRICAS = [
    ("avg_ms", "Tempo medio de resposta (ms)", "Average response time"),
    ("median_ms", "Mediana - Percentil 50% (ms)", "Median response time"),
    ("p95_ms", "Percentil 95% (ms)", "95%"),
    ("rps", "Requisicoes por segundo (RPS)", "Requests/s"),
    ("erro_pct", "Taxa de erro (%)", None),  # calculada: falhas/total*100
]

PADRAO = re.compile(r"(cenario\d+)_u(\d+)_i(\d+)_stats\.csv$")


def achar_coluna(linha, *candidatas):
    for c in candidatas:
        for chave, valor in linha.items():
            if chave.strip().lower() == c.lower():
                return valor
    return None


def ler_stats(caminho):
    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            nome = (linha.get("Name") or "").strip()
            if nome in ("Aggregated", "Aggregated "):
                total = float(achar_coluna(linha, "# requests", "Request Count") or 0)
                falhas = float(achar_coluna(linha, "# failures", "Failure Count") or 0)
                avg = float(achar_coluna(linha, "Average response time", "Average Latency") or 0)
                median = float(achar_coluna(linha, "Median Response Time") or 0)
                p95 = float(achar_coluna(linha, "95%") or 0)
                rps = float(achar_coluna(linha, "Requests/s", "Requests/s (failures/s)") or 0)
                erro = (falhas / total * 100) if total else 0.0
                return {"avg_ms": avg, "median_ms": median, "p95_ms": p95, "rps": rps, "erro_pct": erro}
    return None


def carregar(pasta):
    dados = {}
    for caminho in glob.glob(os.path.join(pasta, "*_stats.csv")):
        m = PADRAO.search(os.path.basename(caminho))
        if not m:
            continue
        cenario, usuarios, instancias = m.group(1), int(m.group(2)), int(m.group(3))
        stats = ler_stats(caminho)
        if stats:
            dados.setdefault(cenario, []).append(
                {"usuarios": usuarios, "instancias": instancias, **stats}
            )
    for cenario in dados:
        dados[cenario].sort(key=lambda d: (d["usuarios"], d["instancias"]))
    return dados


def plotar_cenario(cenario, pontos, pasta_saida, plt):
    import numpy as np

    usuarios = sorted({p["usuarios"] for p in pontos})
    instancias = sorted({p["instancias"] for p in pontos})

    def serie(filtro, eixo, chave):
        vals = []
        for x in eixo:
            achou = [p for p in pontos if filtro(p, x)]
            vals.append(np.mean([p[chave] for p in achou]) if achou else np.nan)
        return vals

    # Grafico 1: X = usuarios, 1 linha por instancia
    fig, eixos = plt.subplots(5, 1, figsize=(8, 18), sharex=True)
    for inst in instancias:
        for ax, (chave, rotulo, _) in zip(eixos, METRICAS):
            ys = serie(lambda p, x, i=inst: p["usuarios"] == x and p["instancias"] == i, usuarios, chave)
            ax.plot(usuarios, ys, marker="o", label=f"{inst} instancia(s)")
            ax.set_ylabel(rotulo)
            ax.grid(True, alpha=0.3)
            ax.legend()
    eixos[-1].set_xlabel("Usuarios simultaneos")
    eixos[0].set_title(f"{cenario} - variando usuarios (eixo X = usuarios)")
    fig.tight_layout()
    caminho1 = os.path.join(pasta_saida, f"{cenario}_usuarios_no_eixo_x.png")
    fig.savefig(caminho1, dpi=110)
    plt.close(fig)

    # Grafico 2: X = instancias, 1 linha por usuarios
    fig, eixos = plt.subplots(5, 1, figsize=(8, 18), sharex=True)
    for usr in usuarios:
        for ax, (chave, rotulo, _) in zip(eixos, METRICAS):
            ys = serie(lambda p, x, u=usr: p["instancias"] == x and p["usuarios"] == u, instancias, chave)
            ax.plot(instancias, ys, marker="o", label=f"{usr} usuario(s)")
            ax.set_ylabel(rotulo)
            ax.grid(True, alpha=0.3)
            ax.legend()
    # so os valores inteiros testados (1, 2, 3), sem 1.25, 1.5...
    eixos[-1].set_xticks(instancias)
    eixos[-1].set_xlabel("Instancias do WordPress")
    eixos[0].set_title(f"{cenario} - variando instancias (eixo X = instancias)")
    fig.tight_layout()
    caminho2 = os.path.join(pasta_saida, f"{cenario}_instancias_no_eixo_x.png")
    fig.savefig(caminho2, dpi=110)
    plt.close(fig)

    return caminho1, caminho2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default=PASTA_PADRAO)
    ap.add_argument("--saida", default=None, help="pasta de saida (padrao: <pasta>/graficos)")
    args = ap.parse_args()

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("ERRO: matplotlib nao instalado. Rode: pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    dados = carregar(args.pasta)
    if not dados:
        print(f"Nenhum CSV de stats encontrado em {args.pasta}", file=sys.stderr)
        sys.exit(1)

    pasta_saida = args.saida or os.path.join(args.pasta, "graficos")
    os.makedirs(pasta_saida, exist_ok=True)

    for cenario, pontos in sorted(dados.items()):
        print(f"{cenario}: {len(pontos)} execucoes -> {pontos}")
        for c in plotar_cenario(cenario, pontos, pasta_saida, plt):
            print(f"  grafico: {c}")
    print(f"\nPronto! Graficos em: {pasta_saida}")


if __name__ == "__main__":
    main()
