function execute(key, page) {
    let host = "http://192.168.1.150:18423";
    try {
        if (CONFIG_URL) {
            host = CONFIG_URL;
        }
    } catch(e) {}

    let response = fetch(host + "/api/search?q=" + encodeURIComponent(key), { headers: { "ngrok-skip-browser-warning": "true" } });
    if (response.ok) {
        let data = response.json();
        let items = data.items || [];
        let books = [];
        
        for (let i = 0; i < items.length; i++) {
            let item = items[i];
            books.push({
                name: item.title,
                link: "https://fanqienovel.com/page/" + item.book_id,
                host: host,
                cover: item.cover_url || "",
                description: "Tác giả: " + (item.author || "Không rõ")
            });
        }
        return Response.success(books, null);
    }
    return Response.error("Không thể kết nối đến máy chủ Tomato để tìm kiếm truyện.");
}
