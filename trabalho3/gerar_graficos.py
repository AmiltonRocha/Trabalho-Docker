#!/usr/bin/env python3
"""
Trabalho 3 - Gera os graficos das execucoes do Locust.

Le os CSVs gerados com --csv (locust/resultados/*_stats.csv), no padrao:
    <cenario>_u<usuarios>_i<instancias>_stats.csv
Ex: cenario1_u100_i3_stats.csv

Gera, por cenario, 2 figuras (PNG):
  - usuarios_no_eixo_x.png : eixo X = usuarios, 1 linha por n. de instancias
  - instancias_no_eixo_x.png: eixo X = instancias, 1 linha por n. de usuarios
Cada figura tem 5 subplots: tempo medio, mediana, P95 (ms), RPS e taxa de erro (%).

Pontos com anel vermelho = execucoes com falhas. O Locust inclui as respostas
de erro (HTTP 500, que voltam rapido) no tempo de resposta e no RPS, entao
nesses pontos o tempo parece menor do que o real.

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
        n_reqs = 0  # requisicoes distintas por visita (post, imagem...)
        for linha in leitor:
            nome = (linha.get("Name") or "").strip()
            if nome != "Aggregated":
                n_reqs += 1
                continue
            total = float(achar_coluna(linha, "# requests", "Request Count") or 0)
            falhas = float(achar_coluna(linha, "# failures", "Failure Count") or 0)
            avg = float(achar_coluna(linha, "Average response time", "Average Latency") or 0)
            median = float(achar_coluna(linha, "Median Response Time") or 0)
            p95 = float(achar_coluna(linha, "95%") or 0)
            rps = float(achar_coluna(linha, "Requests/s", "Requests/s (failures/s)") or 0)
            erro = (falhas / total * 100) if total else 0.0
            return {"avg_ms": avg, "median_ms": median, "p95_ms": p95, "rps": rps,
                    "erro_pct": erro, "n_reqs": n_reqs}
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

    # cenarios com imagem: o "Aggregated" soma post + imagem (2 requisicoes
    # por visita), entao tempo e RPS nao sao comparaveis com o cenario2
    com_imagem = any(p["n_reqs"] > 1 for p in pontos)

    def serie(filtro, eixo, chave):
        vals = []
        for x in eixo:
            achou = [p for p in pontos if filtro(p, x)]
            vals.append(np.mean([p[chave] for p in achou]) if achou else np.nan)
        return vals

    def desenhar(eixo_x, linhas, rotulo_linha, xlabel, titulo, arquivo):
        """eixo_x: valores do eixo X; linhas: (valor, filtro) de cada linha."""
        fig, eixos = plt.subplots(5, 1, figsize=(8, 18), sharex=True)
        houve_falha = False
        for valor, filtro in linhas:
            erros = serie(filtro, eixo_x, "erro_pct")
            for ax, (chave, rotulo, _) in zip(eixos, METRICAS):
                ys = serie(filtro, eixo_x, chave)
                ax.plot(eixo_x, ys, marker="o", label=rotulo_linha(valor))
                # execucao com falhas: anel vermelho (o valor inclui respostas de erro)
                xs_f = [x for x, e in zip(eixo_x, erros) if e > 0]
                ys_f = [y for y, e in zip(ys, erros) if e > 0]
                if xs_f:
                    houve_falha = True
                    ax.scatter(xs_f, ys_f, s=160, facecolors="none",
                               edgecolors="#D32F2F", linewidths=1.5, zorder=3)
        for ax, (chave, rotulo, _) in zip(eixos, METRICAS):
            if com_imagem and chave != "erro_pct":
                rotulo += "\n(post + imagem)"
            ax.set_ylabel(rotulo)
            ax.grid(True, alpha=0.3)
            # metricas nao negativas: eixo Y comeca em 0 (evita -0.04% de erro)
            ax.set_ylim(0, max(ax.get_ylim()[1], 1))
            ax.legend()
        # so os valores testados no eixo X (ex: 1, 2, 3 instancias)
        eixos[-1].set_xticks(eixo_x)
        eixos[-1].set_xlabel(xlabel)
        eixos[0].set_title(titulo)
        rect = (0, 0, 1, 1)
        if houve_falha:
            fig.text(0.5, 0.005,
                     "Anel vermelho: execucao com falhas (HTTP 500). O Locust inclui as respostas\n"
                     "de erro, que voltam rapido, no tempo e no RPS - o tempo real dos acertos e maior.",
                     ha="center", fontsize=8, color="#D32F2F")
            rect = (0, 0.025, 1, 1)
        fig.tight_layout(rect=rect)
        caminho = os.path.join(pasta_saida, arquivo)
        fig.savefig(caminho, dpi=110)
        plt.close(fig)
        return caminho

    # Grafico 1: X = usuarios, 1 linha por instancia
    caminho1 = desenhar(
        usuarios,
        [(i, lambda p, x, i=i: p["usuarios"] == x and p["instancias"] == i) for i in instancias],
        lambda i: f"{i} instancia(s)",
        "Usuarios simultaneos",
        f"{cenario} - variando usuarios (eixo X = usuarios)",
        f"{cenario}_usuarios_no_eixo_x.png",
    )

    # Grafico 2: X = instancias, 1 linha por usuarios
    caminho2 = desenhar(
        instancias,
        [(u, lambda p, x, u=u: p["instancias"] == x and p["usuarios"] == u) for u in usuarios],
        lambda u: f"{u} usuario(s)",
        "Instancias do WordPress",
        f"{cenario} - variando instancias (eixo X = instancias)",
        f"{cenario}_instancias_no_eixo_x.png",
    )

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
