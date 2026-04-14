async function ExportAPI(projectId) {
  // 跳出輸入框
  const password = prompt("請輸入ZIP壓縮密碼：");

  // 使用者按取消
  if (password === null) {
    return;
  }

  const button = event.currentTarget;
  button.disabled = true;
  button.innerText = '匯出中...';

  try {
    await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        project_id: projectId,
        zip_password: password   // 👈 把密碼送出去
      })
    });

    setTimeout(() => {
      window.location.reload();
    }, 500);

  } catch (err) {
    console.error(err);
    alert('匯出失敗');
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