import { useCallback, useEffect, useMemo, useState } from 'react'

import { FilterPage } from './features/filter/pages/FilterPage'
import { HomePage } from './features/home/pages/HomePage'
import { ViewerPage } from './features/viewer/pages/ViewerPage'
import { DefaultService } from './generated/api'
import { fetchViewerImages } from './features/viewer/api/viewerApi'

type LocationState = {
  pathname: string
  search: string
}

const HOME_PATH = '/'
const VIEWER_PATH = '/viewer'
const FILTER_PATH = '/filter'
const DIRECTORY_ID_PARAM = 'directory_id'
const TAG_PARAM = 'tag'
const TAG_SEPARATOR = ','

function buildViewerPathFromDirectory(directoryId: string): string {
  return `${VIEWER_PATH}?${DIRECTORY_ID_PARAM}=${encodeURIComponent(directoryId)}`
}

function buildViewerPathFromTags(tags: string[]): string {
  const encoded = tags.filter(Boolean).join(TAG_SEPARATOR)
  return `${VIEWER_PATH}?${TAG_PARAM}=${encodeURIComponent(encoded)}`
}

type ViewerRoute = {
  isViewer: boolean
  requestedDirectoryId: string
  selectedTags: string[]
}

type HomeRoute = {
  requestedDirectoryId: string
}

type FilterRoute = {
  isFilter: boolean
  selectedTags: string[]
}

function parseViewerRoute(location: LocationState): ViewerRoute {
  if (!location.pathname.startsWith(VIEWER_PATH)) {
    return {
      isViewer: false,
      requestedDirectoryId: '',
      selectedTags: [],
    }
  }

  const params = new URLSearchParams(location.search)
  return {
    isViewer: true,
    requestedDirectoryId: params.get(DIRECTORY_ID_PARAM) ?? '',
    selectedTags: (params.get(TAG_PARAM) ?? '').split(TAG_SEPARATOR).map((tag) => tag.trim()).filter(Boolean),
  }
}

function parseHomeRoute(location: LocationState): HomeRoute {
  if (location.pathname !== HOME_PATH) {
    return {
      requestedDirectoryId: '',
    }
  }

  const params = new URLSearchParams(location.search)
  return {
    requestedDirectoryId: params.get(DIRECTORY_ID_PARAM) ?? '',
  }
}

function parseFilterRoute(location: LocationState): FilterRoute {
  if (!location.pathname.startsWith(FILTER_PATH)) {
    return {
      isFilter: false,
      selectedTags: [],
    }
  }

  const params = new URLSearchParams(location.search)
  return {
    isFilter: true,
    selectedTags: (params.get(TAG_PARAM) ?? '').split(TAG_SEPARATOR).map((tag) => tag.trim()).filter(Boolean),
  }
}

function getLocationState(): LocationState {
  return {
    pathname: window.location.pathname,
    search: window.location.search,
  }
}

function buildPath({ pathname, search }: LocationState): string {
  return `${pathname}${search}`
}

export function App() {
  const [location, setLocation] = useState(() => getLocationState())

  useEffect(() => {
    const handlePopState = () => {
      setLocation(getLocationState())
    }

    window.addEventListener('popstate', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  const navigate = useCallback((nextPath: string) => {
    if (buildPath(location) === nextPath) {
      return
    }

    window.history.pushState(null, '', nextPath)
    setLocation(getLocationState())
  }, [location])

  const navigateHome = useCallback((directoryId: string) => {
    if (!directoryId) {
      navigate(HOME_PATH)
      return
    }

    const params = new URLSearchParams({
      [DIRECTORY_ID_PARAM]: directoryId,
    })
    navigate(`${HOME_PATH}?${params.toString()}`)
  }, [navigate])

  const navigateFilter = useCallback((tags: string[] = []) => {
    if (tags.length === 0) {
      navigate(FILTER_PATH)
      return
    }

    const params = new URLSearchParams({ [TAG_PARAM]: tags.join(TAG_SEPARATOR) })
    navigate(`${FILTER_PATH}?${params.toString()}`)
  }, [navigate])

  const navigateViewerFromDirectory = useCallback(
    (directoryId: string) => {
      navigate(buildViewerPathFromDirectory(directoryId))
    },
    [navigate]
  )

  const navigateViewerFromTags = useCallback(
    (tags: string[]) => {
      navigate(buildViewerPathFromTags(tags))
    },
    [navigate]
  )

  const viewerRoute = useMemo(() => parseViewerRoute(location), [location])
  const homeRoute = useMemo(() => parseHomeRoute(location), [location])
  const filterRoute = useMemo(() => parseFilterRoute(location), [location])

  if (viewerRoute.isViewer) {
    const hasTagMode = viewerRoute.selectedTags.length > 0

    return (
      <ViewerPage
        listFileIds={async () => {
          if (hasTagMode) {
            const payload = await DefaultService.queryTagIndex({
              requestBody: {
                mode: 'and',
                tags: viewerRoute.selectedTags,
              },
            })
            return payload.file_ids
          }

          if (!viewerRoute.requestedDirectoryId) {
            return []
          }

          const images = await fetchViewerImages(viewerRoute.requestedDirectoryId)
          return images.map((image) => image.file_id)
        }}
        onNavigateBack={() => {
          if (hasTagMode) {
            navigateFilter(viewerRoute.selectedTags)
            return
          }

          navigateHome(viewerRoute.requestedDirectoryId)
        }}
        allowImageDelete={!hasTagMode}
      />
    )
  }

  if (filterRoute.isFilter) {
    return (
      <FilterPage
        selectedTags={filterRoute.selectedTags}
        onChangeTags={navigateFilter}
        onOpenViewer={navigateViewerFromTags}
      />
    )
  }

  return (
    <HomePage
      requestedDirectoryId={homeRoute.requestedDirectoryId}
      onOpenViewer={navigateViewerFromDirectory}
      onOpenFilter={() => navigateFilter()}
    />
  )
}
