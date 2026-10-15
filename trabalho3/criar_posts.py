#!/usr/bin/env python3
"""
Trabalho 3 - Gera os conteudos dos 3 cenarios de teste e cria os posts
no WordPress via XML-RPC (stdlib, sem dependencias).

Cenarios:
  1) post com imagem de ~1MB
  2) post com texto de ~400KB
  3) post com imagem de ~300KB

Gera/usa os arquivos em cenarios/ e grava locust/posts.json com as URLs
dos posts para o locustfile.py.

Uso:
  python3 criar_posts.py --host http://localhost --user Amilton --password '@Amilton-2903'
"""
import argparse
import base64
import json
import os
import random
import string
import struct
import sys
import xmlrpc.client
import zlib
from urllib.parse import urlparse

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_CENARIOS = os.path.join(AQUI, "cenarios")
POSTS_JSON = os.path.join(AQUI, "locust", "posts.json")


def gerar_png_ruido(caminho, largura, altura):
    """PNG valido com pixels aleatorios (nao comprime -> tamanho ~= esperado)."""
    bruto = bytearray()
    for _ in range(altura):
        bruto.append(0)  # filtro: None
        bruto.extend(os.urandom(largura * 3))  # RGB

    def chunk(tipo, dados):
        dados = tipo + dados
        return (
            struct.pack(">I", len(dados[4:])) + dados
            + struct.pack(">I", zlib.crc32(dados) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0)
    conteudo = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(bruto), 0))
        + chunk(b"IEND", b"")
    )
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return len(conteudo)


def gerar_texto(caminho, tamanho_bytes):
    """Texto ~400KB de palavras aleatorias."""
    palavras = [
        "docker", "wordpress", "nginx", "balanceador", "carga", "locust",
        "usuario", "requisicao", "resposta", "servidor", "contenedor",
        "instancia", "banco", "dados", "mysql", "performance", "latencia",
        "throughput", "escala", "teste", "web", "apache", "php", "http",
    ]
    partes = []
    total = 0
    rnd = random.Random(42)
    while total < tamanho_bytes:
        p = " ".join(rnd.choice(palavras) for _ in range(8))
        partes.append(p)
        total += len(p) + 1
    texto = "\n\n".join(partes)[:tamanho_bytes]
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
    return len(texto)


def garantir_conteudos():
    """Cria os arquivos de cenario (se nao existirem) e retorna info de cada um."""
    os.makedirs(PASTA_CENARIOS, exist_ok=True)
    specs = [
        ("imagem_1mb.png", "png", (580, 580)),   # ~1.01 MB
        ("imagem_300kb.png", "png", (320, 320)),  # ~307 KB
        ("texto_400kb.txt", "txt", 400 * 1024),
    ]
    info = {}
    for nome, tipo, arg in specs:
        caminho = os.path.join(PASTA_CENARIOS, nome)
        if not os.path.exists(caminho):
            if tipo == "png":
                gerar_png_ruido(caminho, *arg)
            else:
                gerar_texto(caminho, arg)
        tamanho = os.path.getsize(caminho)
        info[nome] = {"caminho": caminho, "tamanho": tamanho}
        print(f"  conteudo: {nome} ({tamanho / 1024:.0f} KB)")
    return info


def caminho_relativo(url_absoluta, host):
    """http://localhost/wp-content/... -> /wp-content/..."""
    p = urlparse(url_absoluta)
    return p.path + (f"?{p.query}" if p.query else "")


def main():
    ap = argparse.ArgumentParser(description="Cria os 3 posts de teste no WordPress")
    ap.add_argument("--host", default="http://localhost", help="URL base do WordPress")
    ap.add_argument("--user", required=True, help="usuario admin do WordPress")
    ap.add_argument("--password", required=True, help="senha do usuario admin")
    args = ap.parse_args()

    print("== 1. Gerando conteudos dos cenarios ==")
    cenarios = garantir_conteudos()

    proxy = xmlrpc.client.ServerProxy(f"{args.host.rstrip('/')}/xmlrpc.php")
    try:
        blogs = proxy.wp.getUsersBlogs(args.user, args.password)
    except xmlrpc.client.Fault as e:
        print(f"ERRO ao autenticar no XML-RPC: {e}", file=sys.stderr)
        sys.exit(1)
    # wp.getUsersBlogs retorna uma lista de blogs
    blog_list = blogs["blogs"] if isinstance(blogs, dict) else blogs
    blog_id = blog_list[0]["blogid"]
    print(f"== 2. Conectado ao WordPress (blog id {blog_id}) ==")

    def subir_imagem(nome):
        info = cenarios[nome]
        with open(info["caminho"], "rb") as f:
            bits = xmlrpc.client.Binary(f.read())
        res = proxy.wp.uploadFile(
            blog_id, args.user, args.password,
            {"name": nome, "type": "image/png", "bits": bits, "overwrite": True},
        )
        return caminho_relativo(res["url"], args.host)

    def criar_post(titulo, conteudo):
        post_id = proxy.wp.newPost(
            blog_id, args.user, args.password,
            {
                "post_title": titulo,
                "post_content": conteudo,
                "post_status": "publish",
                "post_type": "post",
            },
        )
        return post_id

    posts = {}

    print("== 3. Criando cenario 1 (imagem ~1MB) ==")
    url_img1 = subir_imagem("imagem_1mb.png")
    pid1 = criar_post(
        "Cenario 1 - Post com imagem de 1MB",
        f"<p>Post de teste do Trabalho 3 com imagem de aproximadamente 1MB.</p>"
        f'<img src="{url_img1}" alt="imagem 1MB" />',
    )
    posts["cenario1"] = {
        "titulo": "Cenario 1 - Post com imagem de 1MB",
        "post_url": f"/?p={pid1}",
        "image_url": url_img1,
    }
    print(f"  post id={pid1} post=/?p={pid1} imagem={url_img1}")

    print("== 4. Criando cenario 2 (texto ~400KB) ==")
    with open(cenarios["texto_400kb.txt"]["caminho"], encoding="utf-8") as f:
        texto = f.read()
    pid2 = criar_post(
        "Cenario 2 - Post com texto de 400KB",
        "<p>Post de teste do Trabalho 3 com texto de aproximadamente 400KB.</p>"
        + "<p>" + texto + "</p>",
    )
    posts["cenario2"] = {
        "titulo": "Cenario 2 - Post com texto de 400KB",
        "post_url": f"/?p={pid2}",
    }
    print(f"  post id={pid2} post=/?p={pid2}")

    print("== 5. Criando cenario 3 (imagem ~300KB) ==")
    url_img3 = subir_imagem("imagem_300kb.png")
    pid3 = criar_post(
        "Cenario 3 - Post com imagem de 300KB",
        f"<p>Post de teste do Trabalho 3 com imagem de aproximadamente 300KB.</p>"
        f'<img src="{url_img3}" alt="imagem 300KB" />',
    )
    posts["cenario3"] = {
        "titulo": "Cenario 3 - Post com imagem de 300KB",
        "post_url": f"/?p={pid3}",
        "image_url": url_img3,
    }
    print(f"  post id={pid3} post=/?p={pid3} imagem={url_img3}")

    with open(POSTS_JSON, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"== Pronto! URLs gravadas em {POSTS_JSON} ==")
    print(json.dumps(posts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
