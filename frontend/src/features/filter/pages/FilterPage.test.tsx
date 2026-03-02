// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
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
})
