export type FilterStateInput = {
  selectedTags: Set<string>
  baseResultIds: ReadonlyArray<string>
  tagToFileIds: Readonly<Record<string, ReadonlyArray<string>>>
}

export type FilterStateSnapshot = {
  currentResultIds: string[]
  unselectedTagStats: Record<string, number>
}

function intersectIds(left: Set<string>, right: ReadonlyArray<string>): Set<string> {
  const next = new Set<string>()
  for (const id of right) {
    if (left.has(id)) {
      next.add(id)
    }
  }
  return next
}

export function computeFilterStateSnapshot(input: FilterStateInput): FilterStateSnapshot {
  const { selectedTags, baseResultIds, tagToFileIds } = input
  const baseSet = new Set(baseResultIds)

  let currentSet = new Set(baseSet)
  for (const tag of selectedTags) {
    const tagFileIds = tagToFileIds[tag] ?? []
    currentSet = intersectIds(currentSet, tagFileIds)
    if (currentSet.size === 0) {
      break
    }
  }

  const unselectedTagStats: Record<string, number> = {}
  for (const [tag, fileIds] of Object.entries(tagToFileIds)) {
    if (selectedTags.has(tag)) {
      continue
    }

    let count = 0
    for (const fileId of fileIds) {
      if (currentSet.has(fileId)) {
        count += 1
      }
    }

    if (count > 0) {
      unselectedTagStats[tag] = count
    }
  }

  return {
    currentResultIds: Array.from(currentSet).sort(),
    unselectedTagStats,
  }
}
