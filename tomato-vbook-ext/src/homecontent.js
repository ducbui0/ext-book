function execute(url, page) {
    let host = "http://192.168.100.51:18423";
    try {
        if (CONFIG_URL) {
            host = CONFIG_URL;
        }
    } catch(e) {}

    let response = fetch(url + "?start=false");
    if (response.ok) {
        let data = response.json();
        let items = data.items || [];
        let books = [];
        
        for (let i = 0; i < items.length; i++) {
            let item = items[i];
            if (item.kind === "dir") {
                let bookId = item.name;
                // Fetch book preview from Tomato local server
                let previewResponse = fetch(host + "/api/preview/" + bookId);
                if (previewResponse.ok) {
                    let preview = previewResponse.json();
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
        }
        return Response.success(books, null);
    }
    return Response.error("Không thể kết nối đến máy chủ Tomato Downloader. Vui lòng kiểm tra địa chỉ IP/Cổng trong cài đặt extension.");
}
