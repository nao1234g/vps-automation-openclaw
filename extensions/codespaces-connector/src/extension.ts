import * as vscode from 'vscode';
import { Octokit } from '@octokit/rest';

interface CodespaceInfo {
    name: string;
    id: number;
    state: string;
    repository: {
        full_name: string;
    };
    machine: {
        name: string;
        display_name: string;
        operating_system: string;
        storage_in_bytes: number;
        memory_in_bytes: number;
        cpus: number;
    } | null;
}

export function activate(context: vscode.ExtensionContext) {
    console.log('GitHub Codespaces Connector is now active');

    const outputChannel = vscode.window.createOutputChannel('Codespaces Connector');
    let statusBarItem: vscode.StatusBarItem;

    const disposable = vscode.commands.registerCommand('codespacesConnector.connect', async () => {
        outputChannel.show();
        outputChannel.appendLine('=== GitHub Codespaces Connector ===');
        outputChannel.appendLine(`Started at: ${new Date().toISOString()}`);

        try {
            // ステップ1: GitHub Codespaces拡張機能のチェック
            outputChannel.appendLine('\n[1/9] Checking GitHub Codespaces extension...');
            const codespacesExt = vscode.extensions.getExtension('GitHub.codespaces');
            
            if (!codespacesExt) {
                outputChannel.appendLine('⚠️  GitHub Codespaces extension not found');
                const choice = await vscode.window.showWarningMessage(
                    'GitHub Codespaces extension is not installed. Would you like to install it?',
                    'Install',
                    'Cancel'
                );
                
                if (choice === 'Install') {
                    outputChannel.appendLine('Opening extension marketplace...');
                    await vscode.commands.executeCommand('workbench.extensions.search', '@id:GitHub.codespaces');
                    return;
                } else {
                    outputChannel.appendLine('❌ Installation cancelled by user');
                    return;
                }
            }
            
            outputChannel.appendLine('✅ GitHub Codespaces extension is installed');

            // ステップ2: 拡張機能のアクティベーション確認
            if (!codespacesExt.isActive) {
                outputChannel.appendLine('[2/9] Activating GitHub Codespaces extension...');
                await codespacesExt.activate();
                outputChannel.appendLine('✅ Extension activated');
            } else {
                outputChannel.appendLine('[2/9] ✅ Extension already active');
            }

            // ステータスバーアイテムの作成
            if (!statusBarItem) {
                statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
                context.subscriptions.push(statusBarItem);
            }
            statusBarItem.text = '$(sync~spin) Connecting to Codespaces...';
            statusBarItem.show();

            // ステップ3: GitHub認証チェック
            outputChannel.appendLine('[3/9] Checking GitHub authentication...');
            
            let session: vscode.AuthenticationSession | undefined;
            try {
                session = await vscode.authentication.getSession('github', ['codespace'], { createIfNone: false });
            } catch (error) {
                outputChannel.appendLine(`⚠️  Authentication check failed: ${error}`);
            }

            if (!session) {
                outputChannel.appendLine('⚠️  Not authenticated with GitHub');
                const authChoice = await vscode.window.showInformationMessage(
                    'GitHub authentication is required to connect to Codespaces.',
                    'Sign in',
                    'Cancel'
                );
                
                if (authChoice === 'Sign in') {
                    outputChannel.appendLine('[4/9] Starting GitHub authentication flow...');
                    try {
                        session = await vscode.authentication.getSession('github', ['codespace'], { createIfNone: true });
                        outputChannel.appendLine('✅ Authentication successful');
                    } catch (error) {
                        outputChannel.appendLine(`❌ Authentication failed: ${error}`);
                        statusBarItem.text = '$(error) Auth Failed';
                        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                        setTimeout(() => statusBarItem.hide(), 5000);
                        return;
                    }
                } else {
                    outputChannel.appendLine('❌ Authentication cancelled by user');
                    statusBarItem.hide();
                    return;
                }
            } else {
                outputChannel.appendLine('[3/9] ✅ Already authenticated with GitHub');
                outputChannel.appendLine(`    Account: ${session.account.label}`);
            }

            // ステップ5: Codespacesリストの取得
            outputChannel.appendLine('[5/9] Fetching available Codespaces...');
            statusBarItem.text = '$(sync~spin) Fetching Codespaces...';

            let codespaces: CodespaceInfo[] = [];
            try {
                const octokit = new Octokit({
                    auth: session!.accessToken
                });

                const response = await octokit.request('GET /user/codespaces');
                codespaces = response.data.codespaces;
                outputChannel.appendLine(`✅ Found ${codespaces.length} Codespace(s)`);
                
                codespaces.forEach((cs, idx) => {
                    outputChannel.appendLine(`    ${idx + 1}. ${cs.name} (${cs.state}) - ${cs.repository.full_name}`);
                });
            } catch (error) {
                outputChannel.appendLine(`❌ Failed to fetch Codespaces: ${error}`);
                vscode.window.showErrorMessage(`Failed to fetch Codespaces: ${error}`);
                statusBarItem.text = '$(error) Fetch Failed';
                statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                setTimeout(() => statusBarItem.hide(), 5000);
                return;
            }

            if (codespaces.length === 0) {
                outputChannel.appendLine('❌ No Codespaces found');
                const createChoice = await vscode.window.showInformationMessage(
                    'No Codespaces found. Would you like to create one?',
                    'Create',
                    'Cancel'
                );
                
                if (createChoice === 'Create') {
                    outputChannel.appendLine('Opening Codespaces creation...');
                    await vscode.commands.executeCommand('github.codespaces.createCodespace');
                }
                statusBarItem.hide();
                return;
            }

            // ステップ6: Codespaceの選択
            outputChannel.appendLine('[6/9] Prompting user to select a Codespace...');
            
            const quickPickItems = codespaces.map(cs => ({
                label: cs.name,
                description: `${cs.state} | ${cs.machine?.display_name || 'Unknown machine'}`,
                detail: cs.repository.full_name,
                codespace: cs
            }));

            const selectedItem = await vscode.window.showQuickPick(quickPickItems, {
                placeHolder: 'Select a Codespace to connect',
                ignoreFocusOut: true
            });

            if (!selectedItem) {
                outputChannel.appendLine('❌ No Codespace selected');
                statusBarItem.hide();
                return;
            }

            outputChannel.appendLine(`✅ Selected: ${selectedItem.label}`);

            // ステップ7: Codespaceへの接続
            outputChannel.appendLine('[7/9] Connecting to Codespace...');
            statusBarItem.text = `$(sync~spin) Connecting to ${selectedItem.label}...`;

            try {
                // GitHub Codespaces拡張のコマンドを実行
                await vscode.commands.executeCommand('github.codespaces.connectToCodespace', {
                    codespace: selectedItem.codespace
                });
                
                outputChannel.appendLine('✅ Connection command executed');
            } catch (error) {
                outputChannel.appendLine(`❌ Connection failed: ${error}`);
                vscode.window.showErrorMessage(`Failed to connect to Codespace: ${error}`);
                statusBarItem.text = '$(error) Connection Failed';
                statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                setTimeout(() => statusBarItem.hide(), 5000);
                return;
            }

            // ステップ8: 接続完了の待機
            outputChannel.appendLine('[8/9] Waiting for connection to complete...');
            await new Promise(resolve => setTimeout(resolve, 3000));

            // ステップ9: 接続状態の確認
            outputChannel.appendLine('[9/9] Verifying connection status...');
            
            // 環境変数をチェック
            const codespaceName = process.env.CODESPACE_NAME;
            if (codespaceName) {
                outputChannel.appendLine(`✅ Connected to Codespace: ${codespaceName}`);
                statusBarItem.text = `$(check) Connected: ${codespaceName}`;
                statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.prominentBackground');
                
                vscode.window.showInformationMessage(
                    `Successfully connected to Codespace: ${codespaceName}`
                );
            } else {
                outputChannel.appendLine('⚠️  Connection status unclear (may still be connecting)');
                statusBarItem.text = `$(info) Connecting...`;
                vscode.window.showInformationMessage(
                    'Connection initiated. Please wait for the window to reload.'
                );
            }

            outputChannel.appendLine('\n=== Connection process completed ===');
            outputChannel.appendLine(`Finished at: ${new Date().toISOString()}`);

            // 5秒後にステータスバーを非表示
            setTimeout(() => {
                if (statusBarItem) {
                    statusBarItem.hide();
                }
            }, 5000);

        } catch (error) {
            outputChannel.appendLine(`\n❌ Unexpected error: ${error}`);
            if (error instanceof Error) {
                outputChannel.appendLine(`   Stack: ${error.stack}`);
            }
            vscode.window.showErrorMessage(`Codespaces Connector Error: ${error}`);
            
            if (statusBarItem) {
                statusBarItem.text = '$(error) Error';
                statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                setTimeout(() => statusBarItem.hide(), 5000);
            }
        }
    });

    context.subscriptions.push(disposable);
}

export function deactivate() {
    console.log('GitHub Codespaces Connector is now deactivated');
}
