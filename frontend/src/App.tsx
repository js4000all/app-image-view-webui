import { useCallback, useEffect, useMemo, useState } from 'react'

import { HomePage } from './features/home/pages/HomePage'
import { ViewerPage } from './features/viewer/pages/ViewerPage'

type LocationState = {
  pathname: string
  search: string
}

const HOME_PATH = '/'
const VIEWER_PATH = '/viewer'
const DIRECTORY_ID_PARAM = 'directory_id'

function buildViewerPath(directoryId: string): string {
  return `${VIEWER_PATH}?${DIRECTORY_ID_PARAM}=${encodeURIComponent(directoryId)}`
}

type ViewerRoute = {
  isViewer: boolean
  requestedDirectoryId: string
}

type HomeRoute = {
  requestedDirectoryId: string
}

function parseViewerRoute(location: LocationState): ViewerRoute {
  if (!location.pathname.startsWith(VIEWER_PATH)) {
    return {
      isViewer: false,
      requestedDirectoryId: '',
    }
  }

  const params = new URLSearchParams(location.search)
  return {
    isViewer: true,
    requestedDirectoryId: params.get(DIRECTORY_ID_PARAM) ?? '',
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

  const navigateViewer = useCallback(
    (directoryId: string) => {
      navigate(buildViewerPath(directoryId))
    },
    [navigate]
  )

  const viewerRoute = useMemo(() => parseViewerRoute(location), [location])
  const homeRoute = useMemo(() => parseHomeRoute(location), [location])

  if (viewerRoute.isViewer) {
    return <ViewerPage requestedDirectoryId={viewerRoute.requestedDirectoryId} onNavigateHome={navigateHome} />
  }

  return <HomePage requestedDirectoryId={homeRoute.requestedDirectoryId} onOpenViewer={navigateViewer} />
}
