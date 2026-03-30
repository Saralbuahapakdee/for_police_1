/**
 * dateUtils.js
 * SQLite stores CURRENT_TIMESTAMP as UTC but without the trailing 'Z',
 * so JavaScript's Date constructor treats it as *local* time — wrong.
 * These helpers append 'Z' so the browser correctly converts UTC → local.
 */

/**
 * Parse a timestamp string from the backend as UTC.
 * If it already has timezone info (contains '+', 'Z', or 'T…:…±') leave it alone.
 */
export function parseUTC(ts) {
  if (!ts) return null
  const s = String(ts).trim()
  // Already has explicit timezone info
  if (s.endsWith('Z') || s.includes('+') || /T.*[-+]\d{2}:\d{2}$/.test(s)) {
    return new Date(s)
  }
  // SQLite format: "2025-01-15 14:30:00" or "2025-01-15T14:30:00"
  // Normalise separator and append Z
  return new Date(s.replace(' ', 'T') + 'Z')
}

/** "15/01/2025 21:30:00"  (date + time, local) */
export function formatDateTime(ts) {
  const d = parseUTC(ts)
  if (!d || isNaN(d)) return 'N/A'
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`
}

/** "15/01/2025"  (date only, local) */
export function formatDate(ts) {
  const d = parseUTC(ts)
  if (!d || isNaN(d)) return String(ts ?? 'N/A')
  return d.toLocaleDateString()
}

/** "21:30:00"  (time only, local) */
export function formatTime(ts) {
  const d = parseUTC(ts)
  if (!d || isNaN(d)) return 'N/A'
  return d.toLocaleTimeString()
}

/** "21:30"  (short time, local) */
export function formatShortTime(ts) {
  const d = parseUTC(ts)
  if (!d || isNaN(d)) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
