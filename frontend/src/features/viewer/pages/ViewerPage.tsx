import { useEffect } from 'react'

import { useViewer } from '../hooks/useViewer'

type ViewerPageProps = {
  requestedDirectoryId: string
  onNavigateHome: (directoryId: string) => void
}

export function ViewerPage(props: ViewerPageProps) {
  const { requestedDirectoryId, onNavigateHome } = props
  const {
    currentDirectory,
    currentImage,
    imageIndexText,
    imageNameText,
    status,
    canDelete,
    initialize,
    moveNext,
    movePrevious,
    deleteCurrentImage
  } = useViewer()

  useEffect(() => {
    void initialize(requestedDirectoryId)
  }, [initialize, requestedDirectoryId])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'ArrowRight') {
        moveNext()
      }

      if (event.key === 'ArrowLeft') {
        movePrevious()
      }

      if (event.key === 'Escape') {
        onNavigateHome(currentDirectory?.directory_id ?? '')
      }

      if (event.key === 'Delete') {
        void deleteCurrentImage()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [currentDirectory, deleteCurrentImage, moveNext, movePrevious, onNavigateHome])

  useEffect(() => {
    const handleWheel = (event: WheelEvent) => {
      if (event.deltaY === 0) {
        return
      }

      event.preventDefault()
      if (event.deltaY > 0) {
        moveNext()
        return
      }

      movePrevious()
    }

    const mainPane = document.querySelector('.main')
    mainPane?.addEventListener('wheel', handleWheel, { passive: false })

    return () => {
      mainPane?.removeEventListener('wheel', handleWheel)
    }
  }, [moveNext, movePrevious])

  return (
    <main className="main">
      <div className="image-stage">
        {currentImage ? (
          <img id="main-image" src={`/api/image/${encodeURIComponent(currentImage.file_id)}`} alt="画像プレビュー" style={{ display: "block" }} />
        ) : null}
        <p id="empty-message" style={{ display: currentImage ? 'none' : 'grid' }}>
          画像がありません
        </p>
        <div className="overlay-panel overlay-panel-left" aria-live="polite">
          <p id="image-index" className="overlay-line">{imageIndexText}</p>
          <div className="overlay-action-row">
            <a
              className="home-link home-icon-link"
              href="/"
              aria-label="ディレクトリ一覧へ戻る"
              title="ディレクトリ一覧へ戻る"
              onClick={(event) => {
                event.preventDefault()
                onNavigateHome(currentDirectory?.directory_id ?? '')
              }}
            >
              ⮌
            </a>
            <button
              id="delete-current-image"
              type="button"
              className="image-delete-button"
              disabled={!canDelete}
              onClick={() => void deleteCurrentImage()}
            >
              削除
            </button>
          </div>
        </div>
        <div className="overlay-panel overlay-panel-right" aria-live="polite">
          <p id="selected-subdir" className="overlay-line selected-subdir">
            {currentDirectory ? `フォルダ名: ${currentDirectory.name}` : 'フォルダ名: -'}
          </p>
          <p className="overlay-line image-name">
            ファイル名: <span id="image-name">{imageNameText || '-'}</span>
          </p>
          <p id="status" className="overlay-line status-message">
            ステータス: {status}
          </p>
        </div>
      </div>
      <p className="sr-only">{imageIndexText}</p>
    </main>
  )
}
