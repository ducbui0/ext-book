function execute(url) {
    let host = "http://192.168.100.51:18423";
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

    // 1. Fetch book preview details to get the book name and TOC
    let previewResponse = fetch(host + "/api/preview/" + bookId);
    if (!previewResponse.ok) {
        return Response.error("Không thể kết nối đến máy chủ Tomato Downloader hoặc không tìm thấy thông tin truyện.");
    }
    let preview = previewResponse.json();
    let bookName = preview.book_name;

    // 2. Fetch the TOC from Fanqie official API to map chapter IDs to titles
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

    // 3. Try to read from the compiled .txt file in the library (Official Release support)
    if (bookName) {
        // Fetch book_name.txt
        let txtUrl = host + "/download/" + encodeURIComponent(bookName) + ".txt";
        let txtResponse = fetch(txtUrl);
        if (txtResponse.ok) {
            let txtContent = txtResponse.text();
            if (txtContent && currentTitle) {
                let chapterText = extractChapterFromTxt(txtContent, currentTitle, nextTitle);
                if (chapterText) {
                    return Response.success(formatContent(chapterText));
                }
            }
        }
    }

    // 4. Fallback: Try reading from status.json (Custom Build / Source Build support)
    let cacheKey = "tomato_cache_" + bookId;
    let cachedData = null;
    try {
        cachedData = localStorage.getItem(cacheKey);
    } catch(e) {}

    let data = null;
    if (cachedData) {
        try {
            data = JSON.parse(cachedData);
        } catch(e) {}
    }

    if (!data) {
        let response = fetch(host + "/download/" + bookId + "/status.json");
        if (response.ok) {
            data = response.json();
            try {
                localStorage.setItem(cacheKey, JSON.stringify(data));
            } catch(e) {
                clearOldCaches();
                try {
                    localStorage.setItem(cacheKey, JSON.stringify(data));
                } catch(err) {}
            }
        } else if (response.status === 404) {
            // Trigger automatic download job
            let triggerResponse = fetch(host + "/api/jobs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ "book_id": bookId })
            });
            if (triggerResponse.ok) {
                return Response.error("Truyện này chưa được tải về máy tính. Máy chủ đã tự động kích hoạt tải xuống.\n\nVui lòng đợi 1-2 phút rồi ấn 'Tải lại chương'!");
            }
        }
    }

    if (data && data.downloaded) {
        let pair = data.downloaded[chapId];
        if (pair && pair[1]) {
            return Response.success(formatContent(pair[1]));
        }
    }

    return Response.error("Chưa có nội dung cho chương này. Vui lòng kiểm tra tiến độ tải trên máy tính.");
}

function extractChapterFromTxt(txt, currentTitle, nextTitle) {
    let indexCurrent = txt.indexOf(currentTitle);
    if (indexCurrent === -1) {
        // Fallback case-insensitive
        let txtLower = txt.toLowerCase();
        let titleLower = currentTitle.toLowerCase();
        indexCurrent = txtLower.indexOf(titleLower);
    }
    
    if (indexCurrent === -1) {
        return null;
    }
    
    let startIndex = indexCurrent + currentTitle.length;
    let endIndex = txt.length;
    
    if (nextTitle) {
        let indexNext = txt.indexOf(nextTitle);
        if (indexNext === -1) {
            let txtLower = txt.toLowerCase();
            let nextTitleLower = nextTitle.toLowerCase();
            indexNext = txtLower.indexOf(nextTitleLower);
        }
        if (indexNext !== -1 && indexNext > startIndex) {
            endIndex = indexNext;
        }
    }
    
    return txt.substring(startIndex, endIndex).trim();
}

function formatContent(content) {
    return content
        .replace(/&lt;br&gt;/g, "<br>")
        .replace(/&lt;p&gt;/g, "")
        .replace(/&lt;\/p&gt;/g, "<br>")
        .replace(/\r\n|\r|\n/g, "<br><br>");
}

function clearOldCaches() {
    try {
        let keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            let key = localStorage.key(i);
            if (key && key.indexOf("tomato_cache_") === 0) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach(k => localStorage.removeItem(k));
    } catch(e) {}
}
