function Get-ArtCodexArguments([switch]$StandardPermissions, [string]$Model) {
    $arguments = @('--no-daemon', '--cd', $Lab)
    if (!$StandardPermissions) {
        # Owner-requested full access, scoped to this launched process.
        $arguments += @('--sandbox', 'danger-full-access', '--ask-for-approval', 'never')
    }
    if ($Model) { $arguments += @('--model', $Model) }
    return $arguments
}
