#!/usr/bin/env python3
"""
Trabalho 3 - Gera graficos COMPARATIVOS com legenda de zona segura vs zona de estouro.

Le os CSVs gerados com --csv (locust/resultados/*_stats.csv), no padrao:
    <cenario>_u<usuarios>_i<instancias>_stats.csv

Zonas definidas (limites validados na maquina de 7,5GB):
  - ZONA SEGURA  : ate 350 usuarios (0% de erro)
  - ZONA ESTOURO : 400+ usuarios (cenario2: ~2-3% de erro com 400, ~16-17% com 500, HTTP 500)

Gera, por cenario, 1 figura (PNG) com 5 subplots de barras e legenda destacando as zonas:
  - comparacao_cenarioN.png

Dependencia: pip install matplotlib
Uso:
  python3 gerar_graficos_comparacao.py
"""
import csv
import glob
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_PADRAO = os.path.join(AQUI, "locust", "resultados")

LIMITE_SEGURO = 350   # usuarios com 0 erro
LIMITE_ESTOURO = 400  # usuarios onde cenario2 comeca a dar erro

METRICAS = [
    ("avg_ms", "Tempo medio de resposta (ms)"),
    ("median_ms", "Mediana - Percentil 50% (ms)"),
    ("p95_ms", "Percentil 95% (ms)"),
    ("rps", "Requisicoes por segundo (RPS)"),
    ("erro_pct", "Taxa de erro (%)"),
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


def plotar_comparacao(cenario, pontos, pasta_saida, plt):
    import numpy as np

    usuarios = sorted({p["usuarios"] for p in pontos})
    instancias = sorted({p["instancias"] for p in pontos})

    def serie(inst, chave):
        vals = []
        for u in usuarios:
            achou = [p for p in pontos if p["usuarios"] == u and p["instancias"] == inst]
            vals.append(np.mean([p[chave] for p in achou]) if achou else np.nan)
        return vals

    cores = {1: "#2196F3", 2: "#4CAF50", 3: "#FF9800"}

    fig, eixos = plt.subplots(5, 1, figsize=(10, 20), sharex=True)

    # posicoes categoricas para as barras (0, 1, 2...)
    pos = list(range(len(usuarios)))

    for idx, (ax, (chave, rotulo)) in enumerate(zip(eixos, METRICAS)):
        # faixas de zona (baseadas no indice)
        meio = (pos[0] + pos[-1]) / 2
        limite_idx = pos[-1] - 0.5 if LIMITE_SEGURO >= usuarios[-2] else pos[0] + 0.5
        ax.axvspan(pos[0] - 0.5, meio + 0.25, alpha=0.12, color="green",
                   label=f"ZONA SEGURA (ate {LIMITE_SEGURO} usr, 0% erro)")
        ax.axvspan(meio + 0.25, pos[-1] + 0.5, alpha=0.12, color="red",
                   label=f"ZONA DE ESTOURO ({LIMITE_ESTOURO}+ usr, erros no cenario2)")

        # BARRAS AGRUPADAS
        largura = 0.25
        for j, inst in enumerate(instancias):
            ys = serie(inst, chave)
            desloc = (j - 1) * largura
            barras = ax.bar([p + desloc for p in pos], ys, width=largura,
                            color=cores.get(inst, "#9C27B0"), alpha=0.85,
                            label=f"{inst} instancia(s)")
            for bar, y in zip(barras, ys):
                if np.isnan(y):
                    continue
                if chave == "erro_pct":
                    txt = f"{y:.1f}%" if y > 0 else "0%"
                elif y >= 100:
                    txt = f"{y:.0f}"
                else:
                    txt = f"{y:.1f}"
                ax.annotate(txt, (bar.get_x() + bar.get_width()/2, bar.get_height()),
                            textcoords="offset points", xytext=(0, 3),
                            ha="center", fontsize=7,
                            fontweight="bold" if (chave == "erro_pct" and y > 0) else "normal",
                            color="#D32F2F" if (chave == "erro_pct" and y > 0) else "black")
        ax.set_xticks(pos)
        ax.set_xticklabels([f"{u}" for u in usuarios])

        ax.set_ylabel(rotulo, fontsize=10)
        ax.grid(True, alpha=0.3, axis="y")
        ax.legend(loc="upper left", fontsize=8, ncol=2)

    eixos[-1].set_xlabel("Usuarios simultaneos (leve=10 | pesado=350 | extremo=400 | maximo=500)", fontsize=10)
    eixos[0].set_title(
        f"{cenario} - Comparacao de carga: ZONA SEGURA (verde) vs ZONA DE ESTOURO (vermelho)\n"
        f"Maquina: 12 CPU / 7,5GB RAM | Locust + WordPress + MySQL na mesma maquina",
        fontsize=11, fontweight="bold",
    )
    fig.tight_layout()
    caminho = os.path.join(pasta_saida, f"comparacao_{cenario}.png")
    fig.savefig(caminho, dpi=120)
    plt.close(fig)
    return caminho


def main():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("ERRO: matplotlib nao instalado. Rode: pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    dados = carregar(PASTA_PADRAO)
    if not dados:
        print(f"Nenhum CSV de stats encontrado em {PASTA_PADRAO}", file=sys.stderr)
        sys.exit(1)

    pasta_saida = os.path.join(PASTA_PADRAO, "comparacao")
    os.makedirs(pasta_saida, exist_ok=True)

    for cenario, pontos in sorted(dados.items()):
        print(f"{cenario}: {len(pontos)} execucoes")
        caminho = plotar_comparacao(cenario, pontos, pasta_saida, plt)
        print(f"  grafico: {caminho}")

    print(f"\nPronto! Graficos comparativos em: {pasta_saida}")


if __name__ == "__main__":
    main()
