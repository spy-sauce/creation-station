/**
 * Route definitions for Talent Agent frontend.
 * Per NUTRIENTS.md §E — route map for react-router-dom@7.
 *
 * All navigation MUST use these constants. No inline route strings.
 */

export const routes = {
  landing: '/',
  login: '/login',
  verifyAuth: '/auth/verify',
  onboarding: '/onboarding',
  overview: '/overview',
  candidates: '/candidates',
  pipeline: '/pipeline',
  reviewQueue: '/review-queue',
  analytics: '/analytics',
  settings: '/settings',
}

/**
 * Get route name from path (for reverse lookup).
 * @param {string} path - The pathname to look up
 * @returns {string|null} The route name or null if not found
 */
export function getRouteName(path) {
  for (const [name, route] of Object.entries(routes)) {
    if (route === path) return name
  }
  return null
}

/**
 * Page titles keyed by route path.
 * Used by TopBar and document title.
 */
export const pageTitles = {
  [routes.overview]: 'Overview',
  [routes.candidates]: 'Candidates',
  [routes.pipeline]: 'Pipeline',
  [routes.reviewQueue]: 'Review Queue',
  [routes.analytics]: 'Analytics',
  [routes.settings]: 'Settings',
}
