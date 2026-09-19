# P3-B71 source3 selection acceptance

日期：2026-09-20

## 結論

`SELECTED / SOURCE AND WINDOWS FROZEN / ZERO CAPTION ACCESS`。依事前固定query、provider排名與排除規則，唯一一次搜尋選中
官方頻道影片`j6Hlk9cY9LQ`（`【APEX】弾を打ってみます【ぶいすぽ/一ノ瀬うるは】`），duration=`12,883s`、rank=`2`。

- provider search invocation=`1`、return code=`0`、elapsed=`0.936168s`。
- raw search stdout=`15,402 bytes`只在記憶解析後丟棄；stdout/stderr內容未保存。
- 已在caption metadata/content前固定四列`600/1200/1800/2400s` context與各自下一分鐘future。
- caption metadata/content、model、future、retry、fallback=`0/0/0/0/0/0`。
- result hash=`8b6e043bb09c236bdef8867c973a242c94fc69dda5ddc172198f1012318db92d`。

這只證明第三來源依規則被事前選定。尚不知道是否有日文字幕，也沒有prediction或system/baseline效果證據；若字幕不可用，
必須保存負結果，不得改query或換到有利來源。
