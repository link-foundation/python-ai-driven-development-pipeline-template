### Fixed
- Cancel superseded read-only CI checks on main and pull requests, while serializing release, Docker and Pages writers without cancelling active publications.
- Retry pinned lychee downloads, verify SHA-256 checksums, and preserve link reports, summaries and failure handling without lychee-action's single-download failure.
