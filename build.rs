fn main() {
    let config = slint_build::CompilerConfiguration::new().with_style("material".into());
    let target = std::env::var("TARGET").unwrap_or_default();
    let ui = if target.contains("android") {
        "ui/mobile.slint"
    } else {
        "ui/app.slint"
    };
    slint_build::compile_with_config(ui, config).expect("Compile Material UI");
}
