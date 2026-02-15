import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

type DirectoryEntry = {
  directory_id: string
  name: string
}

type ImageEntry = {
  file_id: string
  name: string
}

type ThumbnailState = {
  loading: boolean
  loaded: boolean
  images: ImageEntry[]
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

async function putJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json() as Promise<T>
}

function SubdirectoryCard(props: {
  subdirectory: DirectoryEntry
  onRename: (subdirectory: DirectoryEntry) => Promise<void>
  registerCard: (directoryId: string, element: HTMLAnchorElement | null) => void
  thumbnailState: ThumbnailState | undefined
}) {
  const { subdirectory, onRename, registerCard, thumbnailState } = props
  const [renaming, setRenaming] = useState(false)

  const thumbnailContent = useMemo(() => {
    if (!thumbnailState || thumbnailState.loading) {
      return <p className="subdir-loading">画像を読み込み中...</p>
    }

    if (thumbnailState.images.length === 0) {
      return <p className="subdir-no-images">画像なし</p>
    }

    return thumbnailState.images.map((image) => (
      <div key={image.file_id} className="subdir-thumb-slot">
        <img
          className="subdir-thumb"
          loading="lazy"
          decoding="async"
          src={`/api/image/${encodeURIComponent(image.file_id)}`}
          alt={`${subdirectory.name} のサムネイル ${image.name}`}
        />
      </div>
    ))
  }, [subdirectory.name, thumbnailState])

  const handleRename = useCallback(async () => {
    const newName = window.prompt('新しいディレクトリ名を入力してください。', subdirectory.name)
    if (newName === null) {
      return
    }

    const trimmed = newName.trim()
    if (!trimmed || trimmed === subdirectory.name) {
      return
    }

    setRenaming(true)
    try {
      await putJson(`/api/subdirectories/${encodeURIComponent(subdirectory.directory_id)}`, {
        new_name: trimmed
      })
      await onRename(subdirectory)
    } finally {
      setRenaming(false)
    }
  }, [onRename, subdirectory])

  return (
    <li>
      <div className="subdir-row">
        <a
          className="subdir-card"
          href={`/viewer?directory_id=${encodeURIComponent(subdirectory.directory_id)}`}
          ref={(element) => registerCard(subdirectory.directory_id, element)}
        >
          <div className="subdir-meta">
            <p className="subdir-name">{subdirectory.name}</p>
          </div>
          <div className="subdir-thumbs">{thumbnailContent}</div>
        </a>
        <button
          type="button"
          className="subdir-rename-button"
          onClick={() => void handleRename()}
          disabled={renaming}
        >
          名前変更
        </button>
      </div>
    </li>
  )
}

export function App() {
  const [subdirectories, setSubdirectories] = useState<DirectoryEntry[]>([])
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [thumbnails, setThumbnails] = useState<Record<string, ThumbnailState>>({})
  const cardElements = useRef<Record<string, HTMLAnchorElement | null>>({})
  const observerRef = useRef<IntersectionObserver | null>(null)

  const loadThumbnails = useCallback(async (subdirectory: DirectoryEntry) => {
    setThumbnails((current) => {
      if (current[subdirectory.directory_id]?.loaded || current[subdirectory.directory_id]?.loading) {
        return current
      }
      return {
        ...current,
        [subdirectory.directory_id]: { loading: true, loaded: false, images: [] }
      }
    })

    try {
      const data = await fetchJson<{ images: ImageEntry[] }>(
        `/api/images/${encodeURIComponent(subdirectory.directory_id)}`
      )
      setThumbnails((current) => ({
        ...current,
        [subdirectory.directory_id]: {
          loading: false,
          loaded: true,
          images: data.images.slice(0, 5)
        }
      }))
    } catch {
      setThumbnails((current) => ({
        ...current,
        [subdirectory.directory_id]: {
          loading: false,
          loaded: true,
          images: []
        }
      }))
    }
  }, [])

  const refreshSubdirectories = useCallback(async () => {
    setLoading(true)
    setStatus('読み込み中...')

    try {
      const data = await fetchJson<{ subdirectories: DirectoryEntry[] }>('/api/subdirectories')
      setSubdirectories(data.subdirectories)
      setThumbnails({})

      if (data.subdirectories.length === 0) {
        setStatus('サブディレクトリがありません。')
      } else {
        setStatus(`${data.subdirectories.length} 件のサブディレクトリがあります。`)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      setStatus(`サブディレクトリ一覧の取得に失敗しました: ${message}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshSubdirectories()
  }, [refreshSubdirectories])

  useEffect(() => {
    observerRef.current?.disconnect()

    if (!('IntersectionObserver' in window)) {
      subdirectories.forEach((subdirectory) => {
        void loadThumbnails(subdirectory)
      })
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return
          }

          const directoryId = (entry.target as HTMLAnchorElement).dataset.directoryId
          if (!directoryId) {
            return
          }

          const subdirectory = subdirectories.find((item) => item.directory_id === directoryId)
          if (!subdirectory) {
            return
          }

          void loadThumbnails(subdirectory)
          observer.unobserve(entry.target)
        })
      },
      { root: null, rootMargin: '120px 0px', threshold: 0.1 }
    )

    observerRef.current = observer

    subdirectories.forEach((subdirectory) => {
      const cardElement = cardElements.current[subdirectory.directory_id]
      if (cardElement) {
        observer.observe(cardElement)
      }
    })

    return () => observer.disconnect()
  }, [loadThumbnails, subdirectories])

  const registerCard = useCallback((directoryId: string, element: HTMLAnchorElement | null) => {
    cardElements.current[directoryId] = element
    if (element) {
      element.dataset.directoryId = directoryId
    }
  }, [])

  const handleRenameComplete = useCallback(
    async (subdirectory: DirectoryEntry) => {
      await refreshSubdirectories()
      setStatus(`「${subdirectory.name}」の名前変更を反映しました。`)
    },
    [refreshSubdirectories]
  )

  return (
    <main className="home">
      <h1>サブディレクトリ一覧</h1>
      <p className="home-description">閲覧するフォルダを選択してください。</p>
      <button
        id="reload-subdirs"
        type="button"
        className="reload-button"
        onClick={() => void refreshSubdirectories()}
        disabled={loading}
      >
        再読み込み
      </button>
      <ul id="subdir-list" className="subdir-list" aria-live="polite">
        {subdirectories.map((subdirectory) => (
          <SubdirectoryCard
            key={subdirectory.directory_id}
            subdirectory={subdirectory}
            onRename={handleRenameComplete}
            registerCard={registerCard}
            thumbnailState={thumbnails[subdirectory.directory_id]}
          />
        ))}
      </ul>
      <p id="home-status" className="home-status">
        {status}
      </p>
    </main>
  )
}
