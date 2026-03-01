import { useCallback, useEffect, useMemo, useState } from 'react'

import { fetchTagSummaries } from '../../home/api/homeApi'

export type TagSummary = {
  tag: string
  count: number
}

type FilterPageProps = {
  selectedTag: string
  onChangeTag: (tag: string) => void
  onOpenViewer: (tag: string) => void
}

export function FilterPage(props: FilterPageProps) {
  const { selectedTag, onChangeTag, onOpenViewer } = props
  const [tags, setTags] = useState<TagSummary[]>([])
  const [status, setStatus] = useState('タグを読み込み中...')

  const loadTags = useCallback(async () => {
    try {
      const summaries = await fetchTagSummaries()
      setTags(summaries)
      setStatus(summaries.length === 0 ? 'タグがありません。' : `${summaries.length}件のタグを表示しています。`)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      setStatus(`タグ一覧の取得に失敗しました: ${message}`)
    }
  }, [])

  useEffect(() => {
    void loadTags()
  }, [loadTags])

  const selectedSummary = useMemo(
    () => tags.find((tag) => tag.tag === selectedTag),
    [selectedTag, tags]
  )
  const canOpenViewer = Boolean(selectedSummary && selectedSummary.count <= 200)

  return (
    <main className="filter">
      <h1>タグ絞り込み（暫定版）</h1>
      <p className="home-description">タグを1つ選択し、対象画像だけを閲覧します。</p>
      <div className="filter-toolbar">
        <a href="/" className="home-link">ホームへ戻る</a>
        <button
          id="open-filter-viewer"
          type="button"
          className="reload-button"
          onClick={() => selectedTag && onOpenViewer(selectedTag)}
          disabled={!canOpenViewer}
        >
          閲覧
        </button>
      </div>
      <div className="tag-button-list" aria-live="polite">
        {tags.map((tag) => {
          const isSelected = tag.tag === selectedTag
          return (
            <button
              key={tag.tag}
              type="button"
              className={`tag-button${isSelected ? ' is-selected' : ''}`}
              onClick={() => onChangeTag(isSelected ? '' : tag.tag)}
            >
              <span>{tag.tag}</span>
              <span className="tag-count">{tag.count}件</span>
            </button>
          )
        })}
      </div>
      <p className="home-status" id="filter-status">{status}</p>
    </main>
  )
}
