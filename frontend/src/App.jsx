import { useEffect, useRef, useState } from 'react'
import './App.css'

const ACCEPTED = ['image/', 'video/']

function nivel(nota) {
  if (nota === null || nota === undefined) return 'na'
  if (nota >= 80) return 'alta'
  if (nota >= 60) return 'media'
  return 'baixa'
}

function App() {
  const [media, setMedia] = useState(null) // { url, type, name, size, file }
  const [legenda, setLegenda] = useState('')
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [analisando, setAnalisando] = useState(false)
  const [resultado, setResultado] = useState(null)
  const inputRef = useRef(null)
  const insightsRef = useRef(null)

  // Libera a URL temporária quando o arquivo é trocado ou removido
  useEffect(() => {
    return () => {
      if (media?.url) URL.revokeObjectURL(media.url)
    }
  }, [media])

  function handleFile(file) {
    if (!file) return
    if (!ACCEPTED.some((t) => file.type.startsWith(t))) {
      setError('Formato não suportado. Envie uma imagem ou um vídeo.')
      return
    }
    setError('')
    setResultado(null)
    setMedia({
      url: URL.createObjectURL(file),
      type: file.type.startsWith('video/') ? 'video' : 'image',
      name: file.name,
      size: file.size,
      file,
    })
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  function clearMedia() {
    setMedia(null)
    setResultado(null)
    setError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  function formatSize(bytes) {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  async function analisar() {
    if (!media) return
    setAnalisando(true)
    setError('')
    setResultado(null)

    const dados = new FormData()
    dados.append('arquivo', media.file)
    dados.append('legenda', legenda)

    try {
      const resposta = await fetch('/api/analisar', { method: 'POST', body: dados })
      const json = await resposta.json().catch(() => null)
      // Sem JSON = o proxy do Vite não achou o backend
      if (!json) throw new TypeError('offline')
      if (!resposta.ok) throw new Error(json.erro || 'Erro ao analisar o arquivo.')
      setResultado(json)
      requestAnimationFrame(() =>
        insightsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      )
    } catch (e) {
      setError(
        e instanceof TypeError
          ? 'Não foi possível falar com o servidor de análise. Ele está rodando? (python app.py na pasta backend)'
          : e.message,
      )
    } finally {
      setAnalisando(false)
    }
  }

  return (
    <>
      <header className="topbar">
        <span className="brand">
          BCY<span className="brand-accent">Lens</span>
        </span>
        <span className="topbar-tag">Análise de imagem e vídeo</span>
      </header>

      <main className="content">
        {/* ---------- Área principal: upload ---------- */}
        <section className="upload-section" aria-labelledby="upload-title">
          <div className="section-head">
            <h1 id="upload-title">Envie sua mídia</h1>
            <p>Arraste uma foto ou um vídeo, escreva a legenda e veja a nota antes de postar.</p>
          </div>

          {!media ? (
            <label
              className={`dropzone ${dragging ? 'is-dragging' : ''}`}
              onDragOver={(e) => {
                e.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
            >
              <input
                ref={inputRef}
                type="file"
                accept="image/*,video/*"
                onChange={(e) => handleFile(e.target.files?.[0])}
                hidden
              />
              <svg
                className="dropzone-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M12 16V4" />
                <path d="m7 9 5-5 5 5" />
                <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
              </svg>
              <span className="dropzone-title">Solte o arquivo aqui</span>
              <span className="dropzone-hint">JPG, PNG, WEBP, MP4, MOV…</span>
              <span className="btn">Escolher arquivo</span>
            </label>
          ) : (
            <div className="preview">
              <div className="preview-frame">
                {media.type === 'image' ? (
                  <img src={media.url} alt={media.name} />
                ) : (
                  <video src={media.url} controls />
                )}
              </div>
              <div className="preview-bar">
                <div className="preview-info">
                  <span className="badge">
                    {media.type === 'image' ? 'Imagem' : 'Vídeo'}
                  </span>
                  <span className="file-name" title={media.name}>
                    {media.name}
                  </span>
                  <span className="file-size">{formatSize(media.size)}</span>
                </div>
                <button type="button" className="btn btn-ghost" onClick={clearMedia}>
                  Trocar arquivo
                </button>
              </div>
            </div>
          )}

          {/* ---------- Legenda + botão de análise ---------- */}
          <div className="caption-box">
            <label htmlFor="legenda" className="caption-label">
              Legenda do post
            </label>
            <textarea
              id="legenda"
              className="caption-input"
              rows={3}
              placeholder="Ex.: Look do dia! Qual vocês preferem, 1 ou 2? Comenta aqui #moda #ootd #lookdodia"
              value={legenda}
              onChange={(e) => setLegenda(e.target.value)}
            />
            <div className="caption-actions">
              <span className="caption-count">{legenda.length} caracteres</span>
              <button
                type="button"
                className="btn btn-analyze"
                onClick={analisar}
                disabled={!media || analisando}
              >
                {analisando
                  ? media?.type === 'video'
                    ? 'Analisando vídeo…'
                    : 'Analisando…'
                  : 'Analisar'}
              </button>
            </div>
          </div>

          {error && <p className="error">{error}</p>}
        </section>

        {/* ---------- Insights ---------- */}
        <section
          className="insights-section"
          aria-labelledby="insights-title"
          ref={insightsRef}
        >
          <h2 id="insights-title">Insights</h2>

          {!resultado ? (
            <p className="insights-text insights-empty">
              {analisando
                ? 'Processando a mídia: iluminação, contraste, nitidez, cores, ângulo, enquadramento, pessoas ao fundo e legenda…'
                : 'Envie uma foto ou um vídeo e clique em “Analisar” para ver a nota de cada critério e as dicas de melhoria.'}
            </p>
          ) : (
            <Resultado r={resultado} />
          )}
        </section>
      </main>

      {/* ---------- Rodapé ---------- */}
      <footer className="footer">
        <span>© {new Date().getFullYear()} BCY Lens</span>
        <span>Ciência da Computação · UNASP</span>
      </footer>
    </>
  )
}

function Resultado({ r }) {
  return (
    <div className="result">
      <div className="result-top">
        <div className={`score score-${nivel(r.nota_geral)}`}>
          <span className="score-value">{r.nota_geral}</span>
          <span className="score-label">nota geral</span>
        </div>
        <div className="score-text">
          <p className="score-class">{r.classificacao}</p>
          {r.tipo === 'video' ? (
            <p>
              Vídeo de {r.duracao_segundos} s · {r.quadros_analisados} quadros analisados.
              Melhor quadro para capa em <strong>{r.melhor_quadro_segundos} s</strong>.
            </p>
          ) : (
            <p>Média ponderada dos 8 critérios. Corrija primeiro as dicas do topo.</p>
          )}
        </div>
      </div>

      <div className="result-grid">
        <div>
          <h3 className="result-h">Notas por critério</h3>
          <ul className="criteria">
            {r.criterios.map((c) => (
              <li key={c.chave} className="criterion">
                <div className="criterion-head">
                  <span className="criterion-name">{c.nome}</span>
                  <span className={`criterion-score lvl-${nivel(c.nota)}`}>
                    {c.nota ?? '—'}
                  </span>
                </div>
                <div className="bar">
                  <div
                    className={`bar-fill lvl-${nivel(c.nota)}`}
                    style={{ width: `${c.nota ?? 0}%` }}
                  />
                </div>
                <span className="criterion-detail">{c.detalhe}</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="result-h">Dicas</h3>
          {r.dicas.length ? (
            <ol className="tips">
              {r.dicas.map((d) => (
                <li key={d.criterio}>
                  <span className={`tip-tag lvl-${nivel(d.nota)}`}>{d.criterio}</span>
                  {d.dica}
                </li>
              ))}
            </ol>
          ) : (
            <p>Nenhum ajuste necessário: pode postar!</p>
          )}

          {r.imagem_anotada && (
            <figure className="annotated">
              <img
                src={`data:image/jpeg;base64,${r.imagem_anotada}`}
                alt="Imagem analisada com a grade dos terços e os rostos marcados"
              />
              <figcaption>
                {r.tipo === 'video' ? 'Melhor quadro do vídeo. ' : ''}
                Verde: rosto principal · amarelo: outras pessoas em primeiro plano · vermelho: pessoas ao fundo · azul: linhas usadas
                para medir o ângulo · branco: grade dos terços.
              </figcaption>
            </figure>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
