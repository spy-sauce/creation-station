/**
 * Onboarding API client — resume upload, profile save, status check.
 *
 * Per NUTRIENTS.md API_CONTRACTS §Onboarding Endpoints:
 * - POST /api/v1/onboarding/resume — Upload + parse resume (multipart)
 * - POST /api/v1/onboarding/profile — Save candidate profile + preferences
 * - GET  /api/v1/onboarding/status — Onboarding completion status
 *
 * Backend response shapes per backend/api/onboarding.py.
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { apiClient } from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * Response from POST /onboarding/resume.
 * Per backend/api/onboarding.py ResumeUploadResponse.
 */
export interface ResumeUploadResponse {
  candidate_id: string
  /** Length in characters of the extracted resume text */
  text_length: number
  /** First 500 chars of extracted text for preview display */
  preview: string
}

/**
 * Remote work preference.
 * Per backend candidate profile model.
 */
export type RemotePreference = 'remote_only' | 'flexible' | 'on_site'

/**
 * Request body for POST /onboarding/profile.
 * Per backend/api/onboarding.py profile endpoint.
 */
export interface ProfileRequest {
  name: string
  linkedin_url: string | null
  github_url: string | null
  personal_context: string | null
  target_locations: string[] | null
  remote_preference: RemotePreference
  min_compensation: number | null
  excluded_companies: string[] | null
  excluded_industries: string[] | null
}

/**
 * Response from POST /onboarding/profile.
 * Per backend/api/onboarding.py ProfileResponse.
 */
export interface ProfileResponse {
  candidate_id: string
  is_onboarded: boolean
}

/**
 * Response from GET /onboarding/status.
 * Per backend/api/onboarding.py OnboardingStatusResponse.
 */
export interface OnboardingStatusResponse {
  is_onboarded: boolean
  has_resume: boolean
  has_profile: boolean
  candidate_id: string | null
}

// ─── API Functions ────────────────────────────────────────────────────────────

/**
 * Upload and parse a resume PDF.
 *
 * Sends the file as multipart/form-data. The backend extracts text, creates or
 * updates the candidate record, and returns a preview.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * POST /api/v1/onboarding/resume
 *
 * @param file - The resume PDF file
 * @returns Candidate id, extracted text length, and preview
 * @throws TalentAgentApiError on 400 (bad file) or other errors
 *
 * @example
 * ```ts
 * const res = await uploadResume(pdfFile)
 * // res.text_length, res.preview
 * ```
 */
export async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post<ResumeUploadResponse>('/onboarding/resume', formData)
}

/**
 * Save the candidate profile and search preferences.
 *
 * Completing this step marks the user as onboarded.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * POST /api/v1/onboarding/profile
 *
 * @param profile - The profile payload
 * @returns Candidate id and onboarding status
 * @throws TalentAgentApiError on 422 (validation) or other errors
 */
export async function saveProfile(profile: ProfileRequest): Promise<ProfileResponse> {
  return apiClient.post<ProfileResponse>('/onboarding/profile', profile)
}

/**
 * Get the current onboarding completion status.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * GET /api/v1/onboarding/status
 *
 * @returns Onboarding flags and candidate id
 * @throws TalentAgentApiError on errors
 */
export async function getOnboardingStatus(): Promise<OnboardingStatusResponse> {
  return apiClient.get<OnboardingStatusResponse>('/onboarding/status')
}
