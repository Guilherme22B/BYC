"""
API do BCY Lens: recebe a foto ou o vídeo enviados pelo site e devolve a análise.

Rodar:  python app.py      (fica em http://127.0.0.1:5000)

Rotas:
    GET  /api/saude     -> {"ok": true}  (o site usa para saber se o servidor está no ar)
    POST /api/analisar  -> multipart com "arquivo" (foto ou vídeo) e "legenda" (texto)
"""

import os
import tempfile

from flask import Flask, jsonify, request

from analise import EXTENSOES_VIDEO, analisar_arquivo

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # até 200 MB

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@app.get("/api/saude")
def saude():
    return jsonify(ok=True)


@app.post("/api/analisar")
def analisar():
    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        return jsonify(erro="Envie uma foto ou um vídeo no campo 'arquivo'."), 400

    extensao = os.path.splitext(arquivo.filename)[1].lower()
    if extensao not in EXTENSOES_IMAGEM | EXTENSOES_VIDEO:
        return jsonify(erro=f"Formato {extensao or 'desconhecido'} não suportado. "
                            "Use JPG, PNG, WEBP, MP4, MOV ou WEBM."), 400

    legenda = request.form.get("legenda", "")

    # O OpenCV lê do disco, então salvamos num arquivo temporário
    descritor, caminho = tempfile.mkstemp(suffix=extensao)
    os.close(descritor)
    try:
        arquivo.save(caminho)
        resultado = analisar_arquivo(caminho, legenda)
    except ValueError as erro:
        return jsonify(erro=str(erro)), 422
    except Exception as erro:  # mostra o motivo no site em vez de travar
        app.logger.exception("Falha na análise")
        return jsonify(erro=f"Erro ao analisar o arquivo: {erro}"), 500
    finally:
        os.remove(caminho)

    return jsonify(resultado)


@app.errorhandler(413)
def arquivo_grande(_):
    return jsonify(erro="Arquivo maior que 200 MB."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
