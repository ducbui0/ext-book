function execute(url) {
    let bookId = url.match(/page\/(\d+)/)[1];
    let newurl = "https://fanqienovel.com/api/reader/directory/detail?bookId=" + bookId;
    let response = fetch(newurl);
    if (response.ok) {
        let doc = response.json();
        let el = doc.data.chapterListWithVolume;
        let list = [];
        
        for (let i = 0; i < el.length; i++) {
            let volume = el[i];
            for (let j = 0; j < volume.length; j++) {
                let chap = volume[j];
                list.push({
                    name: chap.title,
                    url: "https://fanqienovel.com/reader/" + bookId + "/" + chap.itemId
                });
            }
        }
        return Response.success(list);
    }
    return Response.error("Không thể lấy mục lục từ trang Fanqie. Vui lòng thử lại sau.");
}
