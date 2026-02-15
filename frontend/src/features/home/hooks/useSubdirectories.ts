import { useCallback, useEffect, useState } from 'react'

import { fetchSubdirectories } from '../api/homeApi'
import type { DirectoryEntry } from '../../../types/home'

type UseSubdirectoriesResult = {
  subdirectories: DirectoryEntry[]
  status: string
  loading: boolean
  refreshSubdirectories: () => Promise<void>
  setStatus: (value: string) => void
}

export function useSubdirectories(): UseSubdirectoriesResult {
  const [subdirectories, setSubdirectories] = useState<DirectoryEntry[]>([])
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  const refreshSubdirectories = useCallback(async () => {
    setLoading(true)
    setStatus('読み込み中...')

    try {
      const items = await fetchSubdirectories()
      setSubdirectories(items)

      if (items.length === 0) {
        setStatus('サブディレクトリがありません。')
      } else {
        setStatus(`${items.length} 件のサブディレクトリがあります。`)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      setStatus(`サブディレクトリ一覧の取得に失敗しました: ${message}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshSubdirectories()
  }, [refreshSubdirectories])

  return {
    subdirectories,
    status,
    loading,
    refreshSubdirectories,
    setStatus
  }
}
