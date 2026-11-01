### Fixed

- Override `archiver-utils`' deprecated `glob@10` with `glob@13.0.6` in the
  artifact action so clean installs emit no deprecation warnings; glob matches
  and ZIP bytes are unchanged and the committed bundle is regenerated.
