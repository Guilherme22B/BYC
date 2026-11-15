"""
BCY Lens pelo terminal (serve também como plano B na demonstração).

Uso:
    python analisar.py foto.jpg --legenda "Meu look de hoje! O que acharam? #moda #look #ootd"
    python analisar.py video.mp4 --legenda "..."
    python analisar.py foto.jpg --json          # imprime o resultado completo em JSON

A imagem anotada é salva ao lado do arquivo como <nome>_bcylens.jpg
"""

import argparse
import base64
import json
import os
import sys

from analise import analisar_arquivo


def barra(nota, largura=20):
    if nota is None:
        return "-" * largura
    cheios = round(nota / 100 * largura)
    return "#" * cheios + "." * (largura - cheios)


def main():
    parser = argparse.ArgumentParser(description="Analisa uma foto ou vídeo com o BCY Lens")
    parser.add_argument("arquivo", help="caminho da foto ou do vídeo")
    parser.add_argument("--legenda", default="", help="legenda que será publicada")
    parser.add_argument("--json", action="store_true", help="imprime o resultado em JSON")
    args = parser.parse_args()

    if not os.path.exists(args.arquivo):
        sys.exit(f"Arquivo não encontrado: {args.arquivo}")

    resultado = analisar_arquivo(args.arquivo, args.legenda)

    base, _ = os.path.splitext(args.arquivo)
    saida = base + "_bcylens.jpg"
    with open(saida, "wb") as f:
        f.write(base64.b64decode(resultado["imagem_anotada"]))

    if args.json:
        resultado = {k: v for k, v in resultado.items() if k != "imagem_anotada"}
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return

    print()
    print(f"  BCY Lens · {os.path.basename(args.arquivo)}")
    if resultado["tipo"] == "video":
        print(f"  Vídeo de {resultado['duracao_segundos']} s · "
              f"{resultado['quadros_analisados']} quadros analisados · "
              f"melhor quadro para capa em {resultado['melhor_quadro_segundos']} s")
    print()
    print(f"  NOTA GERAL: {resultado['nota_geral']}/100  ({resultado['classificacao']})")
    print()
    for c in resultado["criterios"]:
        nota = "  --" if c["nota"] is None else f"{c['nota']:4d}"
        print(f"  {c['nome']:<17}{nota}  {barra(c['nota'])}  {c['detalhe']}")
    print()
    if resultado["dicas"]:
        print("  DICAS (da mais urgente para a menos urgente)")
        for d in resultado["dicas"]:
            print(f"  - {d['dica']}")
    else:
        print("  Nenhuma dica: a foto está pronta para postar!")
    print()
    print(f"  Imagem anotada salva em: {saida}")
    print()


if __name__ == "__main__":
    main()
