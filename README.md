# news

AI・ソフトウェアエンジニアリング・エンジニアリングマネジメントを中心に、時事・スポーツ・ゲーム・グルメ・ガジェット・クラウドファンディング・ふるさと納税まで、毎日のニュースを Web 検索で収集して日本語要約にまとめる Claude Code の scheduled task 一式。

収集結果は Obsidian Vault（`~/Documents/Obsidian/Vault/News/`）に Markdown で保存される。

## 構成

[`daily-news`](daily-news/SKILL.md) という単一タスク。1日2回（朝・夕）実行され、**実行時刻で朝刊/夕刊を出し分ける**（12時より前なら朝刊、以降なら夕刊）。

| 版 | 出力ファイル | 判定 |
|---|---|---|
| 朝刊 | `YYYY-MM-DD-morning.md` | 実行時刻が 12 時より前 |
| 夕刊 | `YYYY-MM-DD-evening.md` | 実行時刻が 12 時以降 |

cron は `0 8,18 * * *` のように1タスクで朝夕2回発火させる。

## 収集カテゴリ

1. AI / 機械学習
2. ソフトウェアエンジニアリング
3. エンジニアリングマネジメント
4. 時事ニュース
5. 大谷翔平
6. ゲーム
7. 将棋
8. バズってる食べ物
9. 注目のガジェット・日用品・料理用品
10. 注目のクラウドファンディング
11. ふるさと納税

## インストール

```bash
git clone https://github.com/nobu666/news.git ~/repos/news
cd ~/repos/news
./install.sh
```

`install.sh` は SKILL.md を `~/.claude/scheduled-tasks/daily-news/SKILL.md` に **シンボリックリンク**する。リポジトリ側を編集すれば、次回の scheduled task 実行にそのまま反映される。

## 編集方針

- リンクは実在する**個別記事の URL**を貼る（月次インデックスやニュース一覧ページは不可）
- 仕様は `daily-news/SKILL.md` 一箇所に集約。朝刊/夕刊で内容を変えたい場合のみ「朝刊／夕刊の判定」セクションを起点に分岐させる

## ライセンス

[MIT](LICENSE)
