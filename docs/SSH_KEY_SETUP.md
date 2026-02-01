# SSH鍵認証セットアップガイド

VPSへの安全なアクセスのため、SSH鍵認証を設定する詳細ガイドです。

## 📚 目次

1. [SSH鍵とは](#ssh鍵とは)
2. [鍵ペアの生成](#鍵ペアの生成)
3. [VPSへの公開鍵登録](#vpsへの公開鍵登録)
4. [SSH設定の強化](#ssh設定の強化)
5. [トラブルシューティング](#トラブルシューティング)

## SSH鍵とは

SSH鍵認証は、パスワード認証よりも安全な認証方式です。

**利点:**
- ブルートフォース攻撃に強い
- パスワード漏洩のリスクがない
- 自動化スクリプトでの使用が容易
- 複数デバイスからの安全なアクセス

**仕組み:**
- **秘密鍵**: ローカルマシンに保管（絶対に共有しない）
- **公開鍵**: VPSに登録（共有しても安全）

## 鍵ペアの生成

### Windows（PowerShell）

```powershell
# SSH鍵ペアの生成
ssh-keygen -t ed25519 -C "your_email@example.com"

# または RSA（より互換性が高い）
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### macOS / Linux

```bash
# ED25519（推奨: 高速で安全）
ssh-keygen -t ed25519 -C "your_email@example.com"

# または RSA
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### 鍵生成時の質問

```
Enter file in which to save the key (/home/user/.ssh/id_ed25519):
```
→ Enterで デフォルトのまま（推奨）

```
Enter passphrase (empty for no passphrase):
```
→ パスフレーズを入力（推奨）または空のままEnter

**パスフレーズを設定する場合:**
- 秘密鍵が盗まれても追加の保護層
- 面倒な場合はssh-agentで管理可能

### 生成された鍵の確認

```bash
# 秘密鍵（絶対に共有しない）
ls -la ~/.ssh/id_ed25519

# 公開鍵（VPSに登録する）
cat ~/.ssh/id_ed25519.pub
```

## VPSへの公開鍵登録

### 方法1: ssh-copy-id（最も簡単）

```bash
# Linux/macOS
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@<VPS_IP>

# パスワードを入力
# 自動的に公開鍵がVPSに登録される
```

### 方法2: 手動でコピー（Windows推奨）

#### Step 1: 公開鍵の内容をコピー

```bash
# Windows PowerShell
type $env:USERPROFILE\.ssh\id_ed25519.pub

# macOS/Linux
cat ~/.ssh/id_ed25519.pub
```

出力例:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJqfH... your_email@example.com
```

#### Step 2: VPSにログイン

```bash
ssh root@<VPS_IP>
# パスワードを入力
```

#### Step 3: authorized_keys に追加

```bash
# .sshディレクトリ作成
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 公開鍵を追加
nano ~/.ssh/authorized_keys
# ↑ コピーした公開鍵を貼り付け（1行で）

# パーミッション設定
chmod 600 ~/.ssh/authorized_keys
```

### 方法3: ConoHaコントロールパネル経由

1. ConoHaコントロールパネルにログイン
2. サーバー管理 → SSH Key
3. 公開鍵を登録
4. サーバー作成時に選択

## SSH鍵認証のテスト

⚠️ **重要**: 既存のSSHセッションは閉じずに、新しいターミナルでテスト

### 新しいターミナルで接続テスト

```bash
ssh root@<VPS_IP>
```

**成功した場合:**
- パスワードを聞かれずにログイン
- パスフレーズを設定した場合はパスフレーズを入力

**失敗した場合:**
- パスワードを聞かれる
- トラブルシューティングセクションを参照

## SSH設定の強化

鍵認証が動作確認できたら、パスワード認証を無効化:

### VPS側の設定 (/etc/ssh/sshd_config)

```bash
sudo nano /etc/ssh/sshd_config
```

以下の設定を変更:

```conf
# Root ログイン無効化
PermitRootLogin no

# パスワード認証無効化
PasswordAuthentication no

# 公開鍵認証有効化
PubkeyAuthentication yes

# チャレンジレスポンス認証無効化
ChallengeResponseAuthentication no

# 認証試行回数制限
MaxAuthTries 3

# 空パスワード禁止
PermitEmptyPasswords no

# X11フォワーディング無効化（不要な場合）
X11Forwarding no

# ログイン猶予時間
LoginGraceTime 60
```

### 設定の反映

```bash
# 設定ファイルの構文チェック
sudo sshd -t

# 問題なければ再起動
sudo systemctl restart sshd
```

⚠️ **注意**: 再起動前に必ず新しいターミナルで鍵認証をテストしてください。

## ローカルマシンのSSH設定（オプション）

接続を簡単にするため、`~/.ssh/config` に設定:

```bash
# ~/.ssh/config
Host myvps
    HostName <VPS_IP>
    User root
    IdentityFile ~/.ssh/id_ed25519
    Port 22
```

これで以下のように簡単に接続:
```bash
ssh myvps
```

## セキュリティベストプラクティス

### 秘密鍵の保護

```bash
# 秘密鍵のパーミッション確認
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub

# .sshディレクトリのパーミッション
chmod 700 ~/.ssh
```

### 複数デバイスでの管理

**推奨方法:**
- デバイスごとに異なる鍵ペアを生成
- VPSの `authorized_keys` に全ての公開鍵を登録

```bash
# VPSで複数の公開鍵を登録
cat >> ~/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAAC3... laptop@example.com
ssh-ed25519 AAAAC3... desktop@example.com
ssh-ed25519 AAAAC3... tablet@example.com
EOF

chmod 600 ~/.ssh/authorized_keys
```

### ssh-agentの使用（パスフレーズ保護時）

パスフレーズを毎回入力したくない場合:

```bash
# ssh-agent起動
eval "$(ssh-agent -s)"

# 秘密鍵を追加
ssh-add ~/.ssh/id_ed25519

# 登録された鍵を確認
ssh-add -l
```

## トラブルシューティング

### 鍵認証が機能しない

#### デバッグモードで接続

```bash
ssh -v root@<VPS_IP>
# または、より詳細に
ssh -vvv root@<VPS_IP>
```

#### VPS側のログ確認

```bash
# VPSで実行
sudo tail -f /var/log/auth.log
```

よくあるエラー:

**"Permission denied (publickey)"**
- 公開鍵が正しく登録されていない
- パーミッションが間違っている
- sshd_configで `PubkeyAuthentication no` になっている

**パーミッション修正:**
```bash
# VPSで実行
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chown -R $USER:$USER ~/.ssh
```

### authorized_keys が読み込まれない

SELinuxが有効な場合:
```bash
# VPSで実行
restorecon -R -v ~/.ssh
```

### ポート変更後に接続できない

```bash
# ポート22以外の場合
ssh -p 2222 root@<VPS_IP>

# ~/.ssh/config に設定
Host myvps
    Port 2222
```

### 鍵を紛失した場合

**対処法:**
1. ConoHaコントロールパネルからコンソールにアクセス
2. パスワード認証を一時的に有効化
3. 新しい鍵ペアを生成して登録
4. パスワード認証を再度無効化

```bash
# VPSで一時的にパスワード認証を有効化
sudo nano /etc/ssh/sshd_config
# PasswordAuthentication yes に変更
sudo systemctl restart sshd
```

## 高度な設定

### ポート転送（Port Forwarding）

```bash
# ローカル→リモート
ssh -L 8080:localhost:80 root@<VPS_IP>

# リモート→ローカル
ssh -R 8080:localhost:3000 root@<VPS_IP>
```

### SSH踏み台（Bastion Host）

```bash
# ~/.ssh/config
Host bastion
    HostName <BASTION_IP>
    User admin
    IdentityFile ~/.ssh/bastion_key

Host internal-server
    HostName <INTERNAL_IP>
    User admin
    IdentityFile ~/.ssh/internal_key
    ProxyJump bastion
```

### 2要素認証（2FA）の追加

Google Authenticatorを使用:

```bash
# VPSにインストール
sudo apt install libpam-google-authenticator -y

# セットアップ
google-authenticator
```

## セキュリティチェックリスト

- [ ] SSH鍵ペアを生成（ED25519推奨）
- [ ] パスフレーズを設定（推奨）
- [ ] 公開鍵をVPSに登録
- [ ] 秘密鍵のパーミッション: 600
- [ ] 鍵認証の動作確認
- [ ] パスワード認証を無効化
- [ ] Root ログインを無効化
- [ ] デフォルトポート変更（オプション）
- [ ] Fail2ban設定
- [ ] 定期的なログ確認

## 参考リンク

- [OpenSSH公式ドキュメント](https://www.openssh.com/manual.html)
- [SSH.com - SSH Keys](https://www.ssh.com/academy/ssh/key)
- [GitHub - SSH設定](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

---

**次のステップ**: [QUICKSTART_SECURITY.md](../QUICKSTART_SECURITY.md) でVPSのセキュアな設定を完了させましょう。
