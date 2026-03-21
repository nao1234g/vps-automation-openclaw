#!/usr/bin/env python3
"""
Google Search Console 認証セットアップスクリプト
実行方法: python3 gsc_auth_setup.py
1回だけ実行。refresh_token を /opt/shared/gsc_token.json に保存する。

必要な前提:
  方式A (推奨): Service Account
    - /opt/shared/gsc_service_account.json を配置する
  方式B: OAuth2 (Desktop app)
    - /opt/shared/gsc_client_secrets.json を配置する
"""

import json, os, sys

SECRETS_FILE = "/opt/shared/gsc_client_secrets.json"
SERVICE_ACCOUNT_FILE = "/opt/shared/gsc_service_account.json"
TOKEN_FILE = "/opt/shared/gsc_token.json"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def try_service_account():
    """Service Account 方式を試す"""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("searchconsole", "v1", credentials=creds)
        result = service.sites().list().execute()
        sites = [s["siteUrl"] for s in result.get("siteEntry", [])]
        print("Service Account 認証成功!")
        print(f"アクセス可能なサイト: {sites}")
        return True
    except Exception as e:
        print(f"Service Account 失敗: {e}")
        return False


def oauth2_flow():
    """OAuth2 フロー (ヘッドレスサーバー対応)"""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("pip3 install google-auth-oauthlib を実行してください")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    print()
    print("=" * 70)
    print("以下のURLをブラウザで開いてGoogleアカウントで認証してください:")
    print()
    print(auth_url)
    print()
    print("=" * 70)
    print("認証後に表示される「認証コード」を入力してください:")

    code = input("認証コード: ").strip()
    flow.fetch_token(code=code)
    creds = flow.credentials

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "auth_method": "oauth2"
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"認証完了! トークンを {TOKEN_FILE} に保存しました。")
    print("今後は gsc_intelligence.py が自動実行されます。")


def main():
    print("=== Google Search Console 認証セットアップ ===")
    print()

    # Service Account を優先
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        print("Service Account ファイルを検出。テスト中...")
        if try_service_account():
            print()
            print("セットアップ完了。gsc_intelligence.py を実行できます。")
            return
        print("OAuth2 方式に切り替えます...")

    # OAuth2 フォールバック
    if not os.path.exists(SECRETS_FILE):
        print(f"ERROR: 認証ファイルが見つかりません。")
        print()
        print("【セットアップ手順 — Service Account (推奨)】")
        print("1. Google Cloud Console (https://console.cloud.google.com/) を開く")
        print("2. APIとサービス → ライブラリ → 'Google Search Console API' を有効化")
        print("3. APIとサービス → 認証情報 → サービスアカウントを作成")
        print("4. キーを作成 (JSON) → ダウンロード")
        print("5. キーファイルを /opt/shared/gsc_service_account.json として VPS に配置")
        print("6. Google Search Console → 設定 → ユーザーと権限 → サービスアカウントのメールを追加")
        print()
        print("【セットアップ手順 — OAuth2 (代替)】")
        print("1. Google Cloud Console → 認証情報 → OAuth 2.0 クライアントID")
        print("2. アプリケーションの種類: デスクトップアプリ")
        print("3. ダウンロードした JSON を /opt/shared/gsc_client_secrets.json として配置")
        print("4. 再度このスクリプトを実行")
        sys.exit(1)

    oauth2_flow()


if __name__ == "__main__":
    main()
