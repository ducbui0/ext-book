load("config.js");

function execute() {
    let host = getHost();
    
    return Response.success([
        {
            title: "Thư viện đã tải",
            input: host + "/api/library",
            script: "homecontent.js"
        }
    ]);
}

