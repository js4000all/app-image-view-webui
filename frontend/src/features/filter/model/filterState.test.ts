import { describe, expect, it } from 'vitest'

import { computeFilterStateSnapshot } from './filterState'

describe('computeFilterStateSnapshot', () => {
  const baseResultIds = ['f1', 'f2', 'f3', 'f4']
  const tagToFileIds = {
    cat: ['f1', 'f2', 'f4'],
    blue: ['f2', 'f3'],
    portrait: ['f4'],
  }

  it('applies AND conditions for selectedTags', () => {
    const snapshot = computeFilterStateSnapshot({
      selectedTags: new Set(['cat', 'blue']),
      baseResultIds,
      tagToFileIds,
    })

    expect(snapshot.currentResultIds).toEqual(['f2'])
  })

  it('recomputes unselected tag stats from currentResultIds and excludes zero counts', () => {
    const snapshot = computeFilterStateSnapshot({
      selectedTags: new Set(['cat']),
      baseResultIds,
      tagToFileIds,
    })

    expect(snapshot.currentResultIds).toEqual(['f1', 'f2', 'f4'])
    expect(snapshot.unselectedTagStats).toEqual({
      blue: 1,
      portrait: 1,
    })
  })
})
