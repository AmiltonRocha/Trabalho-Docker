#!/usr/bin/env python3
"""
Trabalho 3 - Gera graficos COMPARATIVOS com legenda de zona segura vs zona de estouro.

Le os CSVs gerados com --csv (locust/resultados/*_stats.csv), no padrao:
    <cenario>_u<usuarios>_i<instancias>_stats.csv

Zonas:
  - ZONA SEGURA  : ate LIMITE_SEGURO (350) usuarios
  - ZONA ESTOURO : acima de LIMITE_SEGURO
A faixa de cada zona e o erro maximo mostrado na legenda sao calculados a
partir dos CSVs de cada cenario (nada fixo no texto).

Gera, por cenario, 1 figura (PNG) com 5 subplots de barras e legenda destacando as zonas:
  - comparacao_cenarioN.png

Barras hachuradas = execucoes com falhas. O Locust inclui as respostas de
erro (HTTP 500, que voltam rapido) no tempo de resposta e no RPS, entao
nessas barras o tempo parece menor do que o real.

Dependencia: pip install matplotlib
Uso:
  python3 gerar_graficos_comparacao.py
  python3 gerar_graficos_comparacao.py --pasta locust/resultados_maxconn500 --legenda "MySQL max_connections=500"
O subtitulo mostra as CPUs/RAM do Docker (lidas do `docker info`) e a --legenda.
"""
import argparse
import csv
import glob
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_PADRAO = os.path.join(AQUI, "locust", "resultados")

LIMITE_SEGURO = 350   # ate aqui o sistema fica estavel (~0% de erro)

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


def descrever_maquina():
    """CPUs e RAM que o Docker enxerga (onde rodaram Locust, WordPress e MySQL)."""
    try:
        saida = subprocess.run(
            ["docker", "info", "--format", "{{.NCPU}} {{.MemTotal}}"],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout.split()
        cpus, ram = int(saida[0]), int(saida[1]) / 1024 ** 3
        return f"Docker: {cpus} CPU / {ram:.1f}GB RAM".replace(".", ",")
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return "Maquina unica"


def plotar_comparacao(cenario, pontos, pasta_saida, plt, legenda):
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

    # posicoes categoricas para as barras (0, 1, 2...)
    pos = list(range(len(usuarios)))

    # zonas a partir dos dados: o limite fica entre o ultimo grupo <= LIMITE_SEGURO
    # e o primeiro grupo acima dele (ex: entre 350 e 400 -> posicao 1.5)
    seguros = [i for i, u in enumerate(usuarios) if u <= LIMITE_SEGURO]
    divisa = (seguros[-1] + 0.5) if seguros else (pos[0] - 0.5)
    acima = [u for u in usuarios if u > LIMITE_SEGURO]

    def erro_max(filtro):
        erros = [p["erro_pct"] for p in pontos if filtro(p["usuarios"])]
        return max(erros) if erros else 0.0

    erro_seguro = erro_max(lambda u: u <= LIMITE_SEGURO)
    erro_estouro = erro_max(lambda u: u > LIMITE_SEGURO)

    fig, eixos = plt.subplots(5, 1, figsize=(10, 20), sharex=True)

    for ax, (chave, rotulo) in zip(eixos, METRICAS):
        if seguros:
            ax.axvspan(pos[0] - 0.5, divisa, alpha=0.12, color="green",
                       label=f"ZONA SEGURA (ate {LIMITE_SEGURO} usr, erro max {erro_seguro:.1f}%)")
        if acima:
            ax.axvspan(divisa, pos[-1] + 0.5, alpha=0.12, color="red",
                       label=f"ZONA DE ESTOURO ({acima[0]}+ usr, erro max {erro_estouro:.1f}%)")

        # BARRAS AGRUPADAS, centradas em cada grupo de usuarios
        largura = 0.25
        for j, inst in enumerate(instancias):
            ys = serie(inst, chave)
            erros = serie(inst, "erro_pct")
            desloc = (j - (len(instancias) - 1) / 2) * largura
            barras = ax.bar([p + desloc for p in pos], ys, width=largura,
                            color=cores.get(inst, "#9C27B0"), alpha=0.85,
                            label=f"{inst} instancia(s)")
            for bar, y, e in zip(barras, ys, erros):
                if np.isnan(y):
                    continue
                # execucao com falhas: hachura (o valor inclui respostas de erro)
                if e > 0:
                    bar.set_hatch("//")
                    bar.set_edgecolor("#D32F2F")
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

        # cenarios com imagem: o "Aggregated" soma post + imagem (2 requisicoes
        # por visita), entao tempo e RPS nao sao comparaveis com o cenario2
        if chave != "erro_pct" and any(p["n_reqs"] > 1 for p in pontos):
            rotulo += "\n(post + imagem)"
        ax.set_ylabel(rotulo, fontsize=10)
        ax.grid(True, alpha=0.3, axis="y")
        # folga no topo para a legenda nao cobrir as barras e os rotulos
        ax.set_ylim(0, max(ax.get_ylim()[1] * 1.3, 1))
        ax.legend(loc="upper left", fontsize=8, ncol=2)

    eixos[-1].set_xlabel(
        "Usuarios simultaneos (" + " | ".join(str(u) for u in usuarios) + ")", fontsize=10)
    eixos[0].set_title(
        f"{cenario} - Comparacao de carga: ZONA SEGURA (verde) vs ZONA DE ESTOURO (vermelho)\n"
        f"{legenda} | Locust + WordPress + MySQL na mesma maquina",
        fontsize=11, fontweight="bold",
    )
    rect = (0, 0, 1, 1)
    if any(p["erro_pct"] > 0 for p in pontos):
        fig.text(0.5, 0.005,
                 "Barras hachuradas: execucoes com falhas (HTTP 500). O Locust inclui as respostas de erro,\n"
                 "que voltam rapido, no tempo e no RPS - nessas barras o tempo real dos acertos e maior.",
                 ha="center", fontsize=8, color="#D32F2F")
        rect = (0, 0.02, 1, 1)
    fig.tight_layout(rect=rect)
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

    ap = argparse.ArgumentParser(description="Graficos comparativos (zona segura x estouro)")
    ap.add_argument("--pasta", default=PASTA_PADRAO, help="pasta com os *_stats.csv")
    ap.add_argument("--legenda", default=None,
                    help='texto do subtitulo (padrao: CPU/RAM do Docker), ex: "MySQL max_connections=500"')
    args = ap.parse_args()
    legenda = descrever_maquina()
    if args.legenda:
        legenda += f" | {args.legenda}"

    dados = carregar(args.pasta)
    if not dados:
        print(f"Nenhum CSV de stats encontrado em {args.pasta}", file=sys.stderr)
        sys.exit(1)

    pasta_saida = os.path.join(args.pasta, "comparacao")
    os.makedirs(pasta_saida, exist_ok=True)

    for cenario, pontos in sorted(dados.items()):
        print(f"{cenario}: {len(pontos)} execucoes")
        caminho = plotar_comparacao(cenario, pontos, pasta_saida, plt, legenda)
        print(f"  grafico: {caminho}")

    print(f"\nPronto! Graficos comparativos em: {pasta_saida}")


if __name__ == "__main__":
    main()
