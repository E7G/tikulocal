use std::sync::Arc;
use tokio::sync::Mutex;
use warp::Filter;

use crate::db::Database;

pub struct HttpServer {
    shutdown: Option<tokio::task::JoinHandle<()>>,
}

impl HttpServer {
    pub fn start(db: Arc<Mutex<Database>>) -> Self {
        let db_clone = Arc::clone(&db);

        let route_index = warp::path::end().map(|| {
            warp::reply::html(
                r#"<html><head><title>题库适配器 API</title></head>
                <body><h1>题库适配器 API</h1>
                <p>POST /adapter-service/search</p></body></html>"#
            )
        });

        let route_status = warp::path("adapter-service")
            .and(warp::path::end())
            .map(|| warp::reply::json(&serde_json::json!({"status": "ok"})));

        let db_for_search = Arc::clone(&db_clone);
        let route_search = warp::path("adapter-service")
            .and(warp::path("search"))
            .and(warp::post())
            .and(warp::body::json())
            .and_then(move |body: serde_json::Value| {
                let db = Arc::clone(&db_for_search);
                async move {
                    let question = body["question"].as_str().unwrap_or("").to_string();
                    let options: Vec<String> = body["options"]
                        .as_array()
                        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                        .unwrap_or_default();

                    let db_guard = db.lock().await;
                    let result = db_guard.search_for_api(&question, &options);

                    match result {
                        Ok(Some(r)) => Ok::<_, warp::Rejection>(warp::reply::json(&r)),
                        Ok(None) => Ok(warp::reply::json(&serde_json::json!({
                            "plat": 0,
                            "question": question,
                            "options": options,
                            "type": 0,
                            "answer": {
                                "answerKey": [],
                                "answerKeyText": "",
                                "answerIndex": [],
                                "answerText": "",
                                "bestAnswer": [],
                                "allAnswer": []
                            }
                        }))),
                        Err(e) => Ok(warp::reply::json(&serde_json::json!({"error": e.to_string()}))),
                    }
                }
            });

        let routes = route_index
            .or(route_status)
            .or(route_search);

        let (tx, rx) = tokio::sync::oneshot::channel::<()>();
        let (_, server) = warp::serve(routes).bind_with_graceful_shutdown(
            ([127, 0, 0, 1], 8060),
            async {
                rx.await.ok();
            },
        );

        let handle = tokio::spawn(async move {
            server.await;
            drop(tx);
        });

        Self {
            shutdown: Some(handle),
        }
    }
}

impl Drop for HttpServer {
    fn drop(&mut self) {
        if let Some(handle) = self.shutdown.take() {
            handle.abort();
        }
    }
}
