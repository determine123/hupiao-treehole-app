# User-entered authorization is encrypted with Windows DPAPI, outside the repository.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$dialog = New-Object System.Windows.Forms.Form
$dialog.Text = '沪漂树洞 · Render 本机部署授权'
$dialog.Size = New-Object System.Drawing.Size(600, 360)
$dialog.StartPosition = 'CenterScreen'
$dialog.FormBorderStyle = 'FixedDialog'
$dialog.MaximizeBox = $false
$info = New-Object System.Windows.Forms.Label
$info.Text = "在 Render 的 Account Settings > API Keys 创建部署令牌。`r`n仅在下面填写，令牌不会发送到聊天；使用 Windows DPAPI 加密保存。`r`n本次只创建免费内测资源，数据库有效期 30 天。"
$info.Location = New-Object System.Drawing.Point(20, 20)
$info.Size = New-Object System.Drawing.Size(550, 75)
$dialog.Controls.Add($info)
$label = New-Object System.Windows.Forms.Label
$label.Text = 'Render API Key（不需要账户密码）'
$label.Location = New-Object System.Drawing.Point(20, 100)
$label.Size = New-Object System.Drawing.Size(500, 22)
$dialog.Controls.Add($label)
$token = New-Object System.Windows.Forms.TextBox
$token.UseSystemPasswordChar = $true
$token.Location = New-Object System.Drawing.Point(20, 125)
$token.Size = New-Object System.Drawing.Size(540, 26)
$dialog.Controls.Add($token)
$emailLabel = New-Object System.Windows.Forms.Label
$emailLabel.Text = '应用公开客服 / 举报邮箱（将向用户展示）'
$emailLabel.Location = New-Object System.Drawing.Point(20, 165)
$emailLabel.Size = New-Object System.Drawing.Size(500, 22)
$dialog.Controls.Add($emailLabel)
$email = New-Object System.Windows.Forms.TextBox
$email.Location = New-Object System.Drawing.Point(20, 190)
$email.Size = New-Object System.Drawing.Size(540, 26)
$dialog.Controls.Add($email)
$save = New-Object System.Windows.Forms.Button
$save.Text = '保存本机授权'
$save.Location = New-Object System.Drawing.Point(365, 245)
$save.Size = New-Object System.Drawing.Size(195, 38)
$save.Add_Click({
    try {
        if ($token.Text.Trim().Length -lt 20) { throw '请填写完整 Render API Key。' }
        $mail = New-Object System.Net.Mail.MailAddress($email.Text.Trim())
        if ($mail.Address -ne $email.Text.Trim() -or $mail.Address -match 'example|\.invalid$') { throw '请填写真实公开邮箱。' }
        $privateDirectory = Join-Path $env:USERPROFILE '.codex/private/hupiao'
        New-Item -ItemType Directory -Force -Path $privateDirectory | Out-Null
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $acl = New-Object System.Security.AccessControl.DirectorySecurity
        $acl.SetAccessRuleProtection($true, $false)
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
        $acl.SetAccessRule($rule)
        Set-Acl -LiteralPath $privateDirectory -AclObject $acl
        $protected = ConvertTo-SecureString $token.Text.Trim() -AsPlainText -Force | ConvertFrom-SecureString
        @{renderTokenEncrypted=$protected;supportEmail=$mail.Address} | ConvertTo-Json | Set-Content (Join-Path $privateDirectory 'render-auth.json') -Encoding UTF8
        $token.Clear()
        [System.Windows.Forms.MessageBox]::Show('已加密保存。请回到 Codex 回复“授权已保存”。','保存完成') | Out-Null
        $dialog.Close()
    } catch {
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'请检查填写内容') | Out-Null
    }
})
$dialog.Controls.Add($save)
$dialog.AcceptButton = $save
[void]$dialog.ShowDialog()
