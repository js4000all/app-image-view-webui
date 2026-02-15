import { fetchJson } from '../../../api/http'
import type { ViewerDirectoryEntry, ViewerImageEntry } from '../../../types/viewer'

export async function fetchViewerDirectories(): Promise<ViewerDirectoryEntry[]> {
  const data = await fetchJson<{ subdirectories: ViewerDirectoryEntry[] }>('/api/subdirectories')
  return data.subdirectories
}

export async function fetchViewerImages(directoryId: string): Promise<ViewerImageEntry[]> {
  const data = await fetchJson<{ images: ViewerImageEntry[] }>(`/api/images/${encodeURIComponent(directoryId)}`)
  return data.images
}

export async function deleteViewerImage(fileId: string): Promise<void> {
  const response = await fetch(`/api/image/${encodeURIComponent(fileId)}`, {
    method: 'DELETE'
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
}
