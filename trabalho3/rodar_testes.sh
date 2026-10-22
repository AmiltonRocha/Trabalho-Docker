#!/usr/bin/env bash
# ============================================================
# Trabalho 3 - Executa a matriz completa de testes de carga
#   instancias (1,2,3) x cenarios (1,2,3) x usuarios (10,350,400,500)
#   10/350 = zona segura (~0 erro) | 400/500 = zona de estouro
#   (cenario2: ate ~3% de erro com 400 e ~16-17% com 500)
# CSVs sao gravados em locust/resultados/
#
# IMPORTANTE: usa `docker compose exec` (e NAO `docker compose run`),
# pois `compose run` re-sincroniza a escala e REMOVE os containers
# extras criados com --scale wordpress=N.
# ============================================================
set -e
cd "$(dirname "$0")"

USUARIOS=(${USUARIOS:-10 350 400 500})
INSTANCIAS=(${INSTANCIAS:-1 2 3})
CENARIOS=(cenario1 cenario2 cenario3)
RUN_TIME=${RUN_TIME:-30s}
SPAWN_RATE=${SPAWN_RATE:-25}

mkdir -p locust/resultados

# garante todos os servicos de base no ar (inclui o locust na web UI)
docker compose up -d

for inst in "${INSTANCIAS[@]}"; do
  echo "=========================== Instancias do WordPress: $inst ==========================="
  docker compose up -d --scale "wordpress=$inst"
  # reinicia o nginx para re-resolver os IPs das instancias no DNS
  docker compose restart nginx
  sleep 10

  # confirma o balanceamento (X-Upstream deve alternar)
  echo "Teste rapido do balanceamento:"
  for i in 1 2 3; do
    curl -sI http://localhost:8080/ | grep -i x-upstream || true
  done

  for cen in "${CENARIOS[@]}"; do
    for usr in "${USUARIOS[@]}"; do
      prefixo="/locust/resultados/${cen}_u${usr}_i${inst}"
      echo "---- ${cen} | usuarios=${usr} | instancias=${inst} | duracao=${RUN_TIME} ----"
      docker compose exec -T locust locust \
        -f /locust/locustfile.py --host=http://nginx \
        --headless -u "${usr}" -r "${SPAWN_RATE}" --run-time "${RUN_TIME}" \
        --tags "${cen}" --csv "${prefixo}" --only-summary || true
    done
  done
done

echo
echo "==== Todos os testes concluidos! ===="
echo "Proximos passos:"
echo "  python3 gerar_graficos.py"
echo "  Graficos em locust/resultados/graficos/"
