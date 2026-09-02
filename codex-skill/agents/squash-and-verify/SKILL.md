---
name: squash-and-verify
description: Clean up a messy feature branch (many small commits, possibly several merge commits from repeatedly pulling in upstream changes) into a small number of logically-grouped commits, verify the squash didn't silently lose or add anything, then safely force-push and fast-forward merge it into the target branch (master/main). Use this whenever the user wants to squash commits before merging, says the branch history is "too messy"/"提交太乱"/"commit 太多", asks to "clean up before merging", or asks to prepare a long-lived feature branch for a clean merge into master. Also trigger proactively after helping resolve a multi-round merge conflict resolution session, right before the user is about to merge into master — that's exactly when history tends to be messiest.
---

# Squash and verify

A feature branch that has absorbed multiple rounds of upstream merges (each pulling in someone else's commits) ends up with a history that's part "what I did" and part "what everyone else did, interleaved." Squashing throws away the interleaving and keeps only the net contribution — but done carelessly, a manual squash can silently drop a file, double-apply a change, or clobber commits a teammate pushed in the meantime. This skill is the checklist that prevents those specific failure modes, learned from doing this exact workflow on a real repo.

Every step below exists to catch one specific way this goes wrong. Skipping a step doesn't just save time — it reopens exactly the failure mode that step was added for.

## Step 0: confirm the target branch is fully absorbed

Before touching anything, check that the target branch (usually `master`) is already an ancestor of the feature branch:

```bash
git fetch origin <target>
git merge-base --is-ancestor <target> <feature-branch> && echo "safe to squash" || echo "STOP: feature branch is missing upstream commits"
```

**Why this matters:** squashing computes a diff against the feature branch's merge-base with `<target>`. If the feature branch hasn't merged the *latest* target yet, the squash will bake in a diff against a stale target — and when you later try to fast-forward merge, it either fails outright or (worse) silently reintroduces changes that target already has, disguised as "your" commit. If the check fails, stop and have the user merge/rebase the latest target into the feature branch first. Don't try to route around this by squashing anyway and resolving conflicts during the squash — that reintroduces exactly the "which side wins" ambiguity squashing is supposed to eliminate.

## Step 1: squash the net diff onto a clean temp branch

```bash
git checkout -b _squash_tmp <target>
git merge --squash <feature-branch>
git reset
```

`git merge --squash` stages the *entire* net diff between the merge-base and the feature branch tip as one changeset, without creating a merge commit. `git reset` unstages it immediately — don't commit yet. The point of doing this on a fresh branch off `<target>` (not in place on the feature branch) is that if anything goes wrong you can just delete `_squash_tmp` and nothing is lost; the original feature branch and its full history are untouched until Step 4.

## Step 2: re-commit in logical groups, not one giant commit

Look at what changed (`git status`, `git diff --stat`) and group by concern — e.g. core feature code, config/env changes, frontend display, prompt/docs content, dev tooling. Stage each group explicitly and commit with a message that explains *why*, not just *what*:

```bash
git add <specific files for this group>
git commit -m "$(cat <<'EOF'
type(scope): what changed and why

More detail if needed.
EOF
)"
```

A few things that matter here:

- **Never `git add -A` or `git add .`.** After a squash-merge, the working tree often has unrelated pre-existing changes sitting around (stray log files, editor scratch directories, other in-progress work the user hasn't committed yet). Blanket-adding sweeps those into your squashed commits. Always name the files you actually mean to include for that group.
- **One commit per concern is a starting point, not a rule.** If the whole diff is small and cohesive, one commit is fine. The goal is "someone skimming `git log --oneline` understands what happened," not "hit a specific commit count."
- **Use a heredoc for the commit message** (as above) so multi-line messages with proper formatting go through cleanly, matching how commits are made throughout a normal session.

## Step 3: verify the squash is lossless before going any further

This is the step that catches "I forgot to `git add` a file" or "I accidentally staged something twice." Don't skip it just because Step 2 felt careful — that feeling is exactly what a missed file feels like too.

```bash
git diff <feature-branch> _squash_tmp
```

**This must be empty.** If it isn't, the squashed branch's content differs from the original feature branch's content — something was dropped, duplicated, or altered while re-grouping commits. Go back and fix it before proceeding; don't rationalize a nonempty diff as "probably fine."

Then re-run whatever verifies the code actually works, on `_squash_tmp`:

```bash
python3 -m compileall -q <source_dir>   # or the project's equivalent build/typecheck step
<test command>                          # e.g. pytest, npm test, go test ./...
```

Confirm the pass count matches what it was before the squash. If a test fails to even collect (import error, path issue), check whether that's pre-existing and unrelated before blaming the squash:

```bash
git log --oneline --all -- <the failing file>
```

If that file has history going back well before this branch existed, the failure predates your work — don't spend time "fixing" it as part of this squash.

## Step 4: replace the branch and force-push

```bash
git branch -f <feature-branch> _squash_tmp
git checkout <feature-branch>
git branch -D _squash_tmp
git push --force-with-lease origin <feature-branch>
```

**Use `--force-with-lease`, never a bare `--force`.** A bare force-push overwrites whatever is on the remote unconditionally. `--force-with-lease` refuses if the remote has moved since your last fetch — which is exactly the case where someone else pushed to this branch while you were squashing, and a bare force would silently discard their work. If the lease check fails, stop and find out what changed remotely before overriding it.

This step rewrites history that may already be pushed. Flag it to the user before running it if there's any chance someone else has this branch checked out or has commits on it you don't know about — this is the one genuinely hard-to-reverse action in the whole workflow.

## Step 5: fast-forward merge into the target

```bash
git fetch origin <target>
git rev-parse origin/<target> <target>   # confirm these two hashes match — local target is fully in sync
git checkout <target>
git merge --ff-only <feature-branch>
git push origin <target>
```

**Use `--ff-only`, not a plain `git merge`.** Because Step 0 already confirmed `<target>` is an ancestor of the feature branch, this merge *should* always be a fast-forward — no merge commit, no conflicts. Requiring `--ff-only` turns any violation of that assumption into a loud, immediate error instead of a silent merge commit or conflict resolution you didn't expect. If `--ff-only` fails, something changed on `<target>` between Step 0 and now (re-fetch and re-check, don't force through it).

## Quick sanity checklist before calling it done

- [ ] Step 0 ancestor check passed (didn't skip it)
- [ ] `git diff <feature-branch> _squash_tmp` was empty
- [ ] Build/compile check passed on the squashed branch
- [ ] Test suite pass count matches pre-squash (any failures explained as pre-existing)
- [ ] Force-push used `--force-with-lease`, and the user was told this rewrites pushed history
- [ ] Final merge into target used `--ff-only` and actually reported "Fast-forward"
