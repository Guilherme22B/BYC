import { useEffect, useRef, useState } from 'react'
import './App.css'

const ACCEPTED = ['image/', 'video/']

function App() {
  const [media, setMedia] = useState(null) // { url, type, name, size }
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

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
    setMedia({
      url: URL.createObjectURL(file),
      type: file.type.startsWith('video/') ? 'video' : 'image',
      name: file.name,
      size: file.size,
    })
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  function clearMedia() {
    setMedia(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  function formatSize(bytes) {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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
            <p>Arraste uma imagem ou um vídeo, ou clique para selecionar.</p>
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

          {error && <p className="error">{error}</p>}
        </section>

        {/* ---------- Insights (em branco, para preencher depois) ---------- */}
        <section className="insights-section" aria-labelledby="insights-title">
          <h2 id="insights-title">Insights</h2>
          <p className="insights-text"></p>
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

export default App
