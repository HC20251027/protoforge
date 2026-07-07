mod commands;
mod sidecar;

use log::info;
use tauri::Manager;

#[tauri::command]
fn ping() -> String {
    "pong".to_string()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let handle = app.handle().clone();

            // 启动 Python sidecar
            let sc = sidecar::Sidecar::spawn().expect("Failed to spawn sidecar");

            // health 轮询(异步,在 tokio runtime 中)
            tauri::async_runtime::spawn(async move {
                if let Err(e) = sc.wait_for_health().await {
                    log::error!("Sidecar health failed: {}", e);
                }
                // sidecar 存活周期绑定到 app handle
                handle.manage(sc);
            });

            info!("ProtoForge desktop starting ...");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            ping,
            commands::system_info,
            commands::health_check,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
