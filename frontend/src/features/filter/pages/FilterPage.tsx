import { useCallback, useEffect, useMemo, useState } from 'react'

import { fetchTagSummaries } from '../../home/api/homeApi'
import { DefaultService } from '../../../generated/api'
import { computeFilterStateSnapshot } from '../model/filterState'

export type TagSummary = {
  tag: string
  count: number
}

type FilterPageProps = {
  selectedTags: string[]
  onChangeTags: (tags: string[]) => void
  onOpenViewer: (tags: string[]) => void
}

export function FilterPage(props: FilterPageProps) {
  const { selectedTags, onChangeTags, onOpenViewer } = props
  const [tags, setTags] = useState<TagSummary[]>([])
  const [tagToFileIds, setTagToFileIds] = useState<Record<string, string[]>>({})
  const [baseResultIds, setBaseResultIds] = useState<string[]>([])
  const [status, setStatus] = useState('タグを読み込み中...')

  const loadTags = useCallback(async () => {
    try {
      const summaries = await fetchTagSummaries()
      setTags(summaries)

      if (summaries.length === 0) {
        setTagToFileIds({})
        setBaseResultIds([])
        setStatus('タグがありません。')
        return
      }

      const pairs = await Promise.all(
        summaries.map(async ({ tag }) => {
          const result = await DefaultService.queryTagIndex({
            requestBody: {
              mode: 'and',
              tags: [tag],
            },
          })
          return [tag, result.file_ids] as const
        })
      )

      const nextTagToFileIds: Record<string, string[]> = {}
      const unionIds = new Set<string>()
      for (const [tag, fileIds] of pairs) {
        nextTagToFileIds[tag] = fileIds
        for (const fileId of fileIds) {
          unionIds.add(fileId)
        }
      }

      setTagToFileIds(nextTagToFileIds)
      setBaseResultIds(Array.from(unionIds).sort())
      setStatus(`${summaries.length}件のタグを表示しています。`)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      setStatus(`タグ一覧の取得に失敗しました: ${message}`)
    }
  }, [])

  useEffect(() => {
    void loadTags()
  }, [loadTags])

  const selectedTagSet = useMemo(() => new Set(selectedTags), [selectedTags])
  const snapshot = useMemo(
    () => computeFilterStateSnapshot({ selectedTags: selectedTagSet, baseResultIds, tagToFileIds }),
    [baseResultIds, selectedTagSet, tagToFileIds]
  )

  const canOpenViewer = snapshot.currentResultIds.length > 0 && snapshot.currentResultIds.length <= 200

  const sortedTags = useMemo(() => {
    const selectedSummaries = tags.filter(({ tag }) => selectedTagSet.has(tag))
    const unselectedSummaries = tags
      .filter(({ tag }) => !selectedTagSet.has(tag))
      .map(({ tag }) => ({ tag, count: snapshot.unselectedTagStats[tag] ?? 0 }))
      .filter(({ count }) => count > 0)

    return [...selectedSummaries, ...unselectedSummaries]
  }, [selectedTagSet, snapshot.unselectedTagStats, tags])

  return (
    <main className="filter">
      <div className="filter-header">
        <h1>タグ絞り込み（暫定版）</h1>
        <p className="home-description">タグを選択してAND条件で対象画像を絞り込みます。</p>
        <div className="filter-toolbar">
          <a href="/" className="home-link">ホームへ戻る</a>
          <button
            id="open-filter-viewer"
            type="button"
            className="reload-button"
            onClick={() => onOpenViewer(selectedTags)}
            disabled={!canOpenViewer}
          >
            閲覧
          </button>
        </div>
        <p className="home-status" id="filter-status">{status}</p>
        <p className="home-status">選択中: {selectedTags.length}タグ / 対象: {snapshot.currentResultIds.length}件</p>
      </div>
      <div className="tag-flow-scroll" aria-live="polite">
        <div className="tag-button-list">
          {sortedTags.map((tag) => {
            const isSelected = selectedTagSet.has(tag.tag)
            const displayCount = isSelected ? snapshot.currentResultIds.length : (snapshot.unselectedTagStats[tag.tag] ?? tag.count)
            return (
              <button
                key={tag.tag}
                type="button"
                className={`tag-button${isSelected ? ' is-selected' : ''}`}
                onClick={() => {
                  const next = new Set(selectedTagSet)
                  if (isSelected) {
                    next.delete(tag.tag)
                  } else {
                    next.add(tag.tag)
                  }
                  onChangeTags(Array.from(next).sort())
                }}
              >
                <span>{tag.tag}</span>
                <span className="tag-count">{displayCount}件</span>
              </button>
            )
          })}
        </div>
      </div>
    </main>
  )
}
