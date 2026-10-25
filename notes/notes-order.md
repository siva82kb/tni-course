# Order of the companion notes

The reading order of the notes pages. Each generator reads this table and puts
previous/next links in its crumb row and at the end of its page, and
`build-notes-list.py` writes the list the course homepage includes from it.
To insert a note, add a row and renumber; to reorder, move rows. Then rebuild
every note (the neighbours' links change) and run `build-notes-list.py`.
Paths are relative to `notes/`. Keep the table's three columns and one note per row.

| # | File | Title |
|---|------|-------|
| 1 | 01-kinematics-kinetics/dlt-notes.html | Camera calibration by the Direct Linear Transform |
| 2 | 01-kinematics-kinetics/ik-notes-thigh.html | Inverse kinematics of a single link |
| 3 | 01-kinematics-kinetics/ik-notes-leg.html | Inverse kinematics of a two-link leg |
| 4 | 01-kinematics-kinetics/fiducial-notes.html | Pose of a fiducial marker from one image |
