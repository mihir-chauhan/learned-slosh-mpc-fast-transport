# Iterations (improve phase)

One file per iteration, created by `rh iter new "<hypothesis>" --prediction "<what we expect>" --move <type>`.
Each iteration changes ONE thing, predicts the outcome before running, validates on the validation
split / primary task, and is closed with `rh iter close <n> --outcome improved|no_change|worse|failed|pivot`.
A promoted variant becomes the new champion: re-run all main + ablation seeds under the same name,
then `rh supersede --group main --name "<method>"` (and per ablation group) so tables show only the
current version while the registry keeps history.
