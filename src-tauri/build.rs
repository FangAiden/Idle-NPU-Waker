fn main() {
    let profile = std::env::var("PROFILE").unwrap_or_default();
    if profile == "debug" && std::env::var_os("TAURI_CONFIG").is_none() {
        let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_default();
        let dev_patch_path = std::path::Path::new(&manifest_dir).join("tauri.conf.dev.json");
        println!("cargo:rerun-if-changed={}", dev_patch_path.display());
        let patch = std::fs::read_to_string(&dev_patch_path)
            .unwrap_or_else(|_| r#"{"bundle":{"externalBin":[]}}"#.to_string());
        std::env::set_var("TAURI_CONFIG", patch);
    }

    tauri_build::build()
}
