---
layout: post
title: "Tips for command"
date: 2022-05-19 14:35:05 +0800
description: Tips for command
img: # Add image post (optional)
---

# Tips for command
- __git__ related
    - `git push`
      ```bash
      git push origin YOUR_BRANCH # normal push commits
      git push origin YOUR_BRANCH --force # force option will rewrite commit history
      ```
    - `git merge-rebase`
      ```bash
      fork_point=$(git merge-rebase --fork-point origin/master YOUR_BRANCH)
      git rebase --onto origin/master $fork_point YOUR_BRANCH
      ```
    - `git rebase`
      ```bash
      git rebase -i head~n # rebase form number n commits before head
      git rebase -i --root # rebase from the root of BRANCH
      ```
- __bash__ related
    - `find`
      ```bash
      find . -maxdepth 5 -mindepth 2 -type f -name "*.csv" | xargs -n1 dirname | sort -u
      find . -maxdepth 2 -type f -name "*.dat" -exec chmod 644 {} \;
      ```
- __npm__ related
    - `install`
      ```bash
      npm install
      ```
