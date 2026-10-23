"""
Locustfile - Trabalho 3
Testes de carga no WordPress com 3 cenários (tags):

  cenario1 : post com imagem de ~1MB   (GET no HTML do post + GET na imagem)
  cenario2 : post com texto de ~400KB  (GET no post - o HTML ja tem ~400KB)
  cenario3 : post com imagem de ~300KB (GET no HTML do post + GET na imagem)

As URLs dos posts vem do arquivo posts.json, gerado pelo criar_posts.py.
Nos cenarios 1 e 3 a imagem e lida do proprio HTML do post (<img src>),
como um navegador faria. Se o post vier sem <img>, a requisicao do post
e marcada como falha (a imagem nao seria testada).
Uso (via docker compose exec):
  --tags cenario1 | cenario2 | cenario3
"""
import json
import os
import re
from urllib.parse import urlparse
from locust import HttpUser, task, between, tag

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posts.json")


def carregar_posts():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


POSTS = carregar_posts()

# so o src (imagem em tamanho original); o srcset traz as miniaturas
# de 150/300px, que nao representam o cenario de 1MB/300KB
IMG_SRC = re.compile(r'<img[^>]+src="([^"]*/wp-content/uploads/[^"]+)"')


class WordpressUser(HttpUser):
    # espera entre 1 e 3 segundos entre acoes do "usuario"
    wait_time = between(1, 3)

    @task(5)
    def pagina_inicial(self):
        self.client.get("/", name="/ (pagina inicial)")

    def post_com_imagens(self, cenario, nome_imagem):
        """GET no HTML do post e depois em cada <img> que ele exibe."""
        post = POSTS.get(cenario, {}).get("post_url", "/?p=1")
        with self.client.get(post, name=f"{cenario}: html do post",
                             catch_response=True) as resp:
            imagens = IMG_SRC.findall(resp.text) if resp.ok else []
            if resp.ok and not imagens:
                resp.failure("post sem <img> - a imagem nao seria testada")
        for src in imagens:
            # caminho relativo: o host do src (localhost:8080) nao existe
            # dentro da rede do Docker, entao usa o host do Locust
            self.client.get(urlparse(src).path, name=nome_imagem)

    @tag("cenario1")
    @task
    def cenario1_imagem_1mb(self):
        self.post_com_imagens("cenario1", "cenario1: imagem ~1MB")

    @tag("cenario2")
    @task
    def cenario2_texto_400kb(self):
        cfg = POSTS.get("cenario2", {})
        post = cfg.get("post_url", "/?p=1")
        self.client.get(post, name="cenario2: texto ~400KB")

    @tag("cenario3")
    @task
    def cenario3_imagem_300kb(self):
        self.post_com_imagens("cenario3", "cenario3: imagem ~300KB")
