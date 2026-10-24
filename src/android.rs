use anyhow::{Context, Result};
use jni::{
    objects::{GlobalRef, JObject},
    JavaVM,
};
use slint::android::AndroidApp;
use std::{path::PathBuf, sync::OnceLock};

struct AndroidContext {
    vm: JavaVM,
    activity: GlobalRef,
    files: PathBuf,
}
static CONTEXT: OnceLock<AndroidContext> = OnceLock::new();

pub fn init(app: &AndroidApp) -> Result<()> {
    let vm = unsafe { JavaVM::from_raw(app.vm_as_ptr().cast()) }?;
    let mut env = vm.attach_current_thread()?;
    let activity = unsafe { JObject::from_raw(app.activity_as_ptr().cast()) };
    let activity_global = env.new_global_ref(&activity)?;
    // AndroidApp owns the reference. Do not delete its handle.
    std::mem::forget(activity);
    let file_obj = env
        .call_method(
            activity_global.as_obj(),
            "getFilesDir",
            "()Ljava/io/File;",
            &[],
        )?
        .l()?;
    let absolute = env
        .call_method(file_obj, "getAbsolutePath", "()Ljava/lang/String;", &[])?
        .l()?;
    let path: String = env
        .get_string(&jni::objects::JString::from(absolute))?
        .into();
    std::fs::create_dir_all(&path)?;
    drop(env);
    CONTEXT
        .set(AndroidContext {
            vm,
            activity: activity_global,
            files: PathBuf::from(path),
        })
        .map_err(|_| anyhow::anyhow!("Android context already initialized"))?;
    Ok(())
}

pub fn files_dir() -> PathBuf {
    CONTEXT
        .get()
        .expect("Android context not initialized")
        .files
        .clone()
}

fn invoke(method: &str) -> Result<()> {
    let state = CONTEXT.get().context("Android context unavailable")?;
    let mut env = state.vm.attach_current_thread()?;
    env.call_method(state.activity.as_obj(), method, "()V", &[])
        .with_context(|| format!("Call Android activity method {method}"))?;
    Ok(())
}

pub fn system_dark() -> bool {
    let Some(state) = CONTEXT.get() else {
        return false;
    };
    let Ok(mut env) = state.vm.attach_current_thread() else {
        return false;
    };
    env.call_method(state.activity.as_obj(), "prefersDark", "()Z", &[])
        .ok()
        .and_then(|v| v.z().ok())
        .unwrap_or(false)
}

pub fn request_import() -> Result<()> {
    invoke("openDocuments")
}
pub fn request_export() -> Result<()> {
    invoke("exportAnswers")
}

pub fn receive_imports() -> Vec<PathBuf> {
    let queue = files_dir().join("pending-imports.txt");
    match std::fs::read_to_string(&queue) {
        Ok(data) => {
            let mut paths = Vec::new();
            for line in data.lines() {
                let path = PathBuf::from(line);
                if path.is_file() && path.starts_with(files_dir().join("imports")) {
                    paths.push(path);
                }
            }
            let _ = std::fs::remove_file(&queue);
            paths
        }
        Err(_) => Vec::new(),
    }
}
