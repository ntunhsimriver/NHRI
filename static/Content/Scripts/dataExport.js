async function ExportAPI(projectId) {
  const button = event.currentTarget;
  button.disabled = true;
  button.innerText = '匯出中...';

  try {
    await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId })
    });

    // 稍微等一下（避免 race condition）
    setTimeout(() => {
      window.location.reload();
    }, 500);

  } catch (err) {
    console.error(err);
    alert('匯出失敗');
  }
}

function  downloadData(projectId, folderName) {
  // body...
    const url = `/api/download?folder_name=${projectId}/${folderName}`;
    // 👉 直接跳下載
    window.location.href = url;
}