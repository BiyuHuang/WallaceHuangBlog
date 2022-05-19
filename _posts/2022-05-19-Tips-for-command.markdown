---
layout: post
title: "Tips for command"
date: 2022-05-19 14:35:05 +0800
description: Tips for command
img: # Add image post (optional)
---

# Tips for command
- git releated
    - push
    ```bash
    git push origin YOUR_BRANCH # normal push commits
    git purh origin YOUR_BRANCH --force # force option will rewrite commit history
    ```
    - merge-rebase
    ```bash
    fork_point=$(git merge-rebase --fork-point origin/master YOUR_BRANCH)
    git rebase --onto origin/master $fork_point YOUR_BRANCH
    ```
    - rebase
    ```bash
    git rebase -i head~n # rebase form number n commits before head
    git rebase -i --root # rebase from the root of BRANCH
    ```
- npm releated
    - install
    ```bash
    npm install
    ```
