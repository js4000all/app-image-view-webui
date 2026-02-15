import { useCallback, useEffect, useMemo, useState } from 'react'

import { HomePage } from './features/home/pages/HomePage'
import { ViewerPage } from './features/viewer/pages/ViewerPage'

function buildViewerPath(directoryId: string): string {
  return `/viewer?directory_id=${encodeURIComponent(directoryId)}`
}

function currentPathWithQuery(): string {
  return `${window.location.pathname}${window.location.search}`
}

export function App() {
  const [path, setPath] = useState(() => currentPathWithQuery())

  useEffect(() => {
    const handlePopState = () => {
      setPath(currentPathWithQuery())
    }

    window.addEventListener('popstate', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  const navigate = useCallback((nextPath: string) => {
    if (currentPathWithQuery() === nextPath) {
      return
    }

    window.history.pushState(null, '', nextPath)
    setPath(nextPath)
  }, [])

  const navigateHome = useCallback(() => {
    navigate('/')
  }, [navigate])

  const navigateViewer = useCallback(
    (directoryId: string) => {
      navigate(buildViewerPath(directoryId))
    },
    [navigate]
  )

  const requestedDirectoryId = useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('directory_id') ?? ''
  }, [path])

  if (window.location.pathname === '/viewer') {
    return <ViewerPage requestedDirectoryId={requestedDirectoryId} onNavigateHome={navigateHome} />
  }

  return <HomePage onOpenViewer={navigateViewer} />
}
