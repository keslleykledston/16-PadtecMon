# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-12-05

### Added
- **Frontend - Alarms Tab**:
  - Added severity-based sorting (CRITICAL → MAJOR → MINOR → WARNING).
  - Added site information below card name in italic, smaller font.
  - Implemented card index system showing "Site-[Serial]-Model" format.
- **Frontend - Cards Tab**:
  - Added "Actions" column with info button for device metrics.
  - Implemented device metrics modal with on-demand data fetching.
  - Modal displays measurements table with name, value, unit, group, and timestamp.
  - Added loading state and empty state handling for measurements.
- **Backend - Alarms**:
  - Added JOIN query with cards table to generate card names.
  - Added `cardName` and `cardModel` fields to alarm responses.
- **Collector - Alarm Sync**:
  - Implemented automatic alarm synchronization every 15 seconds.
  - Added logic to detect and clear alarms no longer active in API.
  - Added `get_active_alarm_ids()` and `update_alarms_status()` database methods.
  - Implemented consistent alarm ID generation using MD5 hash fallback.

### Changed
- **Frontend - Alarms Tab**:
  - Removed separate "Site" column from alarms table.
  - Changed "Card" column header to "Card / Site".
  - Updated default filter to show only ACTIVE alarms.
- **Collector - Alarms**:
  - Updated `upsert_alarm()` to correctly map API fields (`alarmName` → `description`, `alarmSeverity` → `severity`).
  - Modified alarm status update query to use explicit type casting for PostgreSQL compatibility.
  - Removed `updated_at` column reference (column doesn't exist in schema).

### Fixed
- **Collector - Alarms**:
  - Fixed PostgreSQL type ambiguity errors in `update_alarms_status()` query.
  - Fixed alarm field mapping to correctly populate description from `alarmName`.
  - Fixed timestamp parsing to handle various date formats from API.
- **Frontend - Alarms**:
  - Clarified that multiple alarms per card are distinct alarms, not duplicates.

## [Previous] - 2025-12-04

### Added
- **Frontend**:
  - Added "Sync Sites" button to the Sites tab to trigger manual synchronization.
  - Added "Sync Cards" button to the Cards tab.
  - Added search functionality to Sites, Cards, and Alarms tabs.
  - Added sorting functionality to the Cards table (click on headers).
  - Implemented periodic API connection status monitoring in the Configuration tab (checks every 5 minutes).
- **Backend**:
  - Added `POST /sites/sync` endpoint to trigger site synchronization.
  - Added `GET /config/padtec-status` endpoint for periodic connection checks.
- **Collector**:
  - Added `POST /collector/sync-sites` endpoint to trigger card collection.

### Changed
- **Frontend**:
  - Updated Card status logic:
    - Cards with `cardModel` containing "MUX_DEMUX" are now displayed as "PASSIVE" (Blue).
    - Cards not updated within the last 2 minutes (relative to the latest collection time) are displayed as "OFFLINE" (Red).
    - Active cards are displayed as "ONLINE" (Green).
  - Updated `Cards` table to include `lastUpdated` data for status calculation.
- **Collector**:
  - **Pagination**: Updated `PadtecClient.get_cards` to fetch all pages of cards from the API, ensuring complete inventory collection.
  - **Scheduling**: Changed card collection schedule to run daily at 00:01 instead of every hour.
  - **Database**: Fixed type casting for `card_part` (ensuring it's treated as a string) to prevent database insertion errors.
  - **API Client**: Removed incorrect `/api` prefix from Padtec API endpoints.
- **Backend**:
  - Refactored connection testing logic into a reusable `_check_padtec_connection` function.

### Fixed
- Fixed database `DataError` where integer values for `card_part` caused insertion failures.
- Fixed API URL construction in `PadtecClient`.
