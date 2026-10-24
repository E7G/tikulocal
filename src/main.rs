#![cfg_attr(
    all(target_os = "windows", not(debug_assertions)),
    windows_subsystem = "windows"
)]

mod api;
mod db;
mod import;

slint::include_modules!();

use slint::{Model, ModelRc, SharedString, StandardListViewItem, VecModel};
use std::{
    collections::BTreeSet,
    fs::File,
    path::{Path, PathBuf},
    rc::Rc,
    sync::{Arc, Mutex},
};

fn kind_name(kind: i32) -> &'static str {
    match kind {
        0 => "单选题",
        1 => "多选题",
        2 => "填空题",
        3 => "判断题",
        4 => "问答题",
        _ => "未知题型",
    }
}

fn question_row(rec: &db::Record) -> QuestionRow {
    QuestionRow {
        id: rec.id as i32,
        title: SharedString::from(rec.question.question.as_str()),
        options: SharedString::from(
            rec.question
                .options
                .iter()
                .enumerate()
                .map(|(idx, x)| format!("{}. {}", (b'A' + idx.min(25) as u8) as char, x))
                .collect::<Vec<_>>()
                .join("  ")
                .as_str(),
        ),
        answer: SharedString::from(rec.question.answer.as_str()),
        kind: SharedString::from(kind_name(rec.question.kind)),
        date: SharedString::from(rec.created_at.as_str()),
        selected: false,
    }
}

fn list_item(text: &str) -> StandardListViewItem {
    SharedString::from(text).into()
}

fn table_row(cells: &[String]) -> ModelRc<StandardListViewItem> {
    ModelRc::new(VecModel::from(
        cells.iter().map(|text| list_item(text)).collect::<Vec<_>>(),
    ))
}

fn set_manage_table(app: &MainWindow, model: &VecModel<QuestionRow>) {
    let rows = (0..model.row_count())
        .filter_map(|index| model.row_data(index))
        .map(|row| {
            table_row(&[
                if row.selected { "✓" } else { "" }.to_owned(),
                row.id.to_string(),
                row.kind.to_string(),
                row.title.to_string(),
                row.answer.to_string(),
            ])
        })
        .collect::<Vec<_>>();
    app.set_manage_table_rows(ModelRc::new(VecModel::from(rows)));
}

fn show_staged(app: &MainWindow, staged: &Arc<Mutex<Vec<PathBuf>>>) {
    let rows: Vec<FileRow> = staged
        .lock()
        .unwrap()
        .iter()
        .map(|path| FileRow {
            name: SharedString::from(
                path.file_name()
                    .map(|s| s.to_string_lossy().to_string())
                    .unwrap_or_default()
                    .as_str(),
            ),
            path: SharedString::from(path.to_string_lossy().as_ref()),
        })
        .collect();
    let file_items = rows
        .iter()
        .map(|row| list_item(&format!("{}    —    {}", row.name, row.path)))
        .collect::<Vec<_>>();
    app.set_file_items(ModelRc::new(VecModel::from(file_items)));
    app.set_staged_files(ModelRc::new(VecModel::from(rows)));
    app.set_selected_file_index(-1);
}

fn refresh_ui(app: &MainWindow, database: &Path, manage_model: &VecModel<QuestionRow>) {
    match db::open(database).and_then(|conn| Ok((db::stats(&conn)?, db::list(&conn, 200)?))) {
        Ok((count, records)) => {
            app.set_total(count[0] as i32);
            app.set_single_count(count[1] as i32);
            app.set_multiple_count(count[2] as i32);
            app.set_blank_count(count[3] as i32);
            app.set_judge_count(count[4] as i32);
            app.set_essay_count(count[5] as i32);
            manage_model.set_vec(records.iter().map(question_row).collect::<Vec<_>>());
            set_manage_table(app, manage_model);
            app.set_selected_manage_row(-1);
            app.set_selected_count(0);
        }
        Err(error) => app.set_status(format!("数据库读取失败：{error}").into()),
    }
}

fn database_path() -> PathBuf {
    let executable = std::env::current_exe().unwrap_or_default();
    let adjacent = executable
        .parent()
        .unwrap_or(Path::new("."))
        .join("tiku.db");
    if adjacent.exists() {
        return adjacent;
    }
    let dir = if cfg!(target_os = "windows") {
        std::env::var_os("LOCALAPPDATA").map(PathBuf::from)
    } else if cfg!(target_os = "macos") {
        std::env::var_os("HOME").map(|h| PathBuf::from(h).join("Library/Application Support"))
    } else {
        std::env::var_os("XDG_DATA_HOME")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".local/share")))
    }
    .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());
    let dir = dir.join("TikuLocal");
    if std::fs::create_dir_all(&dir).is_err() {
        return adjacent;
    }
    dir.join("tiku.db")
}

fn appearance_path() -> PathBuf {
    let base = if cfg!(target_os = "windows") {
        std::env::var_os("LOCALAPPDATA").map(PathBuf::from)
    } else if cfg!(target_os = "macos") {
        std::env::var_os("HOME").map(|home| PathBuf::from(home).join("Library/Application Support"))
    } else {
        std::env::var_os("XDG_CONFIG_HOME")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".config")))
    }
    .unwrap_or_else(|| std::env::temp_dir());
    base.join("TikuLocal").join("appearance.txt")
}

fn read_appearance() -> i32 {
    std::fs::read_to_string(appearance_path())
        .ok()
        .and_then(|s| s.trim().parse::<i32>().ok())
        .filter(|mode| (0..=2).contains(mode))
        .unwrap_or(0)
}

fn save_appearance(mode: i32) {
    let path = appearance_path();
    if let Some(parent) = path.parent() {
        if std::fs::create_dir_all(parent).is_err() {
            return;
        }
    }
    let _ = std::fs::write(path, mode.to_string());
}

#[cfg(windows)]
fn system_prefers_dark() -> bool {
    #[link(name = "advapi32")]
    unsafe extern "system" {
        fn RegGetValueW(
            hkey: isize,
            subkey: *const u16,
            value: *const u16,
            flags: u32,
            value_type: *mut u32,
            data: *mut u8,
            len: *mut u32,
        ) -> i32;
    }
    fn utf16(text: &str) -> Vec<u16> {
        text.encode_utf16().chain(std::iter::once(0)).collect()
    }
    let subkey = utf16("Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize");
    let value = utf16("AppsUseLightTheme");
    let mut result: u32 = 1;
    let mut len = std::mem::size_of::<u32>() as u32;
    let ok = unsafe {
        RegGetValueW(
            0x80000001_u32 as isize,
            subkey.as_ptr(),
            value.as_ptr(),
            0x18,
            std::ptr::null_mut(),
            (&mut result as *mut u32).cast::<u8>(),
            &mut len,
        )
    };
    ok == 0 && result == 0
}

#[cfg(target_os = "macos")]
fn system_prefers_dark() -> bool {
    std::process::Command::new("defaults")
        .args(["read", "-g", "AppleInterfaceStyle"])
        .output()
        .map(|output| String::from_utf8_lossy(&output.stdout).trim() == "Dark")
        .unwrap_or(false)
}

#[cfg(not(any(windows, target_os = "macos")))]
fn system_prefers_dark() -> bool {
    if let Ok(theme) = std::env::var("GTK_THEME") {
        if theme.to_lowercase().contains("dark") {
            return true;
        }
    }
    std::process::Command::new("gsettings")
        .args(["get", "org.gnome.desktop.interface", "color-scheme"])
        .output()
        .map(|output| String::from_utf8_lossy(&output.stdout).contains("prefer-dark"))
        .unwrap_or(false)
}

#[cfg(windows)]
fn apply_windows_titlebar(dark: bool) {
    #[link(name = "user32")]
    unsafe extern "system" {
        fn EnumWindows(
            callback: unsafe extern "system" fn(isize, isize) -> i32,
            data: isize,
        ) -> i32;
        fn GetWindowThreadProcessId(hwnd: isize, process_id: *mut u32) -> u32;
        fn IsWindowVisible(hwnd: isize) -> i32;
    }
    unsafe extern "system" fn find_our_window(hwnd: isize, data: isize) -> i32 {
        let mut process_id: u32 = 0;
        unsafe {
            GetWindowThreadProcessId(hwnd, &mut process_id);
            if process_id == std::process::id() && IsWindowVisible(hwnd) != 0 {
                *(data as *mut isize) = hwnd;
                return 0;
            }
        }
        1
    }
    #[link(name = "dwmapi")]
    unsafe extern "system" {
        fn DwmSetWindowAttribute(hwnd: isize, attribute: u32, value: *const u32, size: u32) -> i32;
    }
    // Enumerate our visible top-level window; exact-title lookup is unreliable on some systems.
    let mut hwnd: isize = 0;
    unsafe {
        EnumWindows(find_our_window, (&mut hwnd as *mut isize) as isize);
    }
    if hwnd == 0 {
        return;
    }
    let dark_mode = u32::from(dark);
    let rounded: u32 = 2;
    // COLORREF uses BGR byte order; matching caption colors prevent dark/light mismatch.
    let caption: u32 = if dark { 0x002D2420 } else { 0x00FAF6F4 };
    let caption_text: u32 = if dark { 0x00FCF7F5 } else { 0x00392920 };
    unsafe {
        let _ = DwmSetWindowAttribute(hwnd, 20, &dark_mode, 4);
        let _ = DwmSetWindowAttribute(hwnd, 33, &rounded, 4);
        let _ = DwmSetWindowAttribute(hwnd, 35, &caption, 4);
        let _ = DwmSetWindowAttribute(hwnd, 36, &caption_text, 4);
    }
}

#[cfg(not(windows))]
fn apply_windows_titlebar(_dark: bool) {}

fn main() {
    if let Err(error) = run() {
        let message = format!("TikuLocal 启动失败：\\n{error}");
        eprintln!("{message}");
        let _ = rfd::MessageDialog::new()
            .set_title("TikuLocal · 启动失败")
            .set_description(&message)
            .set_level(rfd::MessageLevel::Error)
            .show();
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let database = database_path();
    db::open(&database)?;
    let api_state = match api::start(database.clone()) {
        Ok(()) => "本地 API 正在监听 · 8060".to_string(),
        Err(error) => format!("API 启动失败：{error}"),
    };
    let app = MainWindow::new()?;
    let preferred_theme = read_appearance();
    app.set_system_dark(system_prefers_dark());
    app.set_theme_mode(preferred_theme);
    app.invoke_apply_palette(preferred_theme);
    {
        let weak = app.as_weak();
        app.on_theme_changed(move |mode| {
            save_appearance(mode);
            if let Some(ui) = weak.upgrade() {
                let dark = mode == 2 || (mode == 0 && ui.get_system_dark());
                apply_windows_titlebar(dark);
            }
        });
    }
    app.set_database_path(database.to_string_lossy().to_string().into());
    app.set_service_state(api_state.into());
    let staged = Arc::new(Mutex::new(Vec::<PathBuf>::new()));
    let manage_model: Rc<VecModel<QuestionRow>> = Rc::new(VecModel::default());
    app.set_manage_rows(manage_model.clone().into());
    refresh_ui(&app, &database, &manage_model);
    show_staged(&app, &staged);
    {
        let staged = staged.clone();
        let weak = app.as_weak();
        app.on_choose_files(move || {
            if let Some(files) = rfd::FileDialog::new()
                .add_filter("题库文件", &["docx", "json"])
                .pick_files()
            {
                let mut queue = staged.lock().unwrap();
                for path in files {
                    if !queue.contains(&path) {
                        queue.push(path);
                    }
                }
                drop(queue);
                if let Some(ui) = weak.upgrade() {
                    show_staged(&ui, &staged);
                }
            }
        });
    }
    {
        let staged = staged.clone();
        let weak = app.as_weak();
        app.on_remove_staged(move |index| {
            if index >= 0 && (index as usize) < staged.lock().unwrap().len() {
                staged.lock().unwrap().remove(index as usize);
            }
            if let Some(ui) = weak.upgrade() {
                show_staged(&ui, &staged);
            }
        });
    }
    {
        let staged = staged.clone();
        let weak = app.as_weak();
        app.on_clear_staged(move || {
            staged.lock().unwrap().clear();
            if let Some(ui) = weak.upgrade() {
                show_staged(&ui, &staged);
            }
        });
    }
    {
        let weak = app.as_weak();
        let database = database.clone();
        let staged = staged.clone();
        app.on_import_all(move || {
            let paths = staged.lock().unwrap().clone();
            if paths.is_empty() {
                return;
            }
            if let Some(ui) = weak.upgrade() {
                ui.set_import_busy(true);
                ui.set_status("正在导入文件…".into());
            }
            let weak = weak.clone();
            let database = database.clone();
            let staged = staged.clone();
            std::thread::spawn(move || {
                let mut failed = Vec::new();
                let mut logs = Vec::new();
                let mut total = 0;
                for path in paths {
                    let result = (|| -> anyhow::Result<usize> {
                        let parsed = import::from_path(&path)?;
                        let mut conn = db::open(&database)?;
                        db::add_many(&mut conn, &parsed)
                    })();
                    let name = path
                        .file_name()
                        .map(|n| n.to_string_lossy().to_string())
                        .unwrap_or_default();
                    match result {
                        Ok(n) if n > 0 => {
                            total += n;
                            logs.push(format!("{name}: {n} 道"));
                        }
                        Ok(_) => {
                            failed.push(path);
                            logs.push(format!("{name}: 未识别到可导入答案"));
                        }
                        Err(e) => {
                            failed.push(path);
                            logs.push(format!("{name}: {e}"));
                        }
                    }
                }
                let message = format!("共导入 {total} 道。{}", logs.join("；"));
                let _ = weak.upgrade_in_event_loop(move |ui| {
                    *staged.lock().unwrap() = failed;
                    show_staged(&ui, &staged);
                    let manage = ui.get_manage_rows();
                    if let Some(model) = manage.as_any().downcast_ref::<VecModel<QuestionRow>>() {
                        refresh_ui(&ui, &database, model);
                    }
                    ui.set_import_busy(false);
                    ui.set_import_report(logs.join("\n").into());
                    ui.set_status(message.into());
                });
            });
        });
    }
    {
        let weak = app.as_weak();
        let database = database.clone();
        app.on_search(move |query, index| {
            let Some(ui) = weak.upgrade() else { return };
            let kind = if index == 0 { None } else { Some(index - 1) };
            match db::open(&database)
                .and_then(|conn| db::search(&conn, query.as_str(), &[], kind, 100))
            {
                Ok(found) => {
                    ui.set_match_count(found.len() as i32);
                    let rows = found
                        .iter()
                        .map(|(_, q)| QuestionRow {
                            id: 0,
                            title: q.question.clone().into(),
                            answer: q.answer.clone().into(),
                            kind: kind_name(q.kind).into(),
                            options: q.options.join(" · ").into(),
                            date: "".into(),
                            selected: false,
                        })
                        .collect::<Vec<_>>();
                    let table_rows = rows
                        .iter()
                        .map(|row: &QuestionRow| {
                            table_row(&[
                                row.kind.to_string(),
                                row.title.to_string(),
                                row.options.to_string(),
                                row.answer.to_string(),
                            ])
                        })
                        .collect::<Vec<_>>();
                    ui.set_search_table_rows(ModelRc::new(VecModel::from(table_rows)));
                    ui.set_search_results(ModelRc::new(VecModel::from(rows)));
                    ui.set_status(format!("搜索完成：{} 道匹配题目", found.len()).into());
                }
                Err(e) => ui.set_status(format!("搜索失败：{e}").into()),
            }
        });
    }
    {
        let weak = app.as_weak();
        let database = database.clone();
        let model = manage_model.clone();
        app.on_refresh(move || {
            if let Some(ui) = weak.upgrade() {
                refresh_ui(&ui, &database, &model);
            }
        });
    }
    {
        let weak = app.as_weak();
        let model = manage_model.clone();
        app.on_toggle_selected(move |index| {
            if index < 0 {
                return;
            }
            if let Some(mut row) = model.row_data(index as usize) {
                row.selected = !row.selected;
                model.set_row_data(index as usize, row);
            }
            let count = (0..model.row_count())
                .filter(|&i| model.row_data(i).is_some_and(|r| r.selected))
                .count();
            if let Some(ui) = weak.upgrade() {
                ui.set_selected_count(count as i32);
                set_manage_table(&ui, &model);
            }
        });
    }
    {
        let weak = app.as_weak();
        let database = database.clone();
        let model = manage_model.clone();
        app.on_delete_selected(move || {
            let ids = (0..model.row_count())
                .filter_map(|i| model.row_data(i))
                .filter(|r| r.selected)
                .map(|r| r.id as i64)
                .collect::<BTreeSet<_>>()
                .into_iter()
                .collect::<Vec<_>>();
            if let Some(ui) = weak.upgrade() {
                match db::open(&database).and_then(|conn| db::delete(&conn, &ids)) {
                    Ok(n) => {
                        refresh_ui(&ui, &database, &model);
                        ui.set_status(format!("删除 {n} 道题目").into());
                    }
                    Err(e) => ui.set_status(format!("删除失败：{e}").into()),
                }
            }
        });
    }
    {
        let weak = app.as_weak();
        let database = database.clone();
        let model = manage_model.clone();
        app.on_clear_all(move || {
            if let Some(ui) = weak.upgrade() {
                match db::open(&database).and_then(|conn| db::clear(&conn)) {
                    Ok(n) => {
                        refresh_ui(&ui, &database, &model);
                        ui.set_status(format!("已清空 {n} 道题目").into());
                    }
                    Err(e) => ui.set_status(format!("清空失败：{e}").into()),
                }
            }
        });
    }
    {
        let database = database.clone();
        let weak = app.as_weak();
        app.on_export_json(move || {
            let Some(ui) = weak.upgrade() else { return };
            let Some(path) = rfd::FileDialog::new()
                .set_file_name("tiku-export.json")
                .add_filter("JSON", &["json"])
                .save_file()
            else {
                return;
            };
            let outcome = (|| -> anyhow::Result<usize> {
                let conn = db::open(&database)?;
                let rows = db::list(&conn, 10_000_000)?;
                let count = rows.len();
                let questions = rows.into_iter().map(|r| r.question).collect::<Vec<_>>();
                serde_json::to_writer_pretty(File::create(path)?, &questions)?;
                Ok(count)
            })();
            ui.set_status(
                match outcome {
                    Ok(n) => format!("成功导出 {n} 道题目"),
                    Err(e) => format!("导出失败：{e}"),
                }
                .into(),
            );
        });
    }
    {
        let database = database.clone();
        app.on_open_folder(move || {
            if let Some(parent) = database.parent() {
                let command = if cfg!(target_os = "windows") {
                    "explorer"
                } else if cfg!(target_os = "macos") {
                    "open"
                } else {
                    "xdg-open"
                };
                let _ = std::process::Command::new(command).arg(parent).spawn();
            }
        });
    }
    app.show()?;
    // Winit may create its native HWND after the first event-loop iteration.
    // Retry once so the caption always matches a persisted manual theme.
    let chrome_weak = app.as_weak();
    slint::Timer::single_shot(std::time::Duration::from_millis(250), move || {
        if let Some(ui) = chrome_weak.upgrade() {
            let dark =
                ui.get_theme_mode() == 2 || (ui.get_theme_mode() == 0 && ui.get_system_dark());
            apply_windows_titlebar(dark);
        }
    });
    apply_windows_titlebar(
        app.get_theme_mode() == 2 || (app.get_theme_mode() == 0 && app.get_system_dark()),
    );

    // Keep "follow system" responsive to appearance changes.
    let palette_poll = slint::Timer::default();
    let weak = app.as_weak();
    palette_poll.start(
        slint::TimerMode::Repeated,
        std::time::Duration::from_secs(4),
        move || {
            if let Some(ui) = weak.upgrade() {
                let dark = system_prefers_dark();
                if ui.get_system_dark() != dark {
                    ui.set_system_dark(dark);
                    if ui.get_theme_mode() == 0 {
                        apply_windows_titlebar(dark);
                    }
                }
            }
        },
    );
    app.run()?;
    Ok(())
}
