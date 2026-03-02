export type FilterHeaderScenario = {
  name: string
  selectedTags: string[]
}

export const filterHeaderScenarios: FilterHeaderScenario[] = [
  {
    name: '折り返し確認（多数タグ）',
    selectedTags: Array.from({ length: 18 }, (_, index) => `tag-${String(index + 1).padStart(2, '0')}`),
  },
  {
    name: '長いタグ名確認',
    selectedTags: [
      'this_is_an_extremely_long_tag_name_for_ui_wrapping_validation_aaaaaaaaaaaaaaaa',
      'portrait',
      'blue_hair',
    ],
  },
]
