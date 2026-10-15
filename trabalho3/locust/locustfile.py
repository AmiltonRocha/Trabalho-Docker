"""
Locustfile - Trabalho 3
Testes de carga no WordPress com 3 cenários (tags):

  cenario1 : post com imagem de ~1MB   (GET no post + GET na imagem)
  cenario2 : post com texto de ~400KB  (GET no post - o HTML ja tem ~400KB)
  cenario3 : post com imagem de ~300KB (GET no post + GET na imagem)

As URLs dos posts vem do arquivo posts.json, gerado pelo criar_posts.py.
Uso (via docker compose run):
  --tags cenario1 | cenario2 | cenario3
"""
import json
import os
from locust import HttpUser, task, between, tag

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posts.json")


def carregar_posts():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


POSTS = carregar_posts()


class WordpressUser(HttpUser):
    # espera entre 1 e 3 segundos entre acoes do "usuario"
    wait_time = between(1, 3)

    @task(5)
    def pagina_inicial(self):
        self.client.get("/", name="/ (pagina inicial)")

    @tag("cenario1")
    @task
    def cenario1_imagem_1mb(self):
        cfg = POSTS.get("cenario1", {})
        post = cfg.get("post_url", "/?p=1")
        imagem = cfg.get("image_url")
        self.client.get(post, name="cenario1: post ~1MB")
        if imagem:
            self.client.get(imagem, name="cenario1: imagem ~1MB")

    @tag("cenario2")
    @task
    def cenario2_texto_400kb(self):
        cfg = POSTS.get("cenario2", {})
        post = cfg.get("post_url", "/?p=1")
        self.client.get(post, name="cenario2: texto ~400KB")

    @tag("cenario3")
    @task
    def cenario3_imagem_300kb(self):
        cfg = POSTS.get("cenario3", {})
        post = cfg.get("post_url", "/?p=1")
        imagem = cfg.get("image_url")
        self.client.get(post, name="cenario3: post ~300KB")
        if imagem:
            self.client.get(imagem, name="cenario3: imagem ~300KB")
