function getHost() {
    let host = "http://192.168.100.51:18423";
    try {
        if (CONFIG_URL) {
            host = CONFIG_URL;
        }
    } catch(e) {}
    
    // If the host URL is the KeyValue database resolver URL
    if (host.indexOf("keyvalue.immanuel.co") !== -1) {
        let response = fetch(host);
        if (response.ok) {
            let resolved = response.text();
            // Clean up double quotes returned by KeyValue API: e.g. "xxx_lhr_life" -> xxx_lhr_life
            resolved = resolved.replace(/^"|"$/g, '').trim();
            if (resolved) {
                // Convert underscores back to dots: e.g. xxx_lhr_life -> xxx.lhr.life
                resolved = resolved.replace(/_/g, ".");
                if (!resolved.startsWith("http")) {
                    resolved = "https://" + resolved;
                }
                return resolved;
            }
        }
    }
    
    return host;
}
