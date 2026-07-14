# Setup after the first automated refresh

The generated profile README replaces the template's top-level `README.md`. This
guide remains here for future edits.

- Change your bio, scoring weights, or summary provider in `config.yml`.
- Run **Update profile README** manually from the Actions tab to apply changes.
- Keep the repository public and named exactly after your GitHub username for GitHub
  to show its README on your profile.
- The scheduled job checks public repository activity at 17 minutes past every
  hour and only pushes a commit when the rendered profile actually changes.

## Refresh after commits

The default setup needs no extra token. It polls GitHub hourly, updates project
selection and last-commit dates, then skips the commit when nothing changed.

For immediate refreshes, the profile workflow also accepts a `repository_dispatch`
event with type `profile-update`. Sending that event from another repository
requires a fine-grained token or GitHub App with access to the profile repository;
never place that credential directly in a workflow file. Store it as a repository
secret in each source repository.

## Writing your introduction

All personal content lives in `config.yml`. Fill in only the fields you want to
show; optional empty lists and strings are hidden automatically.

For a fully automatic profile, set only `profile.github_username`. The display
name comes from GitHub, while role, interests, strengths, current focus, stacks,
featured repositories, language mix, and repository activity are inferred from
public repository data. Any non-empty value in `config.yml` overrides the inferred
value.

```yaml
profile:
  name: "Your name"
  headline: "The kind of developer you are in one sentence"
  introduction: >-
    A concise two-sentence introduction shown at the top of your profile.
  story: >-
    Explain what motivates you, how you solve problems, and what you learned from
    your work. Three to five sentences is usually enough.
  affiliation: "School, team, or company"
  interests: ["Backend", "Cloud", "AI"]
  certifications: []
  strengths:
    - "A strength supported by a concrete behavior"
    - "Another strength"
  current_focus:
    - "What you are learning or building now"
  email: ""
  blog_url: ""
```

Add technologies to `stacks`, then list experience under `activities`. Repository
cards and the language chart are generated from your public GitHub repositories,
so they do not need to be entered manually.

The top profile visual is generated automatically from the same GitHub data.
Change `render.theme_color` to a six-digit hex color without `#` to customize
its accent.

## Apply it to your GitHub profile

1. Create a **public** GitHub repository whose name exactly matches your GitHub username.
2. Upload this project to that repository and edit `config.yml` on the default branch.
3. Open **Settings → Actions → General** and set workflow permissions to
   **Read and write permissions** if it is not already enabled.
4. Open **Actions → Update profile README → Run workflow**.
5. After the workflow finishes, visit your GitHub profile. The generated top-level
   `README.md` appears automatically and refreshes once per day.
