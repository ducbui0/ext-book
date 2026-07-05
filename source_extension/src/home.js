function execute() {
    let host = "http://192.168.1.150:18423";
    try {
        if (CONFIG_URL) {
            host = CONFIG_URL;
        }
    } catch(e) {}
    
    return Response.success([
        {
            title: "Thư viện đã tải",
            input: host + "/api/library",
            script: "homecontent.js"
        }
    ]);
}
