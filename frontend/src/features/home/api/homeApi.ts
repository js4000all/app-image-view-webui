import { DefaultService } from '../../../generated/api'
import type { DirectoryEntry, ImageEntry } from '../../../types/home'

export async function fetchSubdirectories(): Promise<DirectoryEntry[]> {
  const data = await DefaultService.listSubdirectories()
  return data.subdirectories
}

export async function fetchDirectoryImages(directoryId: string): Promise<ImageEntry[]> {
  const data = await DefaultService.listImages({ directoryId })
  return data.images
}

export async function renameSubdirectory(directoryId: string, newName: string): Promise<void> {
  await DefaultService.renameSubdirectory({
    directoryId,
    requestBody: { new_name: newName }
  })
}
