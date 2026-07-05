function execute(url) {
    let host = "http://192.168.1.150:18423";
    try {
        if (CONFIG_URL) {
            host = CONFIG_URL;
        }
    } catch(e) {}

    let match = url.match(/reader\/(\d+)\/(\d+)/);
    if (!match) {
        return Response.error("Đường dẫn chương không hợp lệ.");
    }
    let bookId = match[1];
    let chapId = match[2];

    // 1. Fetch book preview
    let previewResponse = fetch(host + "/api/preview/" + bookId, { headers: { "ngrok-skip-browser-warning": "true" } });
    if (!previewResponse.ok) {
        return Response.error("Không thể kết nối đến máy chủ Tomato Downloader hoặc không tìm thấy thông tin truyện.");
    }
    let preview = previewResponse.json();
    let txtFilePath = preview.txt_file; 

    // Nếu chưa có file .txt (tức là truyện chưa tải trên PC) -> Trigger tải xuống!
    if (!txtFilePath) {
        // Trigger automatic download job
        let triggerResponse = fetch(host + "/api/jobs", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            body: JSON.stringify({ "book_id": bookId })
        });
        if (triggerResponse.ok) {
            return Response.error("Truyện này chưa được tải về máy tính. Máy chủ đã tự động kích hoạt tải xuống.\n\nVui lòng đợi 1-2 phút rồi ấn 'Tải lại chương'!");
        }
        return Response.error("Chưa có file txt trên máy tính. Vui lòng kiểm tra lại.");
    }

    // 2. Nếu đã có file txt -> Fetch TOC từ Fanqie để lấy title
    let tocUrl = "https://fanqienovel.com/api/reader/directory/detail?bookId=" + bookId;
    let tocResponse = fetch(tocUrl);
    let chapters = [];
    if (tocResponse.ok) {
        let tocJson = tocResponse.json();
        let volumes = tocJson.data.chapterListWithVolume;
        for (let i = 0; i < volumes.length; i++) {
            let vol = volumes[i];
            for (let j = 0; j < vol.length; j++) {
                chapters.push({
                    id: vol[j].itemId,
                    title: vol[j].title
                });
            }
        }
    }

    // Find current and next chapter titles
    let currentTitle = "";
    let nextTitle = "";
    for (let i = 0; i < chapters.length; i++) {
        if (chapters[i].id == chapId) {
            currentTitle = chapters[i].title;
            if (i + 1 < chapters.length) {
                nextTitle = chapters[i + 1].title;
            }
            break;
        }
    }

    // 3. Gọi Máy chủ trích xuất chữ của chương này (Nhanh & Tối ưu tải hàng loạt)
    if (currentTitle) {
        let chapterUrl = host + "/api/chapter/" + bookId + "?title=" + encodeURIComponent(currentTitle) + "&next=" + encodeURIComponent(nextTitle);
        let chapterResponse = fetch(chapterUrl, { headers: { "ngrok-skip-browser-warning": "true" } });
        if (chapterResponse.ok) {
            let json = chapterResponse.json();
            if (json.content) {
                return Response.success(formatContent(json.content));
            }
        }
    }

    return Response.error("Không thể trích xuất chương này. File txt có thể bị lỗi hoặc chưa hoàn thiện.");
}

function formatContent(content) {
    return content
        .replace(/&lt;br&gt;/g, "<br>")
        .replace(/&lt;p&gt;/g, "")
        .replace(/&lt;\/p&gt;/g, "<br>")
        .replace(/\r\n|\r|\n/g, "<br><br>");
}
