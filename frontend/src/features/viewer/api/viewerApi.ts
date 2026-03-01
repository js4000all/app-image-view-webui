import { DefaultService } from '../../../generated/api'
import type { ViewerDirectoryEntry, ViewerImageEntry, ViewerImageMetadata } from '../../../types/viewer'

export async function fetchViewerDirectories(): Promise<ViewerDirectoryEntry[]> {
  const data = await DefaultService.listSubdirectories()
  return data.subdirectories
}

export async function fetchViewerImages(directoryId: string): Promise<ViewerImageEntry[]> {
  const data = await DefaultService.listImages({ directoryId })
  return data.images
}

export async function fetchViewerImageMetadata(fileId: string): Promise<ViewerImageMetadata> {
  const data = await DefaultService.getImageMetadata({ fileId })
  return data
}

export async function deleteViewerImage(fileId: string): Promise<void> {
  await DefaultService.deleteImage({ fileId })
}
