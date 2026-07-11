@echo off
REM Configure main branch protection via GitHub API (Windows batch wrapper for curl)
REM Usage: set_branch_protection.cmd
if "%GH_TOKEN%"=="" (
  echo ERROR: GH_TOKEN env required 1>&2
  exit /b 1
)
curl.exe -s -X PUT ^
  -H "Authorization: token %GH_TOKEN%" ^
  -H "Accept: application/vnd.github+json" ^
  -H "Content-Type: application/json" ^
  -H "User-Agent: TRAE-CLI" ^
  -d "{\"required_status_checks\":null,\"enforce_admins\":false,\"required_pull_request_reviews\":null,\"restrictions\":null,\"required_linear_history\":true,\"allow_force_pushes\":false,\"allow_deletions\":false,\"block_creations\":false,\"required_conversation_resolution\":false}" ^
  https://api.github.com/repos/HC20251027/protoforge/branches/main/protection
