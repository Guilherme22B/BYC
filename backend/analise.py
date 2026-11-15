"""
BCY Lens — núcleo de processamento de imagem.

Analisa uma foto (ou os quadros de um vídeo) e devolve uma nota de 0 a 100
para cada um dos 8 critérios, a nota geral ponderada, as dicas e a imagem
anotada.

Conteúdos da disciplina usados (slide 8 da apresentação):
    Espaços de cor ........ cv2.cvtColor (cinza e HSV)      -> preprocessar()
    Histograma ............ cv2.calcHist                    -> avaliar_iluminacao()
    Filtros e convolução .. cv2.Laplacian, cv2.GaussianBlur -> avaliar_nitidez(), preprocessar()
    Detecção de bordas .... cv2.Canny                       -> avaliar_angulo()
    Transformada de Hough . cv2.HoughLinesP                 -> avaliar_angulo()
    Detecção de objetos ... cv2.CascadeClassifier (Haar)    -> detectar_rostos()
    Geometria da imagem ... cv2.resize, regra dos terços    -> preprocessar(), avaliar_enquadramento()
"""

import base64
import os
import re

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

LADO_MAXIMO = 1080  # a imagem é padronizada para 1080 px no lado maior

# Peso de cada critério na nota geral (soma = 100)
PESOS = {
    "iluminacao": 15,
    "contraste": 10,
    "nitidez": 15,
    "cores": 10,
    "angulo": 10,
    "enquadramento": 15,
    "pessoas_fundo": 10,
    "legenda": 15,
}

NOMES = {
    "iluminacao": "Iluminação",
    "contraste": "Contraste",
    "nitidez": "Nitidez",
    "cores": "Cores",
    "angulo": "Ângulo",
    "enquadramento": "Enquadramento",
    "pessoas_fundo": "Pessoas ao fundo",
    "legenda": "Legenda",
}

# Abaixo desta nota o critério gera uma dica de melhoria
NOTA_PARA_DICA = 70

PASTA = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def limitar(valor, minimo=0.0, maximo=100.0):
    return float(max(minimo, min(maximo, valor)))


def faixa_ideal(valor, zero_baixo, ideal_min, ideal_max, zero_alto):
    """Nota 100 dentro da faixa ideal, caindo em linha reta até 0 nas pontas."""
    if valor < ideal_min:
        return limitar((valor - zero_baixo) / (ideal_min - zero_baixo) * 100)
    if valor > ideal_max:
        return limitar((zero_alto - valor) / (zero_alto - ideal_max) * 100)
    return 100.0


def criterio(nota, detalhe, dica=None, medida=None):
    """Formato padrão do resultado de cada critério."""
    return {
        "nota": None if nota is None else round(nota),
        "detalhe": detalhe,
        "dica": dica if (nota is not None and nota < NOTA_PARA_DICA) else None,
        "medida": medida,
    }


# ---------------------------------------------------------------------------
# Pré-processamento
# ---------------------------------------------------------------------------

def preprocessar(imagem_bgr):
    """Reduz para no máximo 1080 px no lado maior e gera as versões cinza, HSV e suavizada."""
    altura, largura = imagem_bgr.shape[:2]
    escala = LADO_MAXIMO / max(altura, largura)
    if escala < 1:  # só reduz; ampliar inventaria pixels e borraria a foto
        imagem_bgr = cv2.resize(imagem_bgr, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)

    cinza = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
    suavizada = cv2.GaussianBlur(cinza, (5, 5), 0)  # reduz ruído antes das bordas
    return imagem_bgr, cinza, hsv, suavizada


# ---------------------------------------------------------------------------
# Critérios 1 a 4: iluminação, contraste, nitidez e cores
# ---------------------------------------------------------------------------

def avaliar_iluminacao(cinza):
    """Histograma de brilho: média e proporção de áreas estouradas ou escuras."""
    hist = cv2.calcHist([cinza], [0], None, [256], [0, 256]).ravel()
    hist = hist / hist.sum()
    niveis = np.arange(256)

    media = float((hist * niveis).sum())
    estourado = float(hist[245:].sum())  # quase branco
    escuro = float(hist[:15].sum())      # quase preto

    nota = faixa_ideal(media, 25, 100, 170, 240)
    # Penaliza quando mais de 5% da foto está estourada ou sem detalhe no escuro
    nota -= max(0, estourado - 0.05) * 200
    nota -= max(0, escuro - 0.05) * 200
    nota = limitar(nota)

    if media < 100 or escuro > 0.05:
        dica = "Foto escura: procure luz natural de frente (janela) ou aumente a exposição."
    elif media > 170 or estourado > 0.05:
        dica = "Foto estourada: evite sol direto ou contraluz e reduza a exposição."
    else:
        dica = None

    detalhe = (f"Brilho médio {media:.0f}/255 · {estourado*100:.0f}% estourado · "
               f"{escuro*100:.0f}% muito escuro")
    return criterio(nota, detalhe, dica, {"brilho_medio": round(media, 1),
                                          "estourado": round(estourado, 3),
                                          "escuro": round(escuro, 3)})


def avaliar_contraste(cinza):
    """Desvio padrão da intensidade: baixo = imagem 'lavada', alto demais = dura."""
    desvio = float(np.std(cinza))
    nota = faixa_ideal(desvio, 10, 45, 80, 120)

    if desvio < 45:
        dica = "Contraste baixo: a foto parece 'lavada'. Busque um fundo que se destaque de você."
    elif desvio > 80:
        dica = "Contraste muito alto: sombras duras. Use luz mais suave ou difusa."
    else:
        dica = None
    return criterio(nota, f"Desvio padrão da intensidade: {desvio:.0f}", dica,
                    {"desvio_padrao": round(desvio, 1)})


def avaliar_nitidez(cinza):
    """Variância do Laplaciano: quanto maior, mais bordas finas (foto nítida)."""
    variancia = float(cv2.Laplacian(cinza, cv2.CV_64F).var())
    # Com a imagem padronizada em 1080 px: ~20 = muito borrada, 250+ = nítida
    nota = limitar((variancia - 20) / (250 - 20) * 100)
    dica = "Foto tremida ou sem foco: apoie o celular e toque na tela para focar."
    return criterio(nota, f"Variância do Laplaciano: {variancia:.0f}", dica,
                    {"variancia_laplaciano": round(variancia, 1)})


def avaliar_cores(hsv):
    """Saturação média no espaço HSV (canal S)."""
    saturacao = float(np.mean(hsv[:, :, 1]))
    nota = faixa_ideal(saturacao, 10, 70, 170, 240)

    if saturacao < 70:
        dica = "Cores apagadas: aproveite fundos e roupas coloridos ou aumente a saturação."
    elif saturacao > 170:
        dica = "Cores saturadas demais: reduza filtros ou a saturação na edição."
    else:
        dica = None
    return criterio(nota, f"Saturação média: {saturacao:.0f}/255", dica,
                    {"saturacao_media": round(saturacao, 1)})


# ---------------------------------------------------------------------------
# Critério 5: ângulo (Canny + Hough)
# ---------------------------------------------------------------------------

def avaliar_angulo(suavizada):
    """Mede a inclinação das linhas retas da cena (horizonte, paredes, portas)."""
    altura, largura = suavizada.shape
    bordas = cv2.Canny(suavizada, 50, 150)
    linhas = cv2.HoughLinesP(bordas, 1, np.pi / 180, threshold=80,
                             minLineLength=int(min(altura, largura) * 0.15), maxLineGap=10)

    desvios, comprimentos, usadas = [], [], []
    if linhas is not None:
        for x1, y1, x2, y2 in linhas.reshape(-1, 4):
            angulo = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180
            # Desvio COM SINAL até a referência mais próxima: horizontal (0°/180°)
            # ou vertical (90°). Se a câmera está torta, todas as linhas desviam
            # para o mesmo lado; linhas naturalmente inclinadas se anulam.
            referencias = [0, 90, 180]
            referencia = min(referencias, key=lambda r: abs(angulo - r))
            desvio = angulo - referencia
            if abs(desvio) <= 15:  # linhas muito diagonais não servem de referência
                desvios.append(desvio)
                comprimentos.append(np.hypot(x2 - x1, y2 - y1))
                usadas.append((int(x1), int(y1), int(x2), int(y2)))

    if len(desvios) < 2:
        return criterio(100, "Poucas linhas retas de referência na cena",
                        medida={"inclinacao_graus": None, "linhas": usadas})

    # Mediana ponderada pelo comprimento: linhas longas pesam mais e
    # linhas "estranhas" (braços, objetos inclinados) não distorcem o resultado
    ordem = np.argsort(desvios)
    desvios_ord = np.array(desvios)[ordem]
    pesos_ord = np.array(comprimentos)[ordem]
    acumulado = np.cumsum(pesos_ord)
    mediana = float(desvios_ord[np.searchsorted(acumulado, acumulado[-1] / 2)])
    inclinacao = abs(mediana)

    nota = limitar(100 - (inclinacao - 1) / (8 - 1) * 100)  # até 1° = 100, 8°+ = 0
    dica = f"Foto torta (~{inclinacao:.0f}°): ative a grade da câmera e alinhe o horizonte."
    return criterio(nota, f"Inclinação de {inclinacao:.1f}° (mediana de {len(usadas)} linhas)",
                    dica, {"inclinacao_graus": round(inclinacao, 1), "linhas": usadas})


# ---------------------------------------------------------------------------
# Critérios 6 e 7: enquadramento e pessoas ao fundo (detecção de rostos)
# ---------------------------------------------------------------------------

_classificador = None


def carregar_classificador():
    """Carrega o classificador Haar de rostos que vem com o opencv-python."""
    global _classificador
    if _classificador is not None:
        return _classificador

    candidatos = []
    if hasattr(cv2, "data") and getattr(cv2.data, "haarcascades", None):
        candidatos.append(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    candidatos.append(os.path.join(PASTA, "haarcascade_frontalface_default.xml"))

    for caminho in candidatos:
        if os.path.exists(caminho):
            classificador = cv2.CascadeClassifier(caminho)
            if not classificador.empty():
                _classificador = classificador
                return _classificador
    raise RuntimeError(
        "Classificador de rostos não encontrado. Instale opencv-python 4.x "
        "(pip install -r requirements.txt) ou copie haarcascade_frontalface_default.xml "
        "para a pasta backend/."
    )


def detectar_rostos(cinza):
    """Retorna os rostos [(x, y, w, h), ...] do maior para o menor."""
    equalizada = cv2.equalizeHist(cinza)
    tamanho_min = max(24, int(min(cinza.shape) * 0.04))
    rostos = carregar_classificador().detectMultiScale(
        equalizada, scaleFactor=1.1, minNeighbors=6, minSize=(tamanho_min, tamanho_min))
    rostos = [tuple(int(v) for v in r) for r in rostos]
    return sorted(rostos, key=lambda r: r[2] * r[3], reverse=True)


def separar_rostos(rostos):
    """Rosto principal = o maior. Ao fundo = rostos com menos de 40% da área dele."""
    if not rostos:
        return None, [], []
    principal = rostos[0]
    area_principal = principal[2] * principal[3]
    fundo = [r for r in rostos[1:] if r[2] * r[3] < 0.4 * area_principal]
    grupo = [r for r in rostos[1:] if r[2] * r[3] >= 0.4 * area_principal]
    return principal, grupo, fundo


def avaliar_enquadramento(rosto, largura, altura):
    """Distância do rosto principal até o ponto da regra dos terços mais próximo."""
    if rosto is None:
        return criterio(None, "Nenhum rosto detectado: enquadramento não avaliado",
                        medida={"rosto": None})

    x, y, w, h = rosto
    cx, cy = x + w / 2, y + h * 0.4  # altura dos olhos, aproximadamente
    pontos = [(largura * a, altura * b) for a in (1 / 3, 2 / 3) for b in (1 / 3, 2 / 3)]
    diagonal = np.hypot(largura, altura)
    distancia = min(np.hypot(cx - px, cy - py) for px, py in pontos) / diagonal

    # Rosto exatamente no centro também é aceitável em retratos
    no_centro = abs(cx - largura / 2) < largura * 0.08 and cy < altura * 0.5
    nota = limitar(100 - (distancia - 0.05) / (0.25 - 0.05) * 100)
    if no_centro:
        nota = max(nota, 75.0)

    # Rosto cortado pela borda da foto
    margem = 0.01 * min(largura, altura)
    cortado = x <= margem or y <= margem or x + w >= largura - margem or y + h >= altura - margem
    if cortado:
        nota = limitar(nota - 40)
        dica = "Rosto cortado pela borda: afaste a câmera e deixe espaço acima da cabeça."
    elif cy > altura * 0.6:
        nota = limitar(nota - 20)
        dica = "Rosto baixo demais: suba o enquadramento e posicione os olhos na linha superior."
    else:
        dica = "Use a regra dos terços: posicione os olhos sobre um dos cruzamentos da grade."

    return criterio(nota, f"Distância até o ponto de terço: {distancia*100:.0f}% da diagonal",
                    dica, {"rosto": list(rosto), "distancia_tercos": round(float(distancia), 3)})


def avaliar_pessoas_fundo(fundo):
    n = len(fundo)
    nota = limitar(100 - 30 * n)  # 1 pessoa = 70, 2 = 40, 3 = 10
    if n == 0:
        return criterio(nota, "Nenhuma pessoa ao fundo", medida={"quantidade": 0})
    texto = "Uma pessoa" if n == 1 else f"{n} pessoas"
    # Com 1 pessoa a nota fica no limite; mostramos a dica mesmo assim
    resultado = criterio(nota, f"{texto} ao fundo", medida={"quantidade": n})
    resultado["dica"] = f"{texto} ao fundo: mude o ângulo ou use o modo retrato para desfocar."
    return resultado


# ---------------------------------------------------------------------------
# Critério 8: legenda (análise de texto)
# ---------------------------------------------------------------------------

PALAVRAS_CTA = [
    "comente", "comenta", "comentem", "marque", "marca", "marquem", "salve", "salva",
    "salvem", "compartilhe", "compartilha", "link na bio", "clique", "acesse", "confira",
    "me conta", "conta pra mim", "conta aqui", "deixe", "deixa", "siga", "segue", "ative",
    "manda pra", "envie", "responda", "vote", "curta", "arrasta", "arraste", "use o cupom",
]


def avaliar_legenda(legenda):
    """Regras de texto: tamanho, hashtags, pergunta e chamada para ação (CTA)."""
    texto = (legenda or "").strip()
    if not texto:
        return criterio(0, "Sem legenda",
                        "Sem legenda: escreva uma frase, faça uma pergunta e inclua hashtags.",
                        {"caracteres": 0, "hashtags": 0, "pergunta": False, "cta": False})

    minusculo = texto.lower()
    hashtags = re.findall(r"#\w+", texto)
    tem_pergunta = "?" in texto
    tem_cta = any(p in minusculo for p in PALAVRAS_CTA)
    tamanho = len(re.sub(r"#\w+", "", texto).strip())

    pontos = 0
    faltando = []
    if 40 <= tamanho <= 400:
        pontos += 25
    elif tamanho < 40:
        pontos += 10
        faltando.append("um texto um pouco maior")
    else:
        pontos += 15
        faltando.append("um texto mais curto")

    if 3 <= len(hashtags) <= 10:
        pontos += 25
    elif hashtags:
        pontos += 12
        faltando.append("entre 3 e 10 hashtags")
    else:
        faltando.append("hashtags (3 a 10)")

    if tem_pergunta:
        pontos += 25
    else:
        faltando.append("uma pergunta para o público")

    if tem_cta:
        pontos += 25
    else:
        faltando.append("uma chamada para ação (ex.: 'comente', 'salve')")

    dica = None
    if faltando:
        if len(faltando) == 1:
            lista = faltando[0]
        else:
            lista = ", ".join(faltando[:-1]) + " e " + faltando[-1]
        dica = f"Legenda: inclua {lista}."

    detalhe = (f"{tamanho} caracteres · {len(hashtags)} hashtags · "
               f"pergunta: {'sim' if tem_pergunta else 'não'} · CTA: {'sim' if tem_cta else 'não'}")
    return criterio(pontos, detalhe, dica, {"caracteres": tamanho, "hashtags": len(hashtags),
                                            "pergunta": tem_pergunta, "cta": tem_cta})


# ---------------------------------------------------------------------------
# Nota geral e dicas
# ---------------------------------------------------------------------------

def nota_geral(criterios):
    """Média ponderada pelos PESOS, ignorando critérios não avaliados."""
    soma, pesos = 0.0, 0.0
    for chave, peso in PESOS.items():
        nota = criterios.get(chave, {}).get("nota")
        if nota is not None:
            soma += nota * peso
            pesos += peso
    return round(soma / pesos) if pesos else 0


def classificar(nota):
    if nota >= 80:
        return "Ótima, pronta para postar"
    if nota >= 60:
        return "Boa, com ajustes"
    if nota >= 40:
        return "Regular, precisa de melhorias"
    return "Fraca, vale refazer a foto"


def montar_dicas(criterios):
    """Dicas ordenadas do pior critério para o melhor."""
    itens = [(c["nota"], chave, c["dica"]) for chave, c in criterios.items()
             if c.get("dica") and c.get("nota") is not None]
    itens.sort(key=lambda t: t[0])
    return [{"criterio": NOMES[chave], "nota": nota, "dica": dica} for nota, chave, dica in itens]


# ---------------------------------------------------------------------------
# Imagem anotada
# ---------------------------------------------------------------------------

def anotar(imagem, criterios, principal, grupo, fundo, nota=None):
    saida = imagem.copy()
    altura, largura = saida.shape[:2]
    espessura = max(2, largura // 400)

    # Grade da regra dos terços
    for i in (1, 2):
        x, y = int(largura * i / 3), int(altura * i / 3)
        cv2.line(saida, (x, 0), (x, altura), (255, 255, 255), 1, cv2.LINE_AA)
        cv2.line(saida, (0, y), (largura, y), (255, 255, 255), 1, cv2.LINE_AA)

    # Linhas usadas para medir o ângulo (azul)
    for x1, y1, x2, y2 in criterios["angulo"]["medida"]["linhas"][:15]:
        cv2.line(saida, (x1, y1), (x2, y2), (255, 160, 0), espessura, cv2.LINE_AA)

    # Rostos: principal em verde, grupo em amarelo, fundo em vermelho
    for (x, y, w, h), cor in ([(principal, (80, 200, 80))] if principal else []) + \
            [(r, (0, 200, 255)) for r in grupo] + [(r, (60, 60, 230)) for r in fundo]:
        cv2.rectangle(saida, (x, y), (x + w, y + h), cor, espessura + 1)

    if nota is not None:
        texto = f"BCY Lens: {nota}/100"
        escala = largura / 1000
        (tw, th), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, 2)
        cv2.rectangle(saida, (10, 10), (30 + tw, 30 + th), (40, 50, 35), -1)
        cv2.putText(saida, texto, (20, 20 + th), cv2.FONT_HERSHEY_SIMPLEX, escala,
                    (255, 255, 255), 2, cv2.LINE_AA)
    return saida


def para_base64(imagem, qualidade=85):
    ok, buffer = cv2.imencode(".jpg", imagem, [cv2.IMWRITE_JPEG_QUALITY, qualidade])
    return base64.b64encode(buffer).decode("ascii") if ok else None


# ---------------------------------------------------------------------------
# Análise de uma imagem (BGR já carregada)
# ---------------------------------------------------------------------------

def analisar_quadro(imagem_bgr):
    """Os 7 critérios visuais de uma imagem. Retorna (critérios, imagem, rostos)."""
    imagem, cinza, hsv, suavizada = preprocessar(imagem_bgr)
    altura, largura = cinza.shape

    principal, grupo, fundo = separar_rostos(detectar_rostos(cinza))
    criterios = {
        "iluminacao": avaliar_iluminacao(cinza),
        "contraste": avaliar_contraste(cinza),
        "nitidez": avaliar_nitidez(cinza),
        "cores": avaliar_cores(hsv),
        "angulo": avaliar_angulo(suavizada),
        "enquadramento": avaliar_enquadramento(principal, largura, altura),
        "pessoas_fundo": avaliar_pessoas_fundo(fundo),
    }
    return criterios, imagem, (principal, grupo, fundo)


def montar_resultado(criterios, tipo, imagem_anotada, extra=None):
    geral = nota_geral(criterios)
    resultado = {
        "tipo": tipo,
        "nota_geral": geral,
        "classificacao": classificar(geral),
        "criterios": [
            {"chave": chave, "nome": NOMES[chave], "peso": PESOS[chave],
             **{k: v for k, v in criterios[chave].items() if k != "medida" or chave != "angulo"}}
            for chave in PESOS
        ],
        "dicas": montar_dicas(criterios),
        "imagem_anotada": para_base64(imagem_anotada),
    }
    if extra:
        resultado.update(extra)
    return resultado


def analisar_imagem(caminho, legenda=""):
    imagem = cv2.imread(caminho)
    if imagem is None:
        raise ValueError("Não foi possível abrir a imagem. Use JPG, PNG ou WEBP.")
    return analisar_imagem_bgr(imagem, legenda)


def analisar_imagem_bgr(imagem, legenda=""):
    criterios, padronizada, (principal, grupo, fundo) = analisar_quadro(imagem)
    criterios["legenda"] = avaliar_legenda(legenda)
    geral = nota_geral(criterios)
    anotada = anotar(padronizada, criterios, principal, grupo, fundo, geral)
    return montar_resultado(criterios, "imagem", anotada)


# ---------------------------------------------------------------------------
# Análise de vídeo: amostra quadros, faz a média e escolhe o melhor quadro
# ---------------------------------------------------------------------------

def analisar_video(caminho, legenda="", quadros_por_segundo=2, max_quadros=60):
    captura = cv2.VideoCapture(caminho)
    if not captura.isOpened():
        raise ValueError("Não foi possível abrir o vídeo. Use MP4, MOV ou WEBM.")

    fps = captura.get(cv2.CAP_PROP_FPS) or 30
    total = int(captura.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    passo = max(1, int(round(fps / quadros_por_segundo)))
    if total and total / passo > max_quadros:
        passo = int(np.ceil(total / max_quadros))

    notas = {chave: [] for chave in PESOS if chave != "legenda"}
    melhor = None  # (nota, tempo, critérios, imagem, rostos)
    indice = 0
    while True:
        ok, quadro = captura.read()
        if not ok:
            break
        if indice % passo == 0:
            criterios, imagem, rostos = analisar_quadro(quadro)
            for chave, valor in criterios.items():
                if valor["nota"] is not None:
                    notas[chave].append(valor["nota"])
            nota_quadro = nota_geral(criterios)
            if melhor is None or nota_quadro > melhor[0]:
                melhor = (nota_quadro, indice / fps, criterios, imagem, rostos)
        indice += 1
    captura.release()

    if melhor is None:
        raise ValueError("O vídeo não tem quadros legíveis.")

    # Critérios do vídeo = média dos quadros; detalhe e dica vêm do quadro mais fraco
    _, tempo, criterios_melhor, imagem_melhor, (principal, grupo, fundo) = melhor
    criterios = {}
    for chave, lista in notas.items():
        base = dict(criterios_melhor[chave])
        if lista:
            media = float(np.mean(lista))
            base["nota"] = round(media)
            base["detalhe"] = (f"Média de {len(lista)} quadros "
                               f"(mín. {min(lista)}, máx. {max(lista)})")
            base["dica"] = base["dica"] or _dica_padrao(chave)
            base["dica"] = base["dica"] if media < NOTA_PARA_DICA else None
        else:
            base["nota"] = None
            base["detalhe"] = "Não avaliado em nenhum quadro"
            base["dica"] = None
        criterios[chave] = base
    criterios["legenda"] = avaliar_legenda(legenda)

    anotada = anotar(imagem_melhor, criterios_melhor, principal, grupo, fundo,
                     nota_geral(criterios_melhor))
    return montar_resultado(criterios, "video", anotada, {
        "quadros_analisados": len(notas["iluminacao"]),
        "duracao_segundos": round(indice / fps, 1),
        "melhor_quadro_segundos": round(tempo, 1),
    })


def _dica_padrao(chave):
    return {
        "iluminacao": "Iluminação irregular no vídeo: grave de frente para a luz natural.",
        "contraste": "Contraste fraco em parte do vídeo: escolha um fundo que destaque você.",
        "nitidez": "Trechos tremidos: apoie o celular ou use o estabilizador da câmera.",
        "cores": "Cores apagadas em parte do vídeo: busque cenários mais coloridos.",
        "angulo": "Vídeo torto em alguns trechos: ative a grade da câmera.",
        "enquadramento": "Mantenha o rosto na linha superior da grade durante o vídeo.",
        "pessoas_fundo": "Pessoas passando ao fundo: grave em um local mais reservado.",
    }[chave]


# ---------------------------------------------------------------------------
# Ponto de entrada único
# ---------------------------------------------------------------------------

EXTENSOES_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def analisar_arquivo(caminho, legenda=""):
    """Decide pela extensão se é foto ou vídeo."""
    extensao = os.path.splitext(caminho)[1].lower()
    if extensao in EXTENSOES_VIDEO:
        return analisar_video(caminho, legenda)
    return analisar_imagem(caminho, legenda)
