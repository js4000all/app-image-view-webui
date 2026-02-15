export type DirectoryEntry = {
  directory_id: string
  name: string
}

export type ImageEntry = {
  file_id: string
  name: string
}

export type ThumbnailState = {
  loading: boolean
  loaded: boolean
  images: ImageEntry[]
}
