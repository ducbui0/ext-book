load("config.js");

function execute(key, page) {
    let host = getHost();

    let response = fetch(host + "/api/search?q=" + encodeURIComponent(key));
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
                cover: host + "/api/preview-cover-by-book/" + item.book_id,
                description: "Tác giả: " + (item.author || "Không rõ")
            });
        }
        return Response.success(books, null);
    }
    return Response.error("Không thể kết nối đến máy chủ Tomato để tìm kiếm truyện.");
}
