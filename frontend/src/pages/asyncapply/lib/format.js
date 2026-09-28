/**
 * Shared formatting helpers for the AsyncApply UI.
 *
 * Timestamps: the API serializes naive UTC (`2026-09-28T17:19:53`, no zone
 * marker), which `new Date()` would read as *local* time and display hours
 * off. Everything here routes through parseUtc so a timestamp is read as the
 * UTC it actually is and rendered in the viewer's own zone.
 */

/**
 * Parse an API timestamp, treating a zone-less string as UTC.
 *
 * @param {string|null|undefined} value
 * @returns {Date|null}
 */
export function parseUtc(value) {
  if (!value) return null
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(value)
  const date = new Date(hasZone ? value : `${value}Z`)
  return Number.isNaN(date.getTime()) ? null : date
}

/**
 * Local date and time, e.g. "28 Sep, 13:19".
 *
 * @param {string} value
 * @returns {string}
 */
export function formatDateTime(value) {
  const date = parseUtc(value)
  if (!date) return ''
  return date.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Local date only, e.g. "28 Sep".
 *
 * @param {string} value
 * @returns {string}
 */
export function formatDate(value) {
  const date = parseUtc(value)
  if (!date) return ''
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

/**
 * Short relative age, e.g. "3m ago", "2d ago".
 *
 * @param {string} value
 * @returns {string}
 */
export function formatRelative(value) {
  const date = parseUtc(value)
  if (!date) return ''
  const seconds = Math.round((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

/**
 * How long something took, from two API timestamps.
 *
 * @param {string|null} start
 * @param {string|null} end
 * @returns {string|null}
 */
export function duration(start, end) {
  const from = parseUtc(start)
  const to = parseUtc(end)
  if (!from || !to) return null
  const ms = to.getTime() - from.getTime()
  if (ms < 0) return null
  const seconds = Math.round(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`
  return `${(minutes / 60).toFixed(1)}h`
}

// Country names and common aliases that appear in a posting's location line.
const COUNTRIES = {
  spain: 'ES', españa: 'ES',
  'united states': 'US', usa: 'US', 'u.s.': 'US', 'united states of america': 'US', america: 'US',
  'united kingdom': 'GB', uk: 'GB', england: 'GB', scotland: 'GB', wales: 'GB', london: 'GB',
  germany: 'DE', deutschland: 'DE', france: 'FR', ireland: 'IE', netherlands: 'NL', holland: 'NL',
  poland: 'PL', portugal: 'PT', italy: 'IT', switzerland: 'CH', sweden: 'SE', denmark: 'DK',
  norway: 'NO', finland: 'FI', belgium: 'BE', austria: 'AT', czechia: 'CZ', 'czech republic': 'CZ',
  romania: 'RO', greece: 'GR', hungary: 'HU', canada: 'CA', mexico: 'MX', brazil: 'BR',
  argentina: 'AR', chile: 'CL', colombia: 'CO', india: 'IN', china: 'CN', japan: 'JP',
  singapore: 'SG', australia: 'AU', 'new zealand': 'NZ', israel: 'IL', 'south korea': 'KR',
  'united arab emirates': 'AE', uae: 'AE', dubai: 'AE',
}

// Cities and US state codes that identify a country on their own, since many
// postings write "San Jose" or "Austin, TX" with no country at all.
const CITY_HINTS = {
  'san jose': 'US', 'san francisco': 'US', 'new york': 'US', nyc: 'US', seattle: 'US',
  austin: 'US', boston: 'US', chicago: 'US', 'santa clara': 'US', 'mountain view': 'US',
  'palo alto': 'US', sunnyvale: 'US', cupertino: 'US', redmond: 'US', denver: 'US',
  atlanta: 'US', 'los angeles': 'US', 'ann arbor': 'US', madrid: 'ES', barcelona: 'ES',
  valencia: 'ES', sevilla: 'ES', bilbao: 'ES', malaga: 'ES', berlin: 'DE', munich: 'DE',
  hamburg: 'DE', paris: 'FR', dublin: 'IE', amsterdam: 'NL', warsaw: 'PL', krakow: 'PL',
  lisbon: 'PT', porto: 'PT', milan: 'IT', rome: 'IT', zurich: 'CH', geneva: 'CH',
  stockholm: 'SE', copenhagen: 'DK', oslo: 'NO', helsinki: 'FI', brussels: 'BE',
  vienna: 'AT', prague: 'CZ', bucharest: 'RO', toronto: 'CA', vancouver: 'CA',
  montreal: 'CA', bangalore: 'IN', bengaluru: 'IN', hyderabad: 'IN', tokyo: 'JP',
  sydney: 'AU', melbourne: 'AU', 'tel aviv': 'IL',
}
const US_STATES = /\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b/

/**
 * Turn an ISO-3166 alpha-2 code into its flag emoji.
 *
 * @param {string} code
 * @returns {string}
 */
function flagOf(code) {
  return String.fromCodePoint(...[...code.toUpperCase()].map((c) => 0x1f1a5 + c.charCodeAt(0)))
}

/**
 * Best-effort flag emoji for a posting's location line.
 *
 * Checks the country name first (the last segment is usually the country),
 * then falls back to a city or US state code, since plenty of postings write
 * only "San Jose" or "Austin, TX". Returns "" rather than guessing wrong when
 * nothing matches -- a missing flag reads better than the wrong country.
 *
 * @param {string|null|undefined} location
 * @returns {string}
 */
export function countryFlag(location) {
  if (!location) return ''
  const text = location.toLowerCase()

  for (const [name, code] of Object.entries(COUNTRIES)) {
    if (new RegExp(`(^|[^a-z])${name}([^a-z]|$)`).test(text)) return flagOf(code)
  }
  for (const [city, code] of Object.entries(CITY_HINTS)) {
    if (new RegExp(`(^|[^a-z])${city}([^a-z]|$)`).test(text)) return flagOf(code)
  }
  if (US_STATES.test(location)) return flagOf('US')
  if (/\bremote\b/.test(text)) return '🌍'
  return ''
}

// One place defining what each application status looks like, so the table,
// the board and the detail panel can never drift apart on colour or wording.
export const STATUS_META = {
  evaluated: { label: 'Evaluated', dot: 'bg-stone-300', chip: 'bg-stone-100 text-stone-500' },
  hard_stopped: { label: 'Filtered out', dot: 'bg-amber-300', chip: 'bg-amber-50 text-amber-700' },
  applied: { label: 'Applied', dot: 'bg-sky-400', chip: 'bg-sky-50 text-sky-700' },
  oa: { label: 'OA', dot: 'bg-violet-400', chip: 'bg-violet-50 text-violet-700' },
  interviewing: { label: 'Interviewing', dot: 'bg-indigo-400', chip: 'bg-indigo-50 text-indigo-700' },
  offer: { label: 'Offer', dot: 'bg-emerald-400', chip: 'bg-emerald-50 text-emerald-700' },
  rejected: { label: 'Rejected', dot: 'bg-rose-300', chip: 'bg-rose-50 text-rose-700' },
  withdrawn: { label: 'Withdrawn', dot: 'bg-stone-400', chip: 'bg-stone-100 text-stone-500' },
}

// The order a real application moves through, used for the board columns and
// the status menu. hard_stopped is excluded: the pipeline sets it and there
// is nothing to track once a posting was filtered out before a CV existed.
export const PIPELINE_STATUSES = ['evaluated', 'applied', 'oa', 'interviewing', 'offer', 'rejected', 'withdrawn']
