import { fetchJson, putJson } from '../../../api/http'
import type { DirectoryEntry, ImageEntry } from '../../../types/home'

export async function fetchSubdirectories(): Promise<DirectoryEntry[]> {
  const data = await fetchJson<{ subdirectories: DirectoryEntry[] }>('/api/subdirectories')
  return data.subdirectories
}

export async function fetchDirectoryImages(directoryId: string): Promise<ImageEntry[]> {
  const data = await fetchJson<{ images: ImageEntry[] }>(`/api/images/${encodeURIComponent(directoryId)}`)
  return data.images
}

export async function renameSubdirectory(directoryId: string, newName: string): Promise<void> {
  await putJson(`/api/subdirectories/${encodeURIComponent(directoryId)}`, {
    new_name: newName
  })
}
