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

// =====================================================================
// Phase 3 Task 1.4 — Tauri sidecar (externalBin) launcher
// ---------------------------------------------------------------------
// The Tauri-side launcher uses ``tauri_plugin_shell::Command::new_sidecar``,
// which resolves the ``binaries/python-bundle/python`` entry declared in
// ``tauri.conf.json`` -> ``bundle.externalBin``.
//
// In dev mode (no bundle), Tauri searches the project's ``binaries/``
// directory at runtime; in production it picks the platform-specific
// binary from the install / game directory.  See the helper
// ``sidecar_binary_path`` for the on-disk layout this function expects.
// =====================================================================

/// 平台无关的 Tauri externalBin 名称,必须与
/// ``tauri.conf.json`` -> ``bundle.externalBin[0]`` 一致。
pub const SIDECAR_BIN_NAME: &str = "python";

/// 启动 sidecar 时传给 Python 的 API 端口。
///
/// Phase 3 Task 6 P0-C1:历史上 sidecar 默认 7655(避免 dev 期 API 进程冲突),
/// 但**生产**场景里后端配置 (`apps/api/app/config.py`) 默认端口是 7654。
/// 两边不一致 → Tauri 启动 Python 后,WebView 调 `fetch('/api/...')` 的
/// 转发目标会指错端口(取决于 Vite dev proxy / Tauri shell 哪个配错)。
///
/// 修复:让 sidecar 启动端口**优先**从 `PROTOFORGE_API_PORT` 读
/// (跟后端 `Settings.port` 的 env prefix `PROTOFORGE_` 对齐),然后
/// 才回退到 `PROTOFORGE_SIDECAR_PORT` 兼容历史 dev 配置,最后兜底
/// `SIDECAR_API_PORT_DEFAULT = 7655`。
pub const SIDECAR_API_PORT_DEFAULT: u16 = 7655;

/// 计算 sidecar 解释器在当前 platform 上的**磁盘路径**(用于调试 /
/// 诊断,真正 spawn 走 ``tauri_plugin_shell::Command::new_sidecar``)。
///
/// 解析规则与 ``tauri.conf.json`` 中 ``bundle.externalBin = "binaries/python-bundle/python"``
/// 的 Tauri 官方约定一致:
///
///   - Windows:  ``binaries/python-bundle/python.exe``
///   - macOS:    ``binaries/python-bundle/python``
///   - Linux:    ``binaries/python-bundle/bin/python``  (``bin/`` 来自 PEP 394)
///
/// 这是一个**纯函数**:不读文件系统,不依赖 cwd。返回的路径是相对
/// 于 sidecar 所在目录(bundle 根或开发期 project root)。
pub fn sidecar_binary_path() -> &'static str {
    if cfg!(target_os = "windows") {
        "binaries/python-bundle/python.exe"
    } else if cfg!(target_os = "macos") {
        "binaries/python-bundle/python"
    } else {
        // Linux + 其它 unix
        "binaries/python-bundle/bin/python"
    }
}

/// 计算玩家在游戏目录里期望看到 sidecar 解释器的路径(仅用于
/// 日志 / 玩家排错消息,不会用来 spawn)。
pub fn sidecar_runtime_path() -> String {
    format!("<game-dir>/{}", sidecar_binary_path())
}

/// 解析 sidecar 实际监听端口。
///
/// **Phase 3 Task 6 P0-C1**:优先读 `PROTOFORGE_API_PORT`(对齐
/// 后端 `Settings.port` 的 env prefix),再读 `PROTOFORGE_SIDECAR_PORT`
/// 兼容历史 dev 配置,最后兜底 7655。这样 Tauri 启动 Python 时
/// 用的端口永远 = 后端读到的端口,不会因为 sidecar 默认 7655 而
/// 撞上"打包后连不上后端"的问题。
pub fn sidecar_port() -> u16 {
    // 1) 优先 PROTOFORGE_API_PORT — 跟后端 Settings 的 env prefix 对齐
    if let Ok(p) = std::env::var("PROTOFORGE_API_PORT") {
        if let Ok(parsed) = p.parse::<u16>() {
            return parsed;
        }
    }
    // 2) 回退 PROTOFORGE_SIDECAR_PORT — 历史 dev 习惯
    if let Ok(p) = std::env::var("PROTOFORGE_SIDECAR_PORT") {
        if let Ok(parsed) = p.parse::<u16>() {
            return parsed;
        }
    }
    // 3) 兜底默认
    SIDECAR_API_PORT_DEFAULT
}

/// Tauri 启动 Python sidecar 的统一入口。
///
/// 调用 ``tauri_plugin_shell::Command::new_sidecar("python")`` 启动
/// ``uvicorn app.main:app --port <port> --host 127.0.0.1`` 并返回
/// 进程句柄,后续可在 setup() 闭包内通过 ``app.manage(child)`` 让
/// 整个 app 生命周期持有它,或者配合 Tauri 2.x 的
/// ``on_window_event`` 在退出时 ``kill()``。
///
/// # 路径解析说明
///
/// ``Command::new_sidecar`` 内部遵循 Tauri 规范:
/// 1. dev 模式 (``tauri dev``): 在 ``src-tauri/binaries/`` 目录里
///    查找与 ``externalBin`` 同名(去掉扩展名)的可执行文件。
/// 2. production 模式 (``tauri build``): 在安装/打包根目录里
///    查找同名可执行文件,平台扩展名由 Tauri 自动追加。
///
/// 因此**不需要**在这里手动拼路径 — 写 ``"python"`` 就够了。
/// ``sidecar_binary_path()`` 仅用于日志和单元测试断言。
///
/// # 参数
///
/// - ``app``: Tauri ``AppHandle``,用来构造 shell command scope。
///
/// # 返回
///
/// - ``Ok(CommandChild)`` — 启动成功,玩家进程已绑定到本 AppHandle。
/// - ``Err(tauri::Error)`` — 启动失败(binary not found, permission,
///   等)。调用方应让 setup() 闭包 ``Err`` 出去,触发 Tauri 启动失败
///   而不是带着半残的 UI 进游戏。
pub fn launch_python_sidecar(
    app: tauri::AppHandle,
) -> Result<tauri_plugin_shell::process::CommandChild, tauri::Error> {
    let port = sidecar_port().to_string();
    let host = "127.0.0.1".to_string();

    log::info!(
        "Launching Tauri Python sidecar (binary={:?}, port={})",
        sidecar_binary_path(),
        port
    );

    // tauri-plugin-shell v2 的 spawn() 返回
    // `Result<(Receiver<CommandEvent>, CommandChild), Error>`,
    // 需解构出 CommandChild 并转换错误类型为 tauri::Error。
    let (_event_rx, child) = tauri_plugin_shell::ShellExt::shell(&app)
        .command(SIDECAR_BIN_NAME)
        .args([
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            port.as_str(),
            "--host",
            host.as_str(),
        ])
        // Phase 3 Task 6 P0-C1:把解析出来的端口作为 PROTOFORGE_API_PORT
        // 注入 sidecar 环境,这样后端 uvicorn 如果读了它(比如新加的兜底
        // 启动脚本),就能保证 listen 在同一个端口上,跟 Tauri 的转发目标对齐。
        .env("PROTOFORGE_API_PORT", port.as_str())
        .current_dir(sidecar_cwd())
        .spawn()
        .map_err(|e| {
            log::error!("Failed to spawn Tauri Python sidecar: {e}");
            tauri::Error::Anyhow(anyhow::Error::new(e))
        })?;
    Ok(child)
}

/// 计算 sidecar 进程的 ``current_dir``(它要在 ``apps/api`` 下面跑,
/// 才能 ``import app.main:app``)。
///
/// 解析顺序:
/// 1. ``PROTOFORGE_API_DIR`` 环境变量(发布版用绝对路径)
/// 2. exe 路径向上 5 级 = 项目根,然后 ``apps/api``(dev 模式)
/// 3. cwd 向上找 ``apps/api``
/// 4. 兜底:就返回 ``.``(让 Tauri 自己报错)
fn sidecar_cwd() -> std::path::PathBuf {
    if let Ok(dir) = std::env::var("PROTOFORGE_API_DIR") {
        return std::path::PathBuf::from(dir);
    }

    if let Ok(exe) = std::env::current_exe() {
        let mut dir = exe.parent().map(|p| p.to_path_buf()).unwrap_or_default();
        for _ in 0..5 {
            let candidate = dir.join("apps").join("api");
            if candidate.join("app").join("main.py").exists() {
                return candidate;
            }
            match dir.parent() {
                Some(p) => dir = p.to_path_buf(),
                None => break,
            }
        }
    }

    if let Ok(cwd) = std::env::current_dir() {
        let mut dir = cwd.clone();
        for _ in 0..5 {
            let candidate = dir.join("apps").join("api");
            if candidate.join("app").join("main.py").exists() {
                return candidate;
            }
            match dir.parent() {
                Some(p) => dir = p.to_path_buf(),
                None => break,
            }
        }
    }

    std::path::PathBuf::from(".")
}

// =====================================================================
// Phase 3 Task 6 P0-C1:端口解析单元测试
// ---------------------------------------------------------------------
// 不在本次任务里跑 `cargo test`(没有 Tauri 编译时间预算),但代码里
// 给出 `#[cfg(test)]` 单测,后续 desktop CI 跑 cargo test 即可验证。
// Python 端另有 test_p0_c1_port_alignment.py 验证"后端配置端口
// = sidecar 默认端口"在 env var 协调下对齐。
// =====================================================================

#[cfg(test)]
mod tests {
    use super::*;

    /// 清理测试可能影响的环境变量(`PROTOFORGE_API_PORT` / `PROTOFORGE_SIDECAR_PORT`)。
    fn clear_env() {
        // SAFETY: tests in this module are single-threaded by default.
        unsafe {
            std::env::remove_var("PROTOFORGE_API_PORT");
            std::env::remove_var("PROTOFORGE_SIDECAR_PORT");
        }
    }

    #[test]
    fn port_defaults_when_no_env_set() {
        clear_env();
        assert_eq!(sidecar_port(), SIDECAR_API_PORT_DEFAULT);
        assert_eq!(sidecar_port(), 7655);
    }

    #[test]
    fn port_prefers_protoforge_api_port() {
        clear_env();
        // SAFETY: tests in this module are single-threaded by default.
        unsafe {
            std::env::set_var("PROTOFORGE_API_PORT", "7654");
        }
        assert_eq!(sidecar_port(), 7654);
        clear_env();
    }

    #[test]
    fn port_falls_back_to_legacy_sidecar_port() {
        clear_env();
        // SAFETY: tests in this module are single-threaded by default.
        unsafe {
            std::env::set_var("PROTOFORGE_SIDECAR_PORT", "8000");
        }
        assert_eq!(sidecar_port(), 8000);
        clear_env();
    }

    #[test]
    fn api_port_wins_over_legacy_sidecar_port() {
        clear_env();
        // SAFETY: tests in this module are single-threaded by default.
        unsafe {
            std::env::set_var("PROTOFORGE_API_PORT", "7654");
            std::env::set_var("PROTOFORGE_SIDECAR_PORT", "8000");
        }
        // PROTOFORGE_API_PORT 优先(P0-C1 修复)
        assert_eq!(sidecar_port(), 7654);
        clear_env();
    }

    #[test]
    fn invalid_port_string_falls_through() {
        clear_env();
        // SAFETY: tests in this module are single-threaded by default.
        unsafe {
            std::env::set_var("PROTOFORGE_API_PORT", "not-a-number");
        }
        // 解析失败 → 落到 default
        assert_eq!(sidecar_port(), SIDECAR_API_PORT_DEFAULT);
        clear_env();
    }
}
