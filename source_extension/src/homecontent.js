function execute(url, page) {
    let host = "http://192.168.1.150:18423";
    try {
        if (CONFIG_URL) {
            host = CONFIG_URL;
        }
    } catch(e) {}

    let response = fetch(url + "?start=false", { headers: { "ngrok-skip-browser-warning": "true" } });
    if (!response.ok) {
        return Response.error("Không thể kết nối đến máy chủ Tomato Downloader. Vui lòng kiểm tra địa chỉ IP/Cổng trong cài đặt extension.");
    }

    let data = response.json();
    let items = data.items || [];

    // Fix #5: Gom tất cả book ID rồi gọi /api/batch_preview một lần thay vì N+1 requests
    let dirItems = [];
    for (let i = 0; i < items.length; i++) {
        if (items[i].kind === "dir") {
            dirItems.push(items[i]);
        }
    }

    // Thử batch preview trước (server mới hỗ trợ)
    let previewMap = {};
    if (dirItems.length > 0) {
        let ids = dirItems.map(function(it) { return it.name; }).join(",");
        try {
            let batchResponse = fetch(host + "/api/batch_preview?ids=" + ids, { headers: { "ngrok-skip-browser-warning": "true" } });
            if (batchResponse.ok) {
                previewMap = batchResponse.json();
            }
        } catch(e) {}
    }

    let books = [];
    for (let i = 0; i < dirItems.length; i++) {
        let bookId = dirItems[i].name;
        let preview = previewMap[bookId];

        // Fallback: nếu batch không trả về (server cũ), gọi riêng lẻ
        if (!preview) {
            let singleResponse = fetch(host + "/api/preview/" + bookId, { headers: { "ngrok-skip-browser-warning": "true" } });
            if (singleResponse.ok) {
                preview = singleResponse.json();
            }
        }

        if (preview) {
            let cover = "";
            if (preview.cover_url) {
                cover = preview.cover_url.startsWith("http") ? preview.cover_url : (host + preview.cover_url);
            }
            books.push({
                name: preview.book_name || bookId,
                link: "https://fanqienovel.com/page/" + bookId,
                host: host,
                cover: cover,
                description: preview.description || ("Tác giả: " + (preview.author || "Không rõ"))
            });
        } else {
            books.push({
                name: "Mã số: " + bookId,
                link: "https://fanqienovel.com/page/" + bookId,
                host: host,
                cover: "",
                description: "Nhấp vào để xem chi tiết hoặc cập nhật từ server."
            });
        }
    }

    return Response.success(books, null);
}
