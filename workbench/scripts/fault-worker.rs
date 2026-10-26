// Deliberate negative-control executable ONLY, built under .artifacts.
// Never included in the package or used for successful game-backed evidence.
use std::io::{self, BufRead};
fn main() {
    let _ = io::stdin().lock().lines().next();
    match std::env::var("WORKBENCH_FAULT").unwrap_or_default().as_str() {
        "protocol-mismatch" => println!("{{\"protocol\":99,\"id\":\"mismatch\",\"ok\":true,\"result\":{{}}}}"),
        "malformed-worker" => println!("unexpected stdout before JSON\n{{}}"),
        "worker-exit" => std::process::exit(17),
        "slow-worker" => {
            std::fs::write("fault-marker.txt", "temporary fault fixture").unwrap();
            std::thread::sleep(std::time::Duration::from_secs(60));
        },
        _ => std::process::exit(18),
    }
}
