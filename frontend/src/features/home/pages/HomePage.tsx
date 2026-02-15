import { useCallback } from 'react'

import { SubdirectoryCard } from '../components/SubdirectoryCard'
import { useSubdirectories } from '../hooks/useSubdirectories'
import { useSubdirectoryThumbnails } from '../hooks/useSubdirectoryThumbnails'
import type { DirectoryEntry } from '../../../types/home'

export function HomePage() {
  const { subdirectories, status, loading, refreshSubdirectories, setStatus } = useSubdirectories()
  const { thumbnails, registerCard, resetThumbnails } = useSubdirectoryThumbnails(subdirectories)

  const handleReload = useCallback(async () => {
    await refreshSubdirectories()
    resetThumbnails()
  }, [refreshSubdirectories, resetThumbnails])

  const handleRenameComplete = useCallback(
    async (subdirectory: DirectoryEntry) => {
      await refreshSubdirectories()
      resetThumbnails()
      setStatus(`「${subdirectory.name}」の名前変更を反映しました。`)
    },
    [refreshSubdirectories, resetThumbnails, setStatus]
  )

  return (
    <main className="home">
      <h1>サブディレクトリ一覧</h1>
      <p className="home-description">閲覧するフォルダを選択してください。</p>
      <button
        id="reload-subdirs"
        type="button"
        className="reload-button"
        onClick={() => void handleReload()}
        disabled={loading}
      >
        再読み込み
      </button>
      <ul id="subdir-list" className="subdir-list" aria-live="polite">
        {subdirectories.map((subdirectory) => (
          <SubdirectoryCard
            key={subdirectory.directory_id}
            subdirectory={subdirectory}
            registerCard={registerCard}
            thumbnailState={thumbnails[subdirectory.directory_id]}
            onRenameComplete={handleRenameComplete}
          />
        ))}
      </ul>
      <p id="home-status" className="home-status">
        {status}
      </p>
    </main>
  )
}
