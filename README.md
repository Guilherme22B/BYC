# BCY Lens

Sistema que analisa uma foto ou um vídeo **antes da postagem**. Ele devolve uma nota de 0 a 100 para cada um de 8 critérios, a nota geral e dicas práticas para melhorar o engajamento.

Projeto Final de Processamento de Imagens · Ciência da Computação · UNASP

## Estrutura

```
bcy-lens/
├── backend/                 Python + OpenCV
│   ├── analise.py           núcleo: os 8 critérios, nota geral, dicas, imagem anotada
│   ├── app.py               API Flask usada pelo site (porta 5000)
│   ├── analisar.py          versão de terminal (plano B na demonstração)
│   ├── requirements.txt
│   └── experimentos/
│       └── analise_original_yolo.py   primeiro teste do grupo (YOLO), fora do sistema final
├── frontend/                site React + Vite
│   ├── src/App.jsx          upload, legenda, botão Analisar e seção Insights
│   └── vite.config.js       redireciona /api para o backend
└── apresentacao/
    └── BCY_Lens.pptx        slides atualizados
```

## Como rodar

São **dois terminais**: um para o backend e outro para o site.

### Terminal 1: backend (Python 3.10+)

```bash
cd backend
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Deve aparecer `Running on http://127.0.0.1:5000`. Deixe esse terminal aberto.

### Terminal 2: site (Node.js 20.19+ ou 22.12+)

```bash
cd frontend
npm install
npm run dev
```

Abra **http://localhost:5173**, envie uma foto ou um vídeo, escreva a legenda e clique em **Analisar**.

### Só pelo terminal (sem site)

```bash
cd backend
python analisar.py caminho/da/foto.jpg --legenda "Look do dia! Qual vocês preferem? Comenta aqui #moda #ootd #lookdodia"
python analisar.py caminho/do/video.mp4 --legenda "..."
python analisar.py foto.jpg --json        # resultado completo em JSON
```

O comando mostra as notas e as dicas no terminal e salva a imagem anotada como `<nome>_bcylens.jpg`.

## Os 8 critérios

| Critério | Técnica (OpenCV) | Função em `analise.py` | Peso |
|---|---|---|---|
| Iluminação | Histograma (`calcHist`): brilho médio, áreas estouradas e escuras | `avaliar_iluminacao` | 15 |
| Contraste | Desvio padrão da intensidade | `avaliar_contraste` | 10 |
| Nitidez | Variância do Laplaciano (`Laplacian`) | `avaliar_nitidez` | 15 |
| Cores | Saturação média no espaço HSV (`cvtColor`) | `avaliar_cores` | 10 |
| Ângulo | `GaussianBlur` + `Canny` + `HoughLinesP`, mediana da inclinação | `avaliar_angulo` | 10 |
| Enquadramento | Rosto principal (Haar) × pontos da regra dos terços | `avaliar_enquadramento` | 15 |
| Pessoas ao fundo | Rostos menores que 40% do principal (`CascadeClassifier`) | `avaliar_pessoas_fundo` | 10 |
| Legenda | Tamanho, hashtags, pergunta e chamada para ação | `avaliar_legenda` | 15 |

- **Pré-processamento:** a imagem é reduzida para no máximo 1080 px no lado maior (`resize`) e convertida para cinza e HSV.
- **Nota geral:** média ponderada pelos pesos acima. Um critério que não pôde ser avaliado (por exemplo, enquadramento sem rosto) fica de fora da média.
- **Classificação:** 80 ou mais = "Ótima, pronta para postar" · 60 a 79 = "Boa, com ajustes" · 40 a 59 = "Regular" · abaixo de 40 = "Fraca".
- **Dicas:** aparecem para cada critério com nota abaixo de 70, da pior para a melhor.
- **Vídeo:** são analisados cerca de 2 quadros por segundo (no máximo 60). Cada nota é a média dos quadros, e o sistema indica o **melhor quadro para usar como capa**.

## Problemas comuns

- **"Não foi possível falar com o servidor de análise"**: o backend não está rodando. Rode `python app.py` no terminal 1.
- **"Classificador de rostos não encontrado"**: o detector Haar vem junto com o `opencv-python` 4.x. Instale com `pip install -r requirements.txt`, que já fixa a versão 4.
- **Vídeo .mov não abre**: depende dos codecs do computador. Se acontecer, converta para .mp4.
