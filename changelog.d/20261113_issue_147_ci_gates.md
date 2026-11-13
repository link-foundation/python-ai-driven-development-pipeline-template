### Fixed

- Run pinned ShellCheck in an isolated environment without pipx PATH warnings.
- Revalidate a moving main branch before release rather than attempting an
  unreachable rebase, preserving original release inputs and source attestation.
- Prevent PR link and Docker jobs from writing caches that main cannot reuse.
- Apply source line limits to shell, JavaScript and MJS helpers.
- Reject oversized distributions before artifact upload and PyPI publication,
  with a configurable per-file budget and largest-member diagnostics.

### Security

- Verify lychee downloads against committed digests for both supported Linux
  architectures, independently of replaceable release checksum assets.
