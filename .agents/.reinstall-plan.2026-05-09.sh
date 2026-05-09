#!/bin/bash
set -e

echo '== 1/11: [JimLiu/baoyu-skills] -> warp (symlink, 17 skills) =='
npx -y skills add JimLiu/baoyu-skills -g -a warp -s baoyu-article-illustrator baoyu-comic baoyu-compress-image baoyu-cover-image baoyu-danger-gemini-web baoyu-danger-x-to-markdown baoyu-format-markdown baoyu-image-gen baoyu-infographic baoyu-markdown-to-html baoyu-post-to-wechat baoyu-post-to-weibo baoyu-post-to-x baoyu-slide-deck baoyu-translate baoyu-url-to-markdown baoyu-xhs-images -y

echo '== 2/11: [anthropics/skills] -> claude-code (symlink, 1 skills) =='
npx -y skills add anthropics/skills -g -a claude-code -s skill-creator -y

echo '== 3/11: [larksuite/cli] -> claude-code (symlink, 21 skills) =='
npx -y skills add larksuite/cli -g -a claude-code -s lark-approval lark-base lark-calendar lark-contact lark-doc lark-drive lark-event lark-im lark-mail lark-minutes lark-openapi-explorer lark-shared lark-sheets lark-skill-maker lark-task lark-vc lark-whiteboard lark-whiteboard-cli lark-wiki lark-workflow-meeting-summary lark-workflow-standup-report -y

echo '== 4/11: [larksuite/cli] -> kiro-cli (symlink, 21 skills) =='
npx -y skills add larksuite/cli -g -a kiro-cli -s lark-approval lark-base lark-calendar lark-contact lark-doc lark-drive lark-event lark-im lark-mail lark-minutes lark-openapi-explorer lark-shared lark-sheets lark-skill-maker lark-task lark-vc lark-whiteboard lark-whiteboard-cli lark-wiki lark-workflow-meeting-summary lark-workflow-standup-report -y

echo '== 5/11: [larksuite/cli] -> openclaw (copy, 21 skills) =='
npx -y skills add larksuite/cli -g -a openclaw -s lark-approval lark-base lark-calendar lark-contact lark-doc lark-drive lark-event lark-im lark-mail lark-minutes lark-openapi-explorer lark-shared lark-sheets lark-skill-maker lark-task lark-vc lark-whiteboard lark-whiteboard-cli lark-wiki lark-workflow-meeting-summary lark-workflow-standup-report -y --copy --dangerously-accept-openclaw-risks

echo '== 6/11: [larksuite/cli] -> qwen-code (symlink, 21 skills) =='
npx -y skills add larksuite/cli -g -a qwen-code -s lark-approval lark-base lark-calendar lark-contact lark-doc lark-drive lark-event lark-im lark-mail lark-minutes lark-openapi-explorer lark-shared lark-sheets lark-skill-maker lark-task lark-vc lark-whiteboard lark-whiteboard-cli lark-wiki lark-workflow-meeting-summary lark-workflow-standup-report -y

echo '== 7/11: [larksuite/cli] -> trae (symlink, 21 skills) =='
npx -y skills add larksuite/cli -g -a trae -s lark-approval lark-base lark-calendar lark-contact lark-doc lark-drive lark-event lark-im lark-mail lark-minutes lark-openapi-explorer lark-shared lark-sheets lark-skill-maker lark-task lark-vc lark-whiteboard lark-whiteboard-cli lark-wiki lark-workflow-meeting-summary lark-workflow-standup-report -y

echo '== 8/11: [larksuite/cli] -> windsurf (symlink, 21 skills) =='
npx -y skills add larksuite/cli -g -a windsurf -s lark-approval lark-base lark-calendar lark-contact lark-doc lark-drive lark-event lark-im lark-mail lark-minutes lark-openapi-explorer lark-shared lark-sheets lark-skill-maker lark-task lark-vc lark-whiteboard lark-whiteboard-cli lark-wiki lark-workflow-meeting-summary lark-workflow-standup-report -y

echo '== 9/11: [nashsu/autocli-skill] -> claude-code (symlink, 1 skills) =='
npx -y skills add nashsu/autocli-skill -g -a claude-code -s autocli -y

echo '== 10/11: [nashsu/autocli-skill] -> openclaw (copy, 1 skills) =='
npx -y skills add nashsu/autocli-skill -g -a openclaw -s autocli -y --copy --dangerously-accept-openclaw-risks

echo '== 11/11: [tw93/Waza] -> openclaw (copy, 7 skills) =='
npx -y skills add tw93/Waza -g -a openclaw -s check design health hunt read think write -y --copy --dangerously-accept-openclaw-risks
