---
layout: post
title: "Tips for command"
date: 2022-05-19 14:35:05 +0800
description: Tips for command
tags: BigData
img:  # Add image post (optional)
---

# Tips for command

- __git__ related
    - ___git push___
      ```bash
      git push origin YOUR_BRANCH # normal push commits
      git push origin YOUR_BRANCH --force # force option will rewrite commit history                                      
      ```
    - ___git merge-base___
      ```bash
      fork_point=$(git merge-base --fork-point origin/master YOUR_BRANCH)
      git rebase --onto origin/master $fork_point YOUR_BRANCH
      ```
    - ___git rebase___
      ```bash
      git rebase -i head~n # rebase form number n commits before head
      git rebase -i --root # rebase from the root of BRANCH
      ```
- __bash__ related
    - ___find___
      ```bash
      find . -maxdepth 5 -mindepth 2 -type f -name "*.csv" | xargs -n1 dirname | sort -u
      find . -maxdepth 2 -type f -name "*.dat" -exec chmod 644 {} \;
      ```
    - ___bash___
      ```bash
      bash -c "java -version"
      ```
- __npm__ related
    - ___install___
      ```bash
      npm install
      ```