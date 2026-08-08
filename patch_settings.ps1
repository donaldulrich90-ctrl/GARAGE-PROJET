# Patch idempotent de settings.py.
# Ajoute les changements semantiques sans polluer les fins de ligne.
$ErrorActionPreference = 'Stop'

$path = Join-Path $PSScriptRoot 'garage_saas\settings.py'
if (-not (Test-Path $path)) {
    Write-Error "settings.py introuvable a l'emplacement: $path"
    exit 1
}

# Lecture en preservant l'encodage exact.
$bytes = [System.IO.File]::ReadAllBytes($path)
$hasBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
$content = [System.Text.Encoding]::UTF8.GetString($bytes)
if ($hasBom) { $content = $content.Substring(1) }

$modified = $false

# 1) Ajouter 'catalog' juste avant 'clients' dans INSTALLED_APPS.
if ($content -notmatch "'catalog',") {
    $before = $content
    $content = [regex]::Replace(
        $content,
        "(?m)^(?<pfx>    'billing',\r?\n)(?<line>    'clients',)",
        { param($m) $m.Groups['pfx'].Value + "    'catalog'," + [regex]::Match($m.Groups['pfx'].Value,'\r?\n').Value + $m.Groups['line'].Value }
    )
    if ($content -ne $before) { $modified = $true; Write-Host "  + 'catalog' ajoute a INSTALLED_APPS" }
}

# 2) Ajouter 'supplier_portal' en fin de INSTALLED_APPS.
if ($content -notmatch "'supplier_portal',") {
    $before = $content
    $content = [regex]::Replace(
        $content,
        "(?m)^(?<pfx>    'taxes',\r?\n)(?<close>\])",
        { param($m) $m.Groups['pfx'].Value + "    'supplier_portal'," + [regex]::Match($m.Groups['pfx'].Value,'\r?\n').Value + $m.Groups['close'].Value }
    )
    if ($content -ne $before) { $modified = $true; Write-Host "  + 'supplier_portal' ajoute a INSTALLED_APPS" }
}

# 3) Rediriger le login vers la vue dispatcher par role.
$new = $content -replace "LOGIN_REDIRECT_URL\s*=\s*'dashboard_home'", "LOGIN_REDIRECT_URL = 'post_login_redirect'"
if ($new -ne $content) { $content = $new; $modified = $true; Write-Host "  + LOGIN_REDIRECT_URL bascule vers post_login_redirect" }

# 4) Bloc PLATFORM_COMMISSION_RATE avant la section WhatsApp.
if ($content -notmatch 'PLATFORM_COMMISSION_RATE') {
    $eol = "`r`n"
    if ($content -notmatch "`r`n") { $eol = "`n" }
    $block = "# --- Commission plateforme ---$eol" +
             "# Taux de commission par defaut preleve sur chaque commande fournisseur validee.$eol" +
             "# Override possible par fournisseur (Supplier.commission_rate).$eol" +
             "PLATFORM_COMMISSION_RATE = os.environ.get('PLATFORM_COMMISSION_RATE', '5.00')$eol$eol"

    $before = $content
    $content = [regex]::Replace(
        $content,
        '(?m)^(#[^\r\n]*WhatsApp Business Cloud API[^\r\n]*)',
        { param($m) $block + $m.Value }
    )
    if ($content -ne $before) {
        $modified = $true
        Write-Host "  + Bloc PLATFORM_COMMISSION_RATE insere avant la section WhatsApp"
    } else {
        $content = $content.TrimEnd() + $eol + $eol + $block.TrimEnd() + $eol
        $modified = $true
        Write-Host "  + Bloc PLATFORM_COMMISSION_RATE ajoute a la fin (fallback)"
    }
}

if (-not $modified) {
    Write-Host "settings.py deja a jour, aucun changement applique."
    exit 0
}

# Ecriture en preservant l'encodage d'origine.
if ($hasBom) {
    $enc = New-Object System.Text.UTF8Encoding($true)
} else {
    $enc = New-Object System.Text.UTF8Encoding($false)
}
[System.IO.File]::WriteAllText($path, $content, $enc)
Write-Host "settings.py patche avec succes."
