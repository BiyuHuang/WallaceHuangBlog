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
    - ___git reset___
      ````
       git reset --hard HEAD~1 # rollback to the last commit and discard any changes
      ````
    - ___git config___
      ```bash
      git config --global alias.cb "branch --show-current" # set alias
      git config --global --unset alias.cb  # unset alias
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
      
- __s3__ related
    - ___list objects___
      ```bash
      aws s3api --endpoint {ENDPOINT} list-objects --bucket {BUCKET_NAME}
      ```
    - ___get object___
      ```bash
      aws s3api --endpoint {ENDPOINT} get-object --bucket {BUCKET_NAME} --key {KEY_NAME} {TARGET_FILE}
      ```
    - ___put object___
      ```bash
      aws s3api --endpoint {ENDPOINT} put-object --bucket {BUCKET_NAME} --key {KEY_NAME} --body {TO_BE_UPLOADED_SOURCE}
      ```
    - ___delete object___
      ```bash
      aws s3api --endpoint {ENDPOINT} delete-object --bucket {BUCKET_NAME} --key {TO_BE_DELETED_KEY}
      ```

- __redis__ related
    - ___del keys by batch___
      ```bash
      redis-cli --scan --pattern "key-prefix-*" | xargs -L 2000 redis-cli del
      ``` 

- __curl__ related
    - ___query public IP address___  
      ```bash
      curl ip.sb
      ```
    - ___no-check-certificate___
      ```bash
      curl 'https://www.google.com' -k
      ```
- __dd__ related
    - ___random token___
      ```bash
      dd if=/dev/urandom bs=128 count=1 2>/dev/null |base64 |tr -d "=+/" |dd bs=32 count=1 2>/dev/null
      ```