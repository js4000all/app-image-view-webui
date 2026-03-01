import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  deleteViewerImage,
  fetchViewerDirectories,
  fetchViewerImageMetadata,
  fetchViewerImages,
} from '../api/viewerApi'
import type { ViewerImageEntry, ViewerImageMetadata } from '../../../types/viewer'

export type ViewerFileIdListProvider = () => Promise<string[]>
export type ViewerImageMetadataProvider = (fileId: string) => Promise<ViewerImageMetadata>
export type ViewerImageDeleteHandler = (fileId: string) => Promise<void>

type UseViewerOptions = {
  listFileIds?: ViewerFileIdListProvider
  getImageMetadata?: ViewerImageMetadataProvider
  deleteImageById?: ViewerImageDeleteHandler
  allowImageDelete?: boolean
}

type UseViewerState = {
  fileIds: string[]
  metadataByFileId: Record<string, ViewerImageMetadata>
  currentIndex: number
  status: string
}

async function resolveDefaultFileIds(): Promise<string[]> {
  const subdirectories = await fetchViewerDirectories()
  if (subdirectories.length === 0) {
    return []
  }

  const images = await fetchViewerImages(subdirectories[0].directory_id)
  return images.map((image) => image.file_id)
}

function toStatus(index: number, total: number, fileId: string, metadataByFileId: Record<string, ViewerImageMetadata>): string {
  const name = metadataByFileId[fileId]?.name ?? fileId
  return `${index + 1} / ${total}: ${name}`
}

export function useViewer(options: UseViewerOptions = {}) {
  const {
    listFileIds = resolveDefaultFileIds,
    getImageMetadata = fetchViewerImageMetadata,
    deleteImageById = deleteViewerImage,
    allowImageDelete = true,
  } = options

  const [state, setState] = useState<UseViewerState>({
    fileIds: [],
    metadataByFileId: {},
    currentIndex: -1,
    status: '読み込み中...',
  })

  const updateStatus = useCallback((status: string) => {
    setState((current) => ({ ...current, status }))
  }, [])

  const loadImages = useCallback(async () => {
    setState((current) => ({
      ...current,
      fileIds: [],
      currentIndex: -1,
    }))

    try {
      const fileIds = await listFileIds()
      if (fileIds.length === 0) {
        setState((current) => ({
          ...current,
          fileIds: [],
          currentIndex: -1,
          status: '画像が見つかりません。',
        }))
        return
      }

      const firstFileId = fileIds[0]
      setState((current) => ({
        ...current,
        fileIds,
        currentIndex: 0,
        status: toStatus(0, fileIds.length, firstFileId, current.metadataByFileId),
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      setState((current) => ({
        ...current,
        fileIds: [],
        currentIndex: -1,
        status: `画像一覧の取得に失敗しました: ${message}`,
      }))
    }
  }, [listFileIds])

  const initialize = useCallback(async () => {
    await loadImages()
  }, [loadImages])

  const ensureMetadata = useCallback(
    async (fileId: string) => {
      if (!fileId) {
        return
      }

      if (state.metadataByFileId[fileId]) {
        return
      }

      try {
        const metadata = await getImageMetadata(fileId)
        setState((current) => {
          if (current.metadataByFileId[fileId]) {
            return current
          }

          const metadataByFileId = {
            ...current.metadataByFileId,
            [fileId]: metadata,
          }

          if (current.currentIndex < 0 || current.currentIndex >= current.fileIds.length) {
            return {
              ...current,
              metadataByFileId,
            }
          }

          const currentFileId = current.fileIds[current.currentIndex]
          return {
            ...current,
            metadataByFileId,
            status: toStatus(current.currentIndex, current.fileIds.length, currentFileId, metadataByFileId),
          }
        })
      } catch {
        // metadata resolution is best-effort
      }
    },
    [getImageMetadata, state.metadataByFileId]
  )

  const currentFileId = useMemo(() => {
    if (state.currentIndex < 0 || state.currentIndex >= state.fileIds.length) {
      return ''
    }

    return state.fileIds[state.currentIndex]
  }, [state.currentIndex, state.fileIds])

  useEffect(() => {
    void ensureMetadata(currentFileId)
  }, [currentFileId, ensureMetadata])

  const moveNext = useCallback(() => {
    void (async () => {
      if (state.fileIds.length === 0) {
        return
      }

      if (state.currentIndex < state.fileIds.length - 1) {
        const nextIndex = state.currentIndex + 1
        const nextFileId = state.fileIds[nextIndex]
        setState((current) => ({
          ...current,
          currentIndex: nextIndex,
          status: toStatus(nextIndex, current.fileIds.length, nextFileId, current.metadataByFileId),
        }))
        return
      }

      try {
        const latestFileIds = await listFileIds()
        if (latestFileIds.length === 0) {
          setState((current) => ({
            ...current,
            fileIds: [],
            currentIndex: -1,
            status: '画像が見つかりません。',
          }))
          return
        }

        const nextIndex = (state.currentIndex + 1) % latestFileIds.length
        const nextFileId = latestFileIds[nextIndex]
        setState((current) => ({
          ...current,
          fileIds: latestFileIds,
          currentIndex: nextIndex,
          status: toStatus(nextIndex, latestFileIds.length, nextFileId, current.metadataByFileId),
        }))
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        updateStatus(`画像一覧の更新に失敗しました: ${message}`)
      }
    })()
  }, [listFileIds, state.currentIndex, state.fileIds.length, updateStatus])

  const movePrevious = useCallback(() => {
    setState((current) => {
      if (current.fileIds.length === 0) {
        return current
      }

      const nextIndex = (current.currentIndex - 1 + current.fileIds.length) % current.fileIds.length
      const nextFileId = current.fileIds[nextIndex]
      return {
        ...current,
        currentIndex: nextIndex,
        status: toStatus(nextIndex, current.fileIds.length, nextFileId, current.metadataByFileId),
      }
    })
  }, [])

  const deleteCurrentImage = useCallback(async () => {
    if (!allowImageDelete) {
      updateStatus('絞り込み画像の閲覧モードでは削除できません。')
      return
    }

    const currentFileId = state.fileIds[state.currentIndex]
    if (!currentFileId) {
      return
    }

    try {
      await deleteImageById(currentFileId)
      const reloadedFileIds = await listFileIds()
      if (reloadedFileIds.length === 0) {
        setState((current) => ({
          ...current,
          fileIds: [],
          currentIndex: -1,
          status: '画像が見つかりません。',
        }))
        return
      }

      const preservedIndex = reloadedFileIds.findIndex((fileId) => fileId === currentFileId)
      const nextIndex = preservedIndex >= 0 ? preservedIndex : Math.min(state.currentIndex, reloadedFileIds.length - 1)
      const nextFileId = reloadedFileIds[nextIndex]
      setState((current) => ({
        ...current,
        fileIds: reloadedFileIds,
        currentIndex: nextIndex,
        status: `画像を削除しました。現在: ${current.metadataByFileId[nextFileId]?.name ?? nextFileId}`,
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      updateStatus(`画像の削除に失敗しました: ${message}`)
    }
  }, [allowImageDelete, deleteImageById, listFileIds, state.currentIndex, state.fileIds, updateStatus])

  const currentImage = useMemo<ViewerImageEntry | null>(() => {
    if (!currentFileId) {
      return null
    }

    return {
      file_id: currentFileId,
      name: state.metadataByFileId[currentFileId]?.name ?? currentFileId,
    }
  }, [currentFileId, state.metadataByFileId])

  const imageIndexText = useMemo(() => {
    if (!currentImage) {
      return '0 / 0'
    }

    return `${state.currentIndex + 1} / ${state.fileIds.length}`
  }, [currentImage, state.currentIndex, state.fileIds.length])

  const imageNameText = currentImage ? currentImage.name : ''
  const currentImageDirectoryName = currentFileId ? state.metadataByFileId[currentFileId]?.directory_name ?? '' : ''

  return {
    currentImageDirectoryName,
    currentImage,
    imageIndexText,
    imageNameText,
    status: state.status,
    canDelete: allowImageDelete && Boolean(currentImage),
    initialize,
    moveNext,
    movePrevious,
    deleteCurrentImage,
  }
}
