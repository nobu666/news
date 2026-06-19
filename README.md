# news

AI・ソフトウェアエンジニアリング・エンジニアリングマネジメントを中心に、時事・スポーツ・ゲーム・グルメ・ガジェット・クラウドファンディング・ふるさと納税まで、毎日のニュースを Web 検索で収集して日本語要約にまとめる Claude Code の scheduled task 一式。

収集結果は Obsidian Vault（`~/Documents/Obsidian/Vault/News/`）に Markdown で保存される。

## 構成

| タスク | 出力ファイル | 用途 |
|---|---|---|
| [`tech-news-morning`](tech-news-morning/SKILL.md) | `YYYY-MM-DD-morning.md` | 朝刊 |
| [`tech-news-evening`](tech-news-evening/SKILL.md) | `YYYY-MM-DD-evening.md` | 夕刊 |

morning / evening は見出し（朝刊 / 夕刊）と出力ファイル名以外は同一仕様。収集カテゴリ・ソース・フォーマットは両者で揃えている。

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

`install.sh` は各 SKILL.md を `~/.claude/scheduled-tasks/<task>/SKILL.md` に **シンボリックリンク**する。リポジトリ側を編集すれば、次回の scheduled task 実行にそのまま反映される。

## 編集方針

- リンクは実在する**個別記事の URL**を貼る（月次インデックスやニュース一覧ページは不可）
- カテゴリ・ソースを追加したいときは morning / evening 両方の SKILL.md を揃えて更新する

## ライセンス

[MIT](LICENSE)
