// Deliberate negative-control executable ONLY, built under .artifacts.
// Never included in the package or used for successful game-backed evidence.
use std::io::{self, BufRead, Write};
fn main() {
    let request = io::stdin().lock().lines().next().unwrap().unwrap();
    let fault = std::env::var("WORKBENCH_FAULT").unwrap_or_default();
    if fault.starts_with("draft-worker-") {
        if request.contains("preview_draft") {
            if fault == "draft-worker-exit" { std::process::exit(17); }
            std::fs::write("fault-marker.txt", "temporary draft fault fixture").unwrap();
            std::thread::sleep(std::time::Duration::from_secs(120));
            std::process::exit(19);
        }
        // Let discovery/open use the real worker. Only the explicitly named
        // draft operation is faulty; never count this helper as positive proof.
        use std::process::{Command, Stdio};
        let mut command = Command::new(std::env::var("WORKBENCH_REAL_PYTHON").unwrap());
        command.args(std::env::args().skip(1)).stdin(Stdio::piped());
        #[cfg(windows)] { use std::os::windows::process::CommandExt; command.creation_flags(0x08000000); }
        let mut child = command.spawn().unwrap();
        writeln!(child.stdin.take().unwrap(), "{}", request).unwrap();
        std::process::exit(child.wait().unwrap().code().unwrap_or(20));
    }
    match fault.as_str() {
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
