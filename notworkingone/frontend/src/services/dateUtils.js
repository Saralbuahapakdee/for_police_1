export function parseUTC(ts) {
  if (!ts) return null
  const s = String(ts).trim()

  if (s.endsWith('Z') || s.includes('+') || /T.*[-+]\d{2}:\d{2}$/.test(s)) {
    return new Date(s)
  }


  return new Date(s.replace(' ', 'T') + 'Z')
}


export function formatDateTime(ts) {
  const d = parseUTC(ts)
  if (!d || isNaN(d)) return 'N/A'
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`
}


export function formatDate(ts) {
  const d = parseUTC(ts)
  if (!d || isNaN(d)) return String(ts ?? 'N/A')
  return d.toLocaleDateString()
}


export function formatTime(ts) {
  const d = parseUTC(ts)
  if (!d || isNaN(d)) return 'N/A'
  return d.toLocaleTimeString()
}


export function formatShortTime(ts) {
  const d = parseUTC(ts)
  if (!d || isNaN(d)) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
