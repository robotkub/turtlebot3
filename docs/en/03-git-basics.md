← [2. Installing the software](02-install.md) | [Back to index](00-index.md) | Next: [4. Understanding Navigation →](04-navigation.md)

# 3. Git Basics

## What git is and why we use it

Git keeps a "history" of the code every time you save (commit). That means:
- You can go back to an older version of the code if a change breaks something -- nothing is ever really lost
- Multiple teammates can edit code at the same time without overwriting each other
- You can see who changed what, when, and why

**GitHub** is the website hosting our code (`https://github.com/robotkub/turtlebot3`).
Everyone on the team pulls the latest code from there, and pushes their
changes back up to it.

## Commands you'll use a lot

| Command | What it does |
|---|---|
| `git clone <url>` | Download a repo onto your machine (do this once, at the start) |
| `git status` | See which files you've changed but haven't committed yet |
| `git pull` | Pull the latest code from GitHub into your local copy |
| `git add <file>` | Tell git you want this file included in the next commit |
| `git commit -m "message"` | Save a snapshot of the code, with a message explaining why |
| `git push` | Send your commits up to GitHub so everyone else sees them too |
| `git log --oneline` | See the full commit history, one line each |

## The workflow this team uses

**Before you start editing code** -- always pull first, so you're not working on a stale copy:

```bash
cd ~/turtlebot3_ws
git pull
```

**Done editing and want to save it**:

```bash
git status                          # see what you actually changed
git add src/ttb3_mission/ttb3_mission/mission_manager.py   # stage the file(s) you want to commit
git commit -m "explain WHY you changed this, not what"
git push
```

## What makes a good commit message

Write **why** you changed something, not **what** (the diff already shows what):

- Good: `fix: tighten approach_close_size so we get closer to the victim sign before dispensing`
- Not great: `fixed stuff`, `update`, `test`

## If `git push` gets rejected

If `git push` errors with "rejected" or "non-fast-forward", it means someone
else pushed before you (GitHub has newer commits than your local copy). Pull
first, then push again:

```bash
git pull
git push
```

If the pull hits a merge conflict (both sides edited the same lines), git
marks the conflicting spots with `<<<<<<<` / `=======` / `>>>>>>>` in the
file. Open it, decide which lines to keep, delete the conflict markers, then
`git add` + `git commit` as normal.

**Don't use** `git push --force` or `git reset --hard` without asking the
team first -- these can permanently destroy someone else's work.

Ready? Move on to [Chapter 4: Understanding Navigation](04-navigation.md).

---
← [2. Installing the software](02-install.md) | [Back to index](00-index.md) | Next: [4. Understanding Navigation →](04-navigation.md)
