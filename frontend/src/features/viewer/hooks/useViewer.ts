import { useCallback, useMemo, useState } from 'react'

import { deleteViewerImage, fetchViewerDirectories, fetchViewerImages } from '../api/viewerApi'
import type { ViewerDirectoryEntry, ViewerImageEntry } from '../../../types/viewer'

type UseViewerState = {
  currentDirectory: ViewerDirectoryEntry | null
  images: ViewerImageEntry[]
  currentIndex: number
  status: string
}

export function useViewer() {
  const [state, setState] = useState<UseViewerState>({
    currentDirectory: null,
    images: [],
    currentIndex: -1,
    status: '読み込み中...'
  })

  const updateStatus = useCallback((status: string) => {
    setState((current) => ({ ...current, status }))
  }, [])

  const loadImages = useCallback(
    async (directory: ViewerDirectoryEntry) => {
      setState((current) => ({
        ...current,
        currentDirectory: directory,
        images: [],
        currentIndex: -1
      }))

      try {
        const images = await fetchViewerImages(directory.directory_id)
        if (images.length === 0) {
          setState((current) => ({
            ...current,
            currentDirectory: directory,
            images: [],
            currentIndex: -1,
            status: '画像が見つかりません。'
          }))
          return
        }

        setState((current) => ({
          ...current,
          currentDirectory: directory,
          images,
          currentIndex: 0,
          status: `1 / ${images.length}: ${images[0].name}`
        }))
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        setState((current) => ({
          ...current,
          currentDirectory: directory,
          images: [],
          currentIndex: -1,
          status: `画像一覧の取得に失敗しました: ${message}`
        }))
      }
    },
    []
  )

  const initialize = useCallback(async (requestedDirectoryId: string) => {
    try {
      const subdirectories = await fetchViewerDirectories()
      if (subdirectories.length === 0) {
        throw new Error('サブディレクトリがありません。')
      }

      const directory = requestedDirectoryId
        ? subdirectories.find((entry) => entry.directory_id === requestedDirectoryId)
        : subdirectories[0]

      if (!directory) {
        throw new Error('指定されたフォルダが見つかりません。')
      }

      await loadImages(directory)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      setState((current) => ({
        ...current,
        currentDirectory: null,
        images: [],
        currentIndex: -1,
        status: message
      }))
    }
  }, [loadImages])

  const moveNext = useCallback(() => {
    setState((current) => {
      if (current.images.length === 0) {
        return current
      }

      const nextIndex = (current.currentIndex + 1) % current.images.length
      const nextImage = current.images[nextIndex]
      return {
        ...current,
        currentIndex: nextIndex,
        status: `${nextIndex + 1} / ${current.images.length}: ${nextImage.name}`
      }
    })
  }, [])

  const movePrevious = useCallback(() => {
    setState((current) => {
      if (current.images.length === 0) {
        return current
      }

      const nextIndex = (current.currentIndex - 1 + current.images.length) % current.images.length
      const nextImage = current.images[nextIndex]
      return {
        ...current,
        currentIndex: nextIndex,
        status: `${nextIndex + 1} / ${current.images.length}: ${nextImage.name}`
      }
    })
  }, [])

  const deleteCurrentImage = useCallback(async () => {
    const currentImage = state.images[state.currentIndex]
    const currentDirectory = state.currentDirectory
    if (!currentDirectory || !currentImage) {
      return
    }

    try {
      await deleteViewerImage(currentImage.file_id)
      const reloadedImages = await fetchViewerImages(currentDirectory.directory_id)

      if (reloadedImages.length === 0) {
        setState((current) => ({
          ...current,
          images: [],
          currentIndex: -1,
          status: '画像が見つかりません。'
        }))
        return
      }

      const preservedIndex = reloadedImages.findIndex((image) => image.file_id === currentImage.file_id)
      const nextIndex = preservedIndex >= 0 ? preservedIndex : Math.min(state.currentIndex, reloadedImages.length - 1)
      setState((current) => ({
        ...current,
        images: reloadedImages,
        currentIndex: nextIndex,
        status: `画像を削除しました: ${currentImage.name}`
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      updateStatus(`画像の削除に失敗しました: ${message}`)
    }
  }, [state.currentDirectory, state.currentIndex, state.images, updateStatus])

  const currentImage = useMemo(() => {
    if (state.currentIndex < 0 || state.currentIndex >= state.images.length) {
      return null
    }

    return state.images[state.currentIndex]
  }, [state.currentIndex, state.images])

  const imageIndexText = useMemo(() => {
    if (!currentImage) {
      return '0 / 0'
    }

    return `${state.currentIndex + 1} / ${state.images.length}`
  }, [currentImage, state.currentIndex, state.images.length])

  const imageNameText = currentImage ? currentImage.name : ''

  return {
    currentDirectory: state.currentDirectory,
    currentImage,
    imageIndexText,
    imageNameText,
    status: state.status,
    canDelete: Boolean(currentImage),
    initialize,
    moveNext,
    movePrevious,
    deleteCurrentImage
  }
}
