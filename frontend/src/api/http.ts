export async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json() as Promise<T>
}

export async function putJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json() as Promise<T>
}
