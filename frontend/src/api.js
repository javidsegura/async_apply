/**
 * Thin fetch wrapper around the AsyncApply REST API.
 */

import { auth } from './firebase.js'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

/**
 * Build a query string from a params object, skipping null/undefined/empty values.
 *
 * @param {Object} params - Key/value pairs to serialize.
 * @returns {string} A leading-? query string, or empty string if no params.
 */
function toQueryString(params) {
  if (!params) return ''
  const entries = Object.entries(params).filter(
    ([, value]) => value !== undefined && value !== null && value !== '',
  )
  if (entries.length === 0) return ''
  const search = new URLSearchParams()
  for (const [key, value] of entries) search.append(key, value)
  return `?${search.toString()}`
}

/**
 * Get a fresh Firebase ID token for the signed-in user, if any.
 *
 * getIdToken() returns the cached token and transparently refreshes it once
 * it's within five minutes of expiring, so callers never need to think
 * about token lifetime themselves.
 *
 * @returns {Promise<string|null>}
 */
async function authHeader() {
  const user = auth.currentUser
  if (!user) return {}
  const token = await user.getIdToken()
  return { Authorization: `Bearer ${token}` }
}

/**
 * Perform a fetch against the API and parse the JSON response.
 *
 * @param {string} path - Path relative to the API base URL.
 * @param {RequestInit} [options] - Fetch options.
 * @returns {Promise<any>} The parsed JSON body, or null for 204 responses.
 */
async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(await authHeader()) },
    ...options,
  })
  if (res.status === 401) {
    // The token expired or was revoked mid-session -- bounce to login
    // rather than surfacing a confusing generic error.
    window.location.href = '/login'
    throw new Error('session expired')
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API error ${res.status} on ${path}: ${text}`)
  }
  if (res.status === 204) return null
  return res.json()
}

// --- AsyncApply ---

export function createAsyncApplyBatch(items) {
  return request('/asyncapply/batches', { method: 'POST', body: JSON.stringify({ items }) })
}

export function getAsyncApplyBatches() {
  return request('/asyncapply/batches')
}

export function getAsyncApplyBatch(id) {
  return request(`/asyncapply/batches/${id}`)
}

export function retryAsyncApplyBatch(id) {
  return request(`/asyncapply/batches/${id}/retry`, { method: 'POST' })
}

export function getAsyncApplyItems(params) {
  return request(`/asyncapply/items${toQueryString(params)}`)
}

export function updateAsyncApplyItem(id, payload) {
  return request(`/asyncapply/items/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function deleteAsyncApplyItem(id) {
  return request(`/asyncapply/items/${id}`, { method: 'DELETE' })
}

/**
 * Fetch an authenticated GET as a blob and return an object URL for it.
 *
 * Both the asset download and the logo image sit behind auth now, so a
 * plain <img src> / <a href> can't reach them -- the browser never attaches
 * a custom header to those native requests. Fetching by hand and handing
 * back a blob: URL is the standard workaround.
 *
 * @param {string} path - Path relative to the API base URL.
 * @returns {Promise<string|null>} An object URL, or null on a 404.
 */
async function fetchBlobUrl(path) {
  const res = await fetch(`${BASE_URL}${path}`, { headers: await authHeader() })
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`)
  return URL.createObjectURL(await res.blob())
}

/**
 * Open one item's CV or cover letter PDF in a new tab.
 *
 * @param {number} itemId
 * @param {'cv'|'cover-letter'} asset
 */
export async function openAsyncApplyAsset(itemId, asset) {
  const url = await fetchBlobUrl(`/asyncapply/items/${itemId}/${asset}`)
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

/**
 * Fetch a company's logo as a blob URL, for an <img src>. Resolves to null
 * if no logo was uploaded.
 *
 * @param {string} company
 * @returns {Promise<string|null>}
 */
export function fetchAsyncApplyLogoUrl(company) {
  return fetchBlobUrl(`/asyncapply/companies/${encodeURIComponent(company)}/logo`)
}

export async function uploadAsyncApplyLogo(company, file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/asyncapply/companies/${encodeURIComponent(company)}/logo`, {
    method: 'PUT',
    headers: await authHeader(),
    body: form,
  })
  if (!res.ok) throw new Error(`API error ${res.status} uploading logo`)
  return res.json()
}

// --- AsyncApply config ---

export function getAsyncApplyProfile() {
  return request('/asyncapply/config/profile')
}

export function updateAsyncApplyProfile(profile) {
  return request('/asyncapply/config/profile', { method: 'PUT', body: JSON.stringify(profile) })
}

export async function fillAsyncApplyProfileFromCv(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/asyncapply/config/profile/from-cv`, {
    method: 'POST',
    headers: await authHeader(),
    body: form,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API error ${res.status} filling profile from CV: ${text}`)
  }
  return res.json()
}

export function getAsyncApplyAgentDna() {
  return request('/asyncapply/config/agent-dna')
}

export function updateAsyncApplyAgentDna(choices, notes) {
  return request('/asyncapply/config/agent-dna', { method: 'PUT', body: JSON.stringify({ choices, notes }) })
}

export function getAsyncApplyAgentDnaAdminNote() {
  return request('/asyncapply/config/agent-dna-admin-note')
}

export function updateAsyncApplyAgentDnaAdminNote(content) {
  return request('/asyncapply/config/agent-dna-admin-note', { method: 'PUT', body: JSON.stringify({ content }) })
}

export function getAsyncApplyMe() {
  return request('/asyncapply/me')
}

export function getAsyncApplyModes() {
  return request('/asyncapply/config/modes')
}

export function getAsyncApplyMode(name) {
  return request(`/asyncapply/config/modes/${name}`)
}

export function updateAsyncApplyMode(name, content) {
  return request(`/asyncapply/config/modes/${name}`, { method: 'PUT', body: JSON.stringify({ content }) })
}

export function getAsyncApplySettings() {
  return request('/asyncapply/config/settings')
}

export function updateAsyncApplySettings(settings) {
  return request('/asyncapply/config/settings', { method: 'PUT', body: JSON.stringify(settings) })
}

export function getAsyncApplyAvailableModels() {
  return request('/asyncapply/config/available-models')
}

// --- AsyncApply admin ---

export function getAsyncApplyAdminUsers() {
  return request('/asyncapply/admin/users')
}

export function getAsyncApplyAdminUserDetail(id) {
  return request(`/asyncapply/admin/users/${id}/detail`)
}

export function updateAsyncApplyAdminBudget(id, tokenBudgetUsd) {
  return request(`/asyncapply/admin/users/${id}/budget`, {
    method: 'PATCH',
    body: JSON.stringify({ token_budget_usd: tokenBudgetUsd }),
  })
}

export function getAsyncApplyAdminStats(window) {
  return request(`/asyncapply/admin/stats${toQueryString({ window })}`)
}
