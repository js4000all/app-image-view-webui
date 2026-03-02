// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DefaultService } from '../../../generated/api'
import { FILTER_RESULT_WARNING_THRESHOLD } from '../constants'
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
  it('keeps viewer transition available even when result count is zero', async () => {
    vi.spyOn(DefaultService, 'listTagIndexRegistry').mockResolvedValue({
      tags: [
        { tag: 'a', file_ids: ['f1'] },
        { tag: 'b', file_ids: ['f2'] },
      ],
    })

    render(<FilterPage selectedTags={['a', 'b']} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    const openViewerButton = await screen.findByRole('button', { name: '閲覧' })
    expect(openViewerButton).toHaveProperty('disabled', false)
    expect(await screen.findByText(/（0件のまま閲覧へ遷移できます）/)).toBeTruthy()
  })


  it('supports display scenarios for wrapping/long-name/many-tags', async () => {
    render(<FilterPage selectedTags={filterHeaderScenarios[0].selectedTags} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    expect(await screen.findByRole('list', { name: '選択中タグ一覧' })).toBeTruthy()
    expect(screen.getAllByRole('button', { name: /タグ「.*」を解除/ }).length).toBeGreaterThan(10)

    render(<FilterPage selectedTags={filterHeaderScenarios[1].selectedTags} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)
    expect(await screen.findByText(/this_is_an_extremely_long_tag_name_for_ui_wrapping_validation/)).toBeTruthy()
  })
})

describe('FilterPage threshold split', () => {
  afterEach(() => {
    cleanup()
  })

  it('splits unselected tags into two sections by ratio and threshold', async () => {
    vi.spyOn(DefaultService, 'listTagIndexRegistry').mockResolvedValue({
      tags: [
        { tag: 'base', file_ids: ['f1', 'f2', 'f3', 'f4'] },
        { tag: 'tight', file_ids: ['f1'] },
        { tag: 'wide', file_ids: ['f1', 'f2', 'f3', 'f4'] },
      ],
    })

    render(<FilterPage selectedTags={['base']} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    const highSection = await screen.findByRole('heading', { name: '絞り込み寄与が高いタグ（比率 ≤ しきい値）' })
    const lowSection = await screen.findByRole('heading', { name: '絞り込み寄与が低いタグ（比率 > しきい値）' })

    expect(within(highSection.parentElement as HTMLElement).getByText(/tight/)).toBeTruthy()
    expect(within(lowSection.parentElement as HTMLElement).getByText(/wide/)).toBeTruthy()
  })

  it('updates section placement when threshold slider changes', async () => {
    vi.spyOn(DefaultService, 'listTagIndexRegistry').mockResolvedValue({
      tags: [
        { tag: 'base', file_ids: ['f1', 'f2', 'f3', 'f4'] },
        { tag: 'middle', file_ids: ['f1', 'f2', 'f3'] },
      ],
    })

    render(<FilterPage selectedTags={['base']} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    const slider = await screen.findByRole('slider', { name: /しきい値/ })
    fireEvent.change(slider, { target: { value: '0.75' } })

    expect(await screen.findByText('しきい値: 0.75')).toBeTruthy()
  })

  it('hides all unselected tags when currentResultCount is zero', async () => {
    vi.spyOn(DefaultService, 'listTagIndexRegistry').mockResolvedValue({
      tags: [
        { tag: 'a', file_ids: ['f1'] },
        { tag: 'b', file_ids: ['f2'] },
      ],
    })

    render(<FilterPage selectedTags={['a', 'b']} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    expect(await screen.findByText('絞り込み結果: 0 / 2 件')).toBeTruthy()
    expect(screen.queryByText(/件 \(.*%\)/)).toBeNull()
  })

  it('shows warning message when filtered result exceeds threshold', async () => {
    vi.spyOn(DefaultService, 'listTagIndexRegistry').mockResolvedValue({
      tags: [
        {
          tag: 'bulk',
          file_ids: Array.from({ length: FILTER_RESULT_WARNING_THRESHOLD + 1 }, (_, i) => `f${i + 1}`),
        },
      ],
    })

    render(<FilterPage selectedTags={['bulk']} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    expect(await screen.findByText(new RegExp(`絞り込み結果: ${FILTER_RESULT_WARNING_THRESHOLD + 1} / ${FILTER_RESULT_WARNING_THRESHOLD + 1} 件`))).toBeTruthy()
    expect(screen.getByText(/⚠️ 結果が多いため、十分に絞り込めていない可能性があります。/)).toBeTruthy()
  })

  it('supports text search for unselected tags', async () => {
    const user = userEvent.setup()
    vi.spyOn(DefaultService, 'listTagIndexRegistry').mockResolvedValue({
      tags: [
        { tag: 'base', file_ids: ['f1', 'f2', 'f3'] },
        { tag: 'apple', file_ids: ['f1'] },
        { tag: 'banana', file_ids: ['f2'] },
      ],
    })

    render(<FilterPage selectedTags={['base']} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    const searchInput = await screen.findByLabelText('タグ検索')
    await user.type(searchInput, 'app')

    expect(screen.getByText('apple')).toBeTruthy()
    expect(screen.queryByText('banana')).toBeNull()
  })

  it('switches unselected tag order and keeps alphabetical tie-breaker for count sort', async () => {
    const user = userEvent.setup()
    vi.spyOn(DefaultService, 'listTagIndexRegistry').mockResolvedValue({
      tags: [
        { tag: 'base', file_ids: ['f1', 'f2', 'f3'] },
        { tag: 'zeta', file_ids: ['f1'] },
        { tag: 'alpha', file_ids: ['f1'] },
        { tag: 'middle', file_ids: ['f1', 'f2'] },
      ],
    })

    render(<FilterPage selectedTags={['base']} onChangeTags={vi.fn()} onOpenViewer={vi.fn()} />)

    expect(await screen.findByText('middle')).toBeTruthy()
    const highSection = await screen.findByRole('heading', { name: '絞り込み寄与が高いタグ（比率 ≤ しきい値）' })
    const highButtons = within(highSection.parentElement as HTMLElement).getAllByRole('button')

    expect(highButtons[0].textContent).toContain('alpha')
    expect(highButtons[1].textContent).toContain('middle')
    expect(highButtons[2].textContent).toContain('zeta')

    const sortSelect = screen.getByLabelText('未選択タグ並び順')
    await user.selectOptions(sortSelect, 'count-desc')

    const countSortedButtons = within(highSection.parentElement as HTMLElement).getAllByRole('button')
    expect(countSortedButtons[0].textContent).toContain('middle')
    expect(countSortedButtons[1].textContent).toContain('alpha')
    expect(countSortedButtons[2].textContent).toContain('zeta')
  })
})
