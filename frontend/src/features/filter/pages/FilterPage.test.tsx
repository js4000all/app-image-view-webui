// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DefaultService } from '../../../generated/api'
import { FilterPage } from './FilterPage'
import { filterHeaderScenarios } from './filterHeaderScenarios'

describe('FilterPage header', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    vi.spyOn(DefaultService, 'listTagIndexRegistry').mockResolvedValue({
      tags: [
        { tag: 'apple', file_ids: ['f1', 'f2'] },
        { tag: 'zebra', file_ids: ['f2'] },
      ],
    })
  })

  it('shows selected tags as sorted chips and supports per-tag remove', async () => {
    const user = userEvent.setup()
    const onChangeTags = vi.fn()

    render(<FilterPage selectedTags={['zebra', 'apple']} onChangeTags={onChangeTags} onOpenViewer={vi.fn()} />)

    const chips = await screen.findAllByRole('button', { name: /タグ「.*」を解除/ })
    expect(chips).toHaveLength(2)
    expect(chips[0].textContent).toContain('apple')
    expect(chips[1].textContent).toContain('zebra')

    await user.click(chips[0])
    expect(onChangeTags).toHaveBeenCalledWith(['zebra'])
  })

  it('always shows result count summary', async () => {
    render(<FilterPage selectedTags={['apple']} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    expect(await screen.findByText('絞り込み結果: 2 / 2 件')).toBeTruthy()
  })

  it('supports display scenarios for wrapping/long-name/many-tags', async () => {
    render(<FilterPage selectedTags={filterHeaderScenarios[0].selectedTags} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    expect(await screen.findByRole('list', { name: '選択中タグ一覧' })).toBeTruthy()
    expect(screen.getAllByRole('button', { name: /タグ「.*」を解除/ }).length).toBeGreaterThan(10)

    render(<FilterPage selectedTags={filterHeaderScenarios[1].selectedTags} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)
    expect(await screen.findByText(/this_is_an_extremely_long_tag_name_for_ui_wrapping_validation/)).toBeTruthy()
  })
})
