import { useCallback, useEffect, useRef, useState } from 'react'

import { fetchDirectoryImages } from '../api/homeApi'
import type { DirectoryEntry, ThumbnailState } from '../../../types/home'

type UseSubdirectoryThumbnailsResult = {
  thumbnails: Record<string, ThumbnailState>
  registerCard: (directoryId: string, element: HTMLAnchorElement | null) => void
  resetThumbnails: () => void
}

export function useSubdirectoryThumbnails(
  subdirectories: DirectoryEntry[]
): UseSubdirectoryThumbnailsResult {
  const [thumbnails, setThumbnails] = useState<Record<string, ThumbnailState>>({})
  const cardElements = useRef<Record<string, HTMLAnchorElement | null>>({})
  const observerRef = useRef<IntersectionObserver | null>(null)

  const resetThumbnails = useCallback(() => {
    setThumbnails({})
  }, [])

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
      const images = await fetchDirectoryImages(subdirectory.directory_id)
      setThumbnails((current) => ({
        ...current,
        [subdirectory.directory_id]: {
          loading: false,
          loaded: true,
          images: images.slice(0, 5)
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

  return {
    thumbnails,
    registerCard,
    resetThumbnails
  }
}
