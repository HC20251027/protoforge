use serde::{Deserialize, Serialize};

/// 系统信息(返回给前端)
#[derive(Serialize, Deserialize, Clone)]
pub struct SystemInfo {
    /// Python 解释器路径
    pub python: String,
    /// 操作系统
    pub platform: String,
    /// CPU 架构
    pub arch: String,
}

/// 返回当前系统信息:Python 路径、平台、架构。
#[tauri::command]
pub fn system_info() -> Result<SystemInfo, String> {
    Ok(SystemInfo {
        python: std::env::var("PROTOFORGE_PYTHON").unwrap_or_else(|_| "python".to_string()),
        platform: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
    })
}

/// 异步请求 sidecar 的 `/health` 端点。
#[tauri::command]
pub async fn health_check() -> Result<serde_json::Value, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(3))
        .build()
        .map_err(|e| e.to_string())?;

    let url = "http://127.0.0.1:7655/health";
    client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Sidecar unreachable: {}", e))?
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Parse error: {}", e))
}
