# Profile maintenance

This repository is special because its name matches the GitHub username. GitHub renders
`README.md` directly on the account overview.

## Automated activity panel

`scripts/generate_profile.py` reads public contribution and repository signals from GitHub's
GraphQL API and generates `assets/activity.svg`. The scheduled workflow runs daily and commits
only when the SVG changes. It uses no third-party statistics service and exposes no secret.

Run locally from PowerShell:

```powershell
$env:GITHUB_TOKEN = gh auth token
python scripts/generate_profile.py
Remove-Item Env:GITHUB_TOKEN
python -m unittest discover -s tests -v
```

## Achievements

GitHub achievements should reflect real collaboration. Do not create spam issues, fake reviews,
or empty pull requests. Useful paths are meaningful pull requests to maintained projects,
substantive code reviews, accepted discussion answers, pair-programmed commits, and projects that
earn genuine stars.

