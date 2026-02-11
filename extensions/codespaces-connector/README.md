# GitHub Codespaces Auto Connector

VS CodeからGitHub Codespacesへの接続を自動化するVS Code拡張機能です。

## 機能

- ✅ GitHub Codespaces拡張機能のインストール状態チェック
- ✅ GitHub認証フローの自動処理
- ✅ 利用可能なCodespacesリストの取得
- ✅ 視覚的なフィードバック（ステータスバー）
- ✅ 詳細なログ出力
- ✅ エラーハンドリング

## セットアップ

### 1. 依存関係のインストール

```bash
cd .vscode/codespaces-connector
npm install
```

### 2. コンパイル

```bash
npm run compile
```

または、ウォッチモードで自動コンパイル:

```bash
npm run watch
```

### 3. 拡張機能のテスト

1. VS Codeで `.vscode/codespaces-connector` フォルダを開く
2. `F5` キーを押してExtension Development Hostを起動
3. コマンドパレット（`Ctrl+Shift+P` または `Cmd+Shift+P`）を開く
4. `Connect to GitHub Codespaces (Auto)` を実行

## 使用方法

### コマンドから実行

1. コマンドパレット（`Ctrl+Shift+P` または `Cmd+Shift+P`）を開く
2. `Connect to GitHub Codespaces (Auto)` と入力して実行
3. 画面の指示に従って接続

### 実行フロー

1. **拡張機能チェック**: GitHub Codespaces拡張機能がインストールされているか確認
2. **認証確認**: GitHub認証状態をチェック（未認証の場合はサインインを促す）
3. **Codespaces取得**: 利用可能なCodespacesリストを取得
4. **選択**: ユーザーが接続先Codespaceを選択
5. **接続**: 選択されたCodespaceに接続
6. **確認**: 接続状態を確認してフィードバック

## ログ出力

詳細なログは「出力」パネルの「Codespaces Connector」チャンネルで確認できます:

```
=== GitHub Codespaces Connector ===
Started at: 2026-02-11T10:30:00.000Z

[1/9] Checking GitHub Codespaces extension...
✅ GitHub Codespaces extension is installed

[2/9] ✅ Extension already active

[3/9] Checking GitHub authentication...
✅ Already authenticated with GitHub
    Account: username

[5/9] Fetching available Codespaces...
✅ Found 3 Codespace(s)
    1. my-codespace-1 (Available) - user/repo1
    2. my-codespace-2 (Available) - user/repo2
    3. my-codespace-3 (Shutdown) - user/repo3

[6/9] Prompting user to select a Codespace...
✅ Selected: my-codespace-1

[7/9] Connecting to Codespace...
✅ Connection command executed

[8/9] Waiting for connection to complete...

[9/9] Verifying connection status...
✅ Connected to Codespace: my-codespace-1

=== Connection process completed ===
Finished at: 2026-02-11T10:30:15.000Z
```

## エラーハンドリング

以下のエラーが処理されます:

- ❌ GitHub Codespaces拡張機能が未インストール → インストールを促す
- ❌ GitHub未認証 → サインインフローを開始
- ❌ Codespacesが存在しない → 作成オプションを提示
- ❌ 接続失敗 → エラーメッセージとログを表示

## ステータスバー表示

接続プロセス中、ステータスバーに進捗が表示されます:

- `$(sync~spin) Connecting to Codespaces...` - 接続処理中
- `$(sync~spin) Fetching Codespaces...` - Codespaces取得中
- `$(check) Connected: codespace-name` - 接続成功
- `$(error) Connection Failed` - 接続失敗

## 開発

### ファイル構成

```
.vscode/codespaces-connector/
├── src/
│   └── extension.ts          # メインロジック
├── out/                       # コンパイル済みJavaScript（自動生成）
├── package.json              # 拡張機能マニフェスト
├── tsconfig.json             # TypeScript設定
├── .eslintrc.json            # ESLint設定
└── README.md                 # このファイル
```

### コンパイルとウォッチ

```bash
# 一回だけコンパイル
npm run compile

# ウォッチモード（ファイル変更を自動検知）
npm run watch

# リント
npm run lint
```

## トラブルシューティング

### 拡張機能が動作しない

1. `npm install` を実行して依存関係をインストール
2. `npm run compile` でTypeScriptをコンパイル
3. VS Codeをリロード（`Ctrl+R` または `Cmd+R`）

### 認証に失敗する

1. GitHub設定でトークンが有効か確認
2. VS Codeを再起動
3. 手動で `GitHub: Sign in` コマンドを実行

### Codespacesリストが取得できない

1. ブラウザでGitHub Codespacesにアクセスできるか確認
2. 認証スコープに `codespace` が含まれているか確認
3. ネットワーク接続を確認

## ライセンス

このプロジェクトのライセンスに従います。
