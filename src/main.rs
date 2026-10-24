mod api;
mod db;
mod import;

use db::Question;
use eframe::egui::{self, Color32, RichText};
use std::{collections::BTreeSet, path::PathBuf};

struct TikuApp {
    db_path: PathBuf,
    tab: usize,
    search: String,
    kind: i32,
    staged: Vec<PathBuf>,
    results: Vec<db::Record>,
    matched: Vec<(i32, Question)>,
    selected: BTreeSet<i64>,
    status: String,
    confirm_clear: bool,
    stats: [i64; 6],
}
impl TikuApp {
    fn new(db_path: PathBuf) -> Self {
        let mut app = Self {
            db_path,
            tab: 0,
            search: String::new(),
            kind: -1,
            staged: vec![],
            results: vec![],
            matched: vec![],
            selected: BTreeSet::new(),
            status: String::new(),
            confirm_clear: false,
            stats: [0; 6],
        };
        app.refresh();
        app
    }
    fn refresh(&mut self) {
        if let Ok(conn) = db::open(&self.db_path) {
            self.results = db::list(&conn, 100).unwrap_or_default();
            self.stats = db::stats(&conn).unwrap_or_default();
        }
    }
    fn import_all(&mut self) {
        let mut keep = Vec::new();
        let mut report = Vec::new();
        let queued = std::mem::take(&mut self.staged);
        for path in queued {
            let outcome = (|| -> anyhow::Result<usize> {
                let questions = import::from_path(&path)?;
                let mut conn = db::open(&self.db_path)?;
                db::add_many(&mut conn, &questions)
            })();
            match outcome {
                Ok(n) if n > 0 => report.push(format!("{}: 导入 {} 道", path.display(), n)),
                Ok(_) => {
                    report.push(format!("{}: 无有效标准答案", path.display()));
                    keep.push(path)
                }
                Err(e) => {
                    report.push(format!("{}: {e}", path.display()));
                    keep.push(path)
                }
            }
        }
        self.staged = keep;
        self.status = report.join("\n");
        self.refresh();
    }
    fn find(&mut self) {
        if let Ok(conn) = db::open(&self.db_path) {
            self.matched = db::search(
                &conn,
                &self.search,
                &[],
                if self.kind < 0 { None } else { Some(self.kind) },
                100,
            )
            .unwrap_or_default();
        }
    }
}
impl eframe::App for TikuApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::SidePanel::left("nav")
            .min_width(175.)
            .show(ctx, |ui| {
                ui.add_space(20.);
                ui.heading(
                    RichText::new("TIKU LOCAL")
                        .size(23.)
                        .color(Color32::from_rgb(54, 185, 190)),
                );
                ui.label("Rust · Native");
                ui.separator();
                ui.add_space(14.);
                for (i, text) in ["📥  批量导入", "🔎  搜索题库", "🗂  管理题库", "⚙  服务信息"]
                    .iter()
                    .enumerate()
                {
                    if ui.selectable_label(self.tab == i, *text).clicked() {
                        self.tab = i;
                        self.refresh();
                    }
                    ui.add_space(9.);
                }
                ui.with_layout(egui::Layout::bottom_up(egui::Align::LEFT), |ui| {
                    ui.label(format!("共 {} 道题目", self.stats[0]));
                    ui.label("API: 127.0.0.1:8060");
                });
            });
        egui::CentralPanel::default().show(ctx,|ui|{
            ui.add_space(10.);
            match self.tab{
                0=>{
                    ui.heading("批量导入题库");
                    ui.label("支持 Word (.docx) 和 JSON，可多选或直接将文件拖进窗口。确认后才会写入数据库。");
                    ui.add_space(10.);
                    if ui.button("＋  选择文件").clicked(){
                        if let Some(paths)=rfd::FileDialog::new().add_filter("题库", &["docx","json"]).pick_files(){
                            for path in paths{if !self.staged.contains(&path){self.staged.push(path);}}
                        }
                    }
                    ui.horizontal(|ui|{
                        if ui.button("导入全部文件").clicked(){self.import_all();}
                        if ui.button("清空待导入").clicked(){self.staged.clear();}
                    });
                    ui.separator();
                    egui::ScrollArea::vertical().max_height(220.).show(ui,|ui|{
                        let mut removal=None;
                        for (i,p) in self.staged.iter().enumerate(){
                            ui.horizontal(|ui|{
                                if ui.small_button("×").clicked(){removal=Some(i);}
                                ui.label(p.display().to_string());
                            });
                        }
                        if let Some(i)=removal{self.staged.remove(i);}
                    });
                    if !self.status.is_empty(){ui.separator();ui.label("导入结果");ui.label(&self.status);}
                },
                1=>{
                    ui.heading("搜索题目");
                    ui.horizontal(|ui|{
                        let edited=ui.text_edit_singleline(&mut self.search);
                        let mut requested=ui.button("搜索").clicked()||edited.lost_focus()&&ui.input(|i|i.key_pressed(egui::Key::Enter));
                        egui::ComboBox::from_id_salt("type").selected_text(match self.kind{-1=>"全部",0=>"单选",1=>"多选",2=>"填空",3=>"判断",_=>"问答"}).show_ui(ui,|ui|{
                            for (id,label) in [(-1,"全部"),(0,"单选"),(1,"多选"),(2,"填空"),(3,"判断"),(4,"问答")]{
                                if ui.selectable_value(&mut self.kind,id,label).changed(){requested=true;}
                            }
                        });
                        if requested{self.find();}
                    });
                    ui.label(format!("共 {} 条匹配",self.matched.len()));
                    egui::ScrollArea::vertical().show(ui,|ui|{
                        for (score,q) in &self.matched{
                            ui.group(|ui|{
                                ui.label(RichText::new(&q.question).strong());
                                ui.small(format!("类型 {} · 匹配评分 {}",q.kind,score));
                                for (i,opt) in q.options.iter().enumerate(){ui.label(format!("{}. {}",(b'A'+i as u8) as char,opt));}
                                ui.colored_label(Color32::from_rgb(38,170,133),format!("答案：{}",q.answer));
                            });ui.add_space(5.);
                        }
                    });
                },
                2=>{
                    ui.heading("题库管理");
                    ui.horizontal_wrapped(|ui|{
                        for (i,name) in ["全部","单选","多选","填空","判断","问答"].iter().enumerate(){
                            ui.group(|ui|{ui.label(*name);ui.heading(self.stats[i].to_string());});
                        }
                    });
                    ui.horizontal(|ui|{
                        if ui.button("刷新").clicked(){self.refresh();}
                        if ui.button("删除选中").clicked()&&!self.selected.is_empty(){
                            if let Ok(conn)=db::open(&self.db_path){let ids=self.selected.iter().copied().collect::<Vec<_>>();let _=db::delete(&conn,&ids);}
                            self.selected.clear();self.refresh();
                        }
                        if ui.button("清空题库…").clicked(){self.confirm_clear=true;}
                    });
                    if self.confirm_clear{
                        ui.horizontal(|ui|{
                            ui.colored_label(Color32::RED,"确认永久清空所有题目？");
                            if ui.button("确认清空").clicked(){if let Ok(conn)=db::open(&self.db_path){let _=db::clear(&conn);}self.confirm_clear=false;self.refresh();}
                            if ui.button("取消").clicked(){self.confirm_clear=false;}
                        });
                    }
                    ui.separator();
                    egui::ScrollArea::vertical().show(ui,|ui|{
                        for entry in &self.results{
                            ui.horizontal(|ui|{
                                let mut checked=self.selected.contains(&entry.id);
                                if ui.checkbox(&mut checked,"").changed(){if checked{self.selected.insert(entry.id);}else{self.selected.remove(&entry.id);}}
                                ui.vertical(|ui|{
                                    ui.label(RichText::new(format!("#{}  {}",entry.id,entry.question.question)).strong());
                                    ui.small(format!("类型 {}   答案 {}   {}",entry.question.kind,entry.question.answer,entry.created_at));
                                });
                            });ui.separator();
                        }
                    });
                },
                _=>{
                    ui.heading("设置和接口");
                    ui.label(format!("数据库：{}",self.db_path.display()));
                    ui.label("题库 API 默认只绑定本地回环地址，端口 8060。");
                    ui.monospace("POST http://127.0.0.1:8060/adapter-service/search");
                    ui.label("兼容 tikuAdapter / OCS 的常用 answerKey、answerIndex、bestAnswer、allAnswer 响应字段。");
                    if ui.button("打开数据库位置").clicked(){
                        if let Some(parent)=self.db_path.parent(){let _=std::process::Command::new(if cfg!(target_os="windows"){"explorer"}else if cfg!(target_os="macos"){"open"}else{"xdg-open"}).arg(parent).spawn();}
                    }
                }
            }
        });
        let dropped = ctx.input(|i| i.raw.dropped_files.clone());
        for file in dropped {
            if let Some(path) = file.path {
                if matches!(
                    path.extension().and_then(|v| v.to_str()),
                    Some("json" | "docx")
                ) && !self.staged.contains(&path)
                {
                    self.staged.push(path);
                    self.tab = 0;
                }
            }
        }
    }
}
fn main() -> eframe::Result<()> {
    let db_path = std::env::current_exe()
        .unwrap_or_else(|_| PathBuf::from("."))
        .parent()
        .unwrap_or_else(|| std::path::Path::new("."))
        .join("tiku.db");
    if let Err(e) = db::open(&db_path) {
        eprintln!("Database error: {e}");
    }
    if let Err(e) = api::start(db_path.clone()) {
        eprintln!("API server unavailable: {e}");
    }
    let opts = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1050., 730.])
            .with_min_inner_size([760., 520.]),
        ..Default::default()
    };
    eframe::run_native(
        "题库本地版 · Rust",
        opts,
        Box::new(move |cc| {
            cc.egui_ctx.set_visuals(egui::Visuals::dark());
            Ok(Box::new(TikuApp::new(db_path)))
        }),
    )
}
