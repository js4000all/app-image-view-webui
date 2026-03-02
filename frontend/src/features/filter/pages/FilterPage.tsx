import { useCallback, useEffect, useMemo, useState } from 'react'

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
  const [splitThreshold, setSplitThreshold] = useState(0.8)
  const [tags, setTags] = useState<TagSummary[]>([])
  const [tagToFileIds, setTagToFileIds] = useState<Record<string, string[]>>({})
  const [baseResultIds, setBaseResultIds] = useState<string[]>([])
  const [status, setStatus] = useState('タグを読み込み中...')

  const loadTags = useCallback(async () => {
    try {
      const registry = await DefaultService.listTagIndexRegistry()
      const summaries = registry.tags
        .map(({ tag, file_ids }) => ({ tag, count: file_ids.length }))
        .sort((left, right) => right.count - left.count || left.tag.localeCompare(right.tag))

      setTags(summaries)

      if (summaries.length === 0) {
        setTagToFileIds({})
        setBaseResultIds([])
        setStatus('タグがありません。')
        return
      }

      const nextTagToFileIds: Record<string, string[]> = {}
      const unionIds = new Set<string>()
      for (const { tag, file_ids } of registry.tags) {
        nextTagToFileIds[tag] = file_ids
        for (const fileId of file_ids) {
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

  const sortedSelectedTags = useMemo(() => [...selectedTags].sort((left, right) => left.localeCompare(right)), [selectedTags])

  const sortedTags = useMemo(() => {
    const selectedSummaries = tags.filter(({ tag }) => selectedTagSet.has(tag))
    const unselectedSummaries = tags
      .filter(({ tag }) => !selectedTagSet.has(tag))
      .map(({ tag }) => {
        const count = snapshot.unselectedTagStats[tag] ?? 0
        const currentResultCount = snapshot.currentResultIds.length
        const ratio = currentResultCount > 0 ? count / currentResultCount : 0
        return { tag, count, ratio }
      })
      .filter(({ count }) => count > 0)

    return [...selectedSummaries, ...unselectedSummaries]
  }, [selectedTagSet, snapshot.currentResultIds.length, snapshot.unselectedTagStats, tags])

  const splitTagSections = useMemo(() => {
    const highContributionTags: Array<{ tag: string; count: number; ratio: number }> = []
    const lowContributionTags: Array<{ tag: string; count: number; ratio: number }> = []

    for (const tag of sortedTags) {
      if (!('ratio' in tag) || selectedTagSet.has(tag.tag)) {
        continue
      }

      if (tag.ratio <= splitThreshold) {
        highContributionTags.push(tag)
      } else {
        lowContributionTags.push(tag)
      }
    }

    return {
      highContributionTags,
      lowContributionTags,
    }
  }, [selectedTagSet, sortedTags, splitThreshold])

  const currentResultCount = snapshot.currentResultIds.length

  return (
    <main className="filter">
      <div className="filter-header">
        <h1>タグ絞り込み（暫定版）</h1>
        <div className="filter-header-row filter-header-row-primary">
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
          <p className="home-status">絞り込み結果: {currentResultCount} / {baseResultIds.length} 件</p>
        </div>
        <div className="filter-header-row">
          <label className="threshold-slider" htmlFor="tag-threshold">
            <span>しきい値: {splitThreshold.toFixed(2)}</span>
          </label>
          <input
            id="tag-threshold"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={splitThreshold}
            onChange={(event) => {
              setSplitThreshold(Number(event.target.value))
            }}
            className="threshold-slider-input"
          />
        </div>
        <div className="selected-tag-chip-list" role="list" aria-label="選択中タグ一覧">
          {sortedSelectedTags.map((tag) => (
            <button
              key={tag}
              type="button"
              className="selected-tag-chip"
              onClick={() => onChangeTags(selectedTags.filter((selectedTag) => selectedTag !== tag))}
              title={`タグ「${tag}」を解除`}
              aria-label={`タグ「${tag}」を解除`}
            >
              <span className="selected-tag-chip-label">{tag}</span>
              <span aria-hidden="true" className="selected-tag-chip-remove">×</span>
            </button>
          ))}
        </div>
        <p className="sr-only" id="filter-status">{status}</p>
      </div>
      <div className="tag-flow-scroll" aria-live="polite">
        <section className="tag-section">
          <h2>絞り込み寄与が高いタグ（比率 ≤ しきい値）</h2>
          <div className="tag-button-list">
            {splitTagSections.highContributionTags.map((tag) => {
              const displayCount = snapshot.unselectedTagStats[tag.tag] ?? tag.count
              return (
                <button
                  key={tag.tag}
                  type="button"
                  className="tag-button"
                  onClick={() => {
                    const next = new Set(selectedTagSet)
                    next.add(tag.tag)
                    onChangeTags(Array.from(next).sort())
                  }}
                >
                  <span>{tag.tag}</span>
                  <span className="tag-count">{displayCount}件 ({(tag.ratio * 100).toFixed(0)}%)</span>
                </button>
              )
            })}
          </div>
        </section>
        <section className="tag-section">
          <h2>絞り込み寄与が低いタグ（比率 &gt; しきい値）</h2>
          <div className="tag-button-list">
            {splitTagSections.lowContributionTags.map((tag) => {
              const displayCount = snapshot.unselectedTagStats[tag.tag] ?? tag.count
              return (
                <button
                  key={tag.tag}
                  type="button"
                  className="tag-button"
                  onClick={() => {
                    const next = new Set(selectedTagSet)
                    next.add(tag.tag)
                    onChangeTags(Array.from(next).sort())
                  }}
                >
                  <span>{tag.tag}</span>
                  <span className="tag-count">{displayCount}件 ({(tag.ratio * 100).toFixed(0)}%)</span>
                </button>
              )
            })}
          </div>
        </section>
        <div className="tag-button-list">
          {sortedTags.filter((tag) => selectedTagSet.has(tag.tag)).map((tag) => {
            const isSelected = selectedTagSet.has(tag.tag)
            const displayCount = currentResultCount
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
