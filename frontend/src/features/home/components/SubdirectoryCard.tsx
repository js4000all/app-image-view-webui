import { useCallback, useMemo, useState } from 'react'

import { renameSubdirectory } from '../api/homeApi'
import type { DirectoryEntry, ThumbnailState } from '../../../types/home'

type SubdirectoryCardProps = {
  subdirectory: DirectoryEntry
  thumbnailState: ThumbnailState | undefined
  registerCard: (directoryId: string, element: HTMLAnchorElement | null) => void
  onRenameComplete: (subdirectory: DirectoryEntry) => Promise<void>
}

export function SubdirectoryCard(props: SubdirectoryCardProps) {
  const { subdirectory, thumbnailState, registerCard, onRenameComplete } = props
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
      await renameSubdirectory(subdirectory.directory_id, trimmed)
      await onRenameComplete(subdirectory)
    } finally {
      setRenaming(false)
    }
  }, [onRenameComplete, subdirectory])

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
