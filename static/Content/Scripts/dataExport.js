async function ExportAPI(projectId) {
  const button = event.currentTarget;
  button.disabled = true;
  button.innerText = '匯出中...';

  try {
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId })
    });

    const data = await res.json();

    // 🔥 顯示提示
    alert(data.message || '匯出已開始');

    // 🔥 稍等再刷新
    setTimeout(() => {
      window.location.reload();
    }, 1500);

  } catch (err) {
    console.error(err);
    alert(data.message);
  }
}

function  downloadData(projectId, folderName, status) {
  // body...
    if (status === "completed") {
        const url = `/api/download?folder_name=${projectId}/${folderName}`;
        // 👉 直接跳下載
        window.location.href = url;
        } else if (status === "running") {
          alert("資料仍在匯出中，請稍後再下載......");

        } else if (status === "empty") {
          alert("資料尚未產生");

        } else if (status === "not_found") {
          alert("尚未建立匯出資料");

        } else {
          alert("狀態異常，無法下載");
        }
}