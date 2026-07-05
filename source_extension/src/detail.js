function execute(url) {
    let host = "http://192.168.1.150:18423";
    try {
        if (CONFIG_URL) {
            host = CONFIG_URL;
        }
    } catch(e) {}

    let bookId = url.match(/page\/(\d+)/)[1];
    let response = fetch(host + "/api/preview/" + bookId, { headers: { "ngrok-skip-browser-warning": "true" } });
    if (response.ok) {
        let preview = response.json();
        let cover = "";
        if (preview.cover_url) {
            cover = preview.cover_url.startsWith("http") ? preview.cover_url : (host + preview.cover_url);
        }
        
        let detailText = "Trạng thái: " + (preview.finished ? "Hoàn thành" : "Đang ra") + "<br>" +
                         "Số chương: " + (preview.chapter_count || "Không rõ") + "<br>" +
                         "Số chữ: " + (preview.word_count || "Không rõ") + "<br>" +
                         "Điểm số: " + (preview.score || "Không rõ") + "<br>" +
                         "Lượt đọc: " + (preview.read_count_text || "Không rõ") + "<br>" +
                         "Thể loại: " + (preview.category || "Không rõ");

        return Response.success({
            name: preview.book_name || ("Sách ID: " + bookId),
            cover: cover,
            host: host,
            author: preview.author || "Không rõ",
            description: preview.description || "Không có mô tả.",
            detail: detailText,
            ongoing: !preview.finished
        });
    }
    return Response.error("Không thể kết nối đến máy chủ Tomato hoặc không tìm thấy truyện này.");
}
