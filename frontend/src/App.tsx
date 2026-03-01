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

function buildViewerPathFromDirectory(directoryId: string): string {
  return `${VIEWER_PATH}?${DIRECTORY_ID_PARAM}=${encodeURIComponent(directoryId)}`
}

function buildViewerPathFromTag(tag: string): string {
  return `${VIEWER_PATH}?${TAG_PARAM}=${encodeURIComponent(tag)}`
}

type ViewerRoute = {
  isViewer: boolean
  requestedDirectoryId: string
  selectedTag: string
}

type HomeRoute = {
  requestedDirectoryId: string
}

type FilterRoute = {
  isFilter: boolean
  selectedTag: string
}

function parseViewerRoute(location: LocationState): ViewerRoute {
  if (!location.pathname.startsWith(VIEWER_PATH)) {
    return {
      isViewer: false,
      requestedDirectoryId: '',
      selectedTag: '',
    }
  }

  const params = new URLSearchParams(location.search)
  return {
    isViewer: true,
    requestedDirectoryId: params.get(DIRECTORY_ID_PARAM) ?? '',
    selectedTag: params.get(TAG_PARAM) ?? '',
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
      selectedTag: '',
    }
  }

  const params = new URLSearchParams(location.search)
  return {
    isFilter: true,
    selectedTag: params.get(TAG_PARAM) ?? '',
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

  const navigateFilter = useCallback((tag = '') => {
    if (!tag) {
      navigate(FILTER_PATH)
      return
    }

    const params = new URLSearchParams({ [TAG_PARAM]: tag })
    navigate(`${FILTER_PATH}?${params.toString()}`)
  }, [navigate])

  const navigateViewerFromDirectory = useCallback(
    (directoryId: string) => {
      navigate(buildViewerPathFromDirectory(directoryId))
    },
    [navigate]
  )

  const navigateViewerFromTag = useCallback(
    (tag: string) => {
      navigate(buildViewerPathFromTag(tag))
    },
    [navigate]
  )

  const viewerRoute = useMemo(() => parseViewerRoute(location), [location])
  const homeRoute = useMemo(() => parseHomeRoute(location), [location])
  const filterRoute = useMemo(() => parseFilterRoute(location), [location])

  if (viewerRoute.isViewer) {
    const hasTagMode = Boolean(viewerRoute.selectedTag)

    return (
      <ViewerPage
        listFileIds={async () => {
          if (hasTagMode) {
            const payload = await DefaultService.queryTagIndex({
              requestBody: {
                mode: 'and',
                tags: [viewerRoute.selectedTag],
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
            navigateFilter(viewerRoute.selectedTag)
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
        selectedTag={filterRoute.selectedTag}
        onChangeTag={navigateFilter}
        onOpenViewer={navigateViewerFromTag}
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
