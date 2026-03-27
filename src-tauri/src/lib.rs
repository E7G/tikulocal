use std::sync::Arc;
use tokio::sync::Mutex;

mod db;
mod parser;
mod server;

pub use db::Database;
pub use parser::QuestionParser;
pub use server::HttpServer;

pub struct AppState {
    pub db: Arc<Mutex<Database>>,
    pub server: Arc<Mutex<Option<HttpServer>>>,
}

#[tauri::command]
async fn search_questions(
    question: String,
    qtype: i32,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<Vec<serde_json::Value>, String> {
    let db = state.db.lock().await;
    db.search_questions(&question, qtype).map_err(|e| e.to_string())
}

#[tauri::command]
async fn import_docx(
    path: String,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<usize, String> {
    let questions = QuestionParser::parse_docx(&path).map_err(|e| e.to_string())?;
    let mut db = state.db.lock().await;
    db.insert_questions(&questions).map_err(|e| e.to_string())
}

#[tauri::command]
async fn import_json(
    path: String,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<usize, String> {
    let content = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let questions: Vec<serde_json::Value> =
        serde_json::from_str(&content).map_err(|e| e.to_string())?;
    let mut db = state.db.lock().await;
    db.insert_questions(&questions).map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_stats(state: tauri::State<'_, Arc<AppState>>) -> Result<serde_json::Value, String> {
    let db = state.db.lock().await;
    db.get_stats().map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_questions(
    limit: i32,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<Vec<serde_json::Value>, String> {
    let db = state.db.lock().await;
    db.get_questions(limit).map_err(|e| e.to_string())
}

#[tauri::command]
async fn delete_question(
    id: i64,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<(), String> {
    let db = state.db.lock().await;
    db.delete_question(id).map_err(|e| e.to_string())
}

#[tauri::command]
async fn clear_all(state: tauri::State<'_, Arc<AppState>>) -> Result<(), String> {
    let db = state.db.lock().await;
    db.clear_all().map_err(|e| e.to_string())
}

#[tauri::command]
async fn start_server(
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<(), String> {
    let db = Arc::clone(&state.db);
    let server = HttpServer::start(db);
    let mut server_guard = state.server.lock().await;
    *server_guard = Some(server);
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let db_path = std::env::current_exe()
        .map(|p| p.parent().unwrap().join("tiku.db"))
        .unwrap_or_else(|_| std::path::PathBuf::from("tiku.db"));

    let db = Database::new(&db_path).expect("Failed to init database");
    let state = Arc::new(AppState {
        db: Arc::new(Mutex::new(db)),
        server: Arc::new(Mutex::new(None)),
    });

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(state.clone())
        .invoke_handler(tauri::generate_handler![
            search_questions,
            import_docx,
            import_json,
            get_stats,
            get_questions,
            delete_question,
            clear_all,
            start_server,
        ])
        .setup(move |_app| {
            let state_clone = state.clone();
            tauri::async_runtime::spawn(async move {
                let db = Arc::clone(&state_clone.db);
                let server = HttpServer::start(db);
                let mut server_guard = state_clone.server.lock().await;
                *server_guard = Some(server);
                println!("HTTP server started on port 8060");
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
