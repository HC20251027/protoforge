use std::process::Child;
use std::sync::Mutex;
use std::time::Duration;

use log::{error, info, warn};

/// Python sidecar 监听端口
const SIDECAR_PORT: u16 = 7655;
/// health 轮询间隔(毫秒)
const HEALTH_POLL_MS: u64 = 500;
/// health 超时时间(秒)
const HEALTH_TIMEOUT_S: u64 = 30;

/// Python sidecar 进程管理器。
///
/// 使用 `Mutex<Option<Child>>` 实现 `Send + Sync`,
/// 以便通过 Tauri 的 `manage()` 注册为全局状态。
pub struct Sidecar {
    child: Mutex<Option<Child>>,
}

impl Sidecar {
    /// 启动 Python uvicorn 进程,监听 `SIDECAR_PORT`。
    pub fn spawn() -> anyhow::Result<Self> {
        info!("Spawning Python sidecar on port {} ...", SIDECAR_PORT);

        let python =
            std::env::var("PROTOFORGE_PYTHON").unwrap_or_else(|_| "python".to_string());

        let port_str = SIDECAR_PORT.to_string();

        let child = std::process::Command::new(&python)
            .args([
                "-m",
                "uvicorn",
                "app.main:app",
                "--port",
                &port_str,
                "--log-level",
                "warning",
            ])
            .current_dir(Self::api_dir()?)
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()
            .map_err(|e| anyhow::anyhow!("Failed to spawn Python sidecar: {e}"))?;

        info!("Python process started (pid: {:?})", child.id());

        Ok(Self {
            child: Mutex::new(Some(child)),
        })
    }

    /// 轮询 `/health` 端点,直到成功或超时(30 秒)。
    pub async fn wait_for_health(&self) -> anyhow::Result<()> {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(2))
            .build()?;

        let url = format!("http://127.0.0.1:{}/health", SIDECAR_PORT);
        let start = std::time::Instant::now();

        loop {
            match client.get(&url).send().await {
                Ok(resp) if resp.status().is_success() => {
                    info!(
                        "Sidecar health OK (waited {}ms)",
                        start.elapsed().as_millis()
                    );
                    return Ok(());
                }
                Ok(resp) => {
                    warn!("Health returned {}: waiting ...", resp.status());
                }
                Err(e) => {
                    warn!("Health poll error: {} — waiting ...", e);
                }
            }

            if start.elapsed() > Duration::from_secs(HEALTH_TIMEOUT_S) {
                error!("Sidecar health timeout after {}s", HEALTH_TIMEOUT_S);
                anyhow::bail!(
                    "Sidecar did not become healthy within {}s",
                    HEALTH_TIMEOUT_S
                );
            }

            tokio::time::sleep(Duration::from_millis(HEALTH_POLL_MS)).await;
        }
    }

    /// 从 exe 路径往上查找 `apps/api` 目录。
    ///
    /// dev 模式下 exe 位于
    /// `apps/desktop/src-tauri/target/debug/xxx.exe`,
    /// 往上 5 级即可到达项目根目录。
    fn api_dir() -> anyhow::Result<std::path::PathBuf> {
        let exe = std::env::current_exe()?;
        let mut dir = exe.parent().unwrap().to_path_buf();

        for _ in 0..5 {
            if dir.join("apps").join("api").join("app").exists() {
                return Ok(dir.join("apps").join("api"));
            }
            match dir.parent() {
                Some(p) => dir = p.to_path_buf(),
                None => break,
            }
        }

        // 兜底:从当前工作目录查找
        let cwd = std::env::current_dir()?;
        if cwd.join("apps").join("api").exists() {
            return Ok(cwd.join("apps").join("api"));
        }

        anyhow::bail!("Cannot locate apps/api directory")
    }

    /// 终止 Python sidecar 进程。
    pub fn kill(&mut self) {
        if let Ok(mut guard) = self.child.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
                let _ = child.wait();
                info!("Sidecar process killed");
            }
        }
    }
}

impl Drop for Sidecar {
    fn drop(&mut self) {
        self.kill();
    }
}
