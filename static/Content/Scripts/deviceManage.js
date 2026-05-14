
// 新增使用者
var ModaladdDevice = document.getElementById('Modal_addDevice');
// 等等要關閉這個彈跳視窗用的
var ModalInstance = bootstrap.Modal.getOrCreateInstance(ModaladdDevice);

ModaladdDevice.addEventListener('show.bs.modal', function (event) {
    var button = event.relatedTarget; // 取得被點擊的按鈕
    var input_data = button.getAttribute('data-bs-value')
    var data = JSON.parse(input_data);

    var modalTitle = document.getElementById('Modal_addDevice_title');
    var Model_id = document.getElementById('DeviceId');
    if (data.id) {
      if (modalTitle) modalTitle.textContent = '更新設備';
      Model_id.readOnly = true;   // 編輯 → 鎖住

    } 
    // 沒資料 => 新增模式
    else {
      if (modalTitle) modalTitle.textContent = '新增設備';
      Model_id.readOnly = false;   // 編輯 → 鎖住

    }

    // 1. 處理設備型號 (Select)
    var modelEl = document.getElementById('DeviceModel');
    if (modelEl) modelEl.value = data.model;

    // 2. 處理設備序號 (Input)
    var idEl = document.getElementById('DeviceId');
    if (idEl) idEl.value = data.id;

    // 3. 處理狀態 (Select)
    var statusEl = document.getElementById('DeviceStatus');
    if (statusEl) statusEl.value = data.status;

    // 4. 處理個案 (如果有資料的話)
    var patEl = document.getElementById('PatId');
    if (patEl) patEl.value = data.pat_id || ""; // 防止出現 "null" 字樣



});


// 當 Modal 關閉時自動重置表單
document.getElementById('Modal_addDevice').addEventListener('hidden.bs.modal', function () {
    form.reset();
    msg.textContent = '';
    msg.className = 'message';
});


// 先宣告
const form = document.getElementById('registerForm');
const msg = document.getElementById('message');

form.addEventListener('submit', async function (e) {
    e.preventDefault();
    
    const id = document.getElementById('DeviceId').value;
    const status = document.getElementById('DeviceStatus').value;
    const model = document.getElementById('DeviceModel').value;
    const pat_id = document.getElementById('PatId').value;

    // 清除前一次樣式
    msg.classList.remove('error-message', 'success-message');
    

    const response = await fetch('/api/addDevice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, status, model, pat_id })
    });

    const result = await response.json();
    if (result.success) {
        msg.textContent = result.message;
        msg.classList.add('success-message');
        setTimeout(() => {
            location.reload();
        }, 500);
    } else {
        msg.textContent = result.message;
        msg.classList.add('error-message');
    }
});

document.getElementById("updateDeviceCountBtn").addEventListener("click", async function () {
  const btn = this;
  var input_data = btn.getAttribute('data-bs-study')
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> 更新中...';

  try {
    const response = await fetch("/api/update-device-count", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        study_id: input_data
      })
    });

    const result = await response.json();

    if (result.success) {
      alert("設備資料量已更新完成!!");
      setTimeout(() => {
            location.reload();
        }, 0);
    } else {
      alert("更新失敗：" + result.message);
    }
  } catch (error) {
    console.error(error);
    alert("呼叫 API 失敗");
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-gear"></i> 更新資料量';
  }
});

let currentDeviceList = [];
let preselectedDeviceIds = new Set();

const modalFhirDevice = document.getElementById("Modal_fhirDevice");

if (modalFhirDevice) {
    modalFhirDevice.addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
        const raw = button?.getAttribute("data-device-list");

        currentDeviceList = [];
        preselectedDeviceIds = new Set();

        if (raw) {
            try {
                currentDeviceList = JSON.parse(raw);

                currentDeviceList.forEach(item => {
                    if (item.id) {
                        preselectedDeviceIds.add(item.id);
                    }

                    if (item.device_id) {
                        preselectedDeviceIds.add(item.device_id);
                    }
                });

            } catch (e) {
                console.error("device list 格式錯誤", e);
            }
        }

        loadFhirDevices();
    });
}

function renderDeviceList(devices) {
    const itemDevice = document.getElementById("item_device");
    const countText = document.getElementById("deviceCountText");

    if (!itemDevice) return;

    if (!devices || devices.length === 0) {
        itemDevice.innerHTML = `
            <div class="col-span-full rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-400">
                目前沒有可選擇的設備
            </div>
        `;
        if (countText) countText.textContent = "共 0 台設備";
        return;
    }

    if (countText) countText.textContent = `共 ${devices.length} 台設備`;

    itemDevice.innerHTML = devices.map(device => {
        const rawId = device.device_id || "";
        const id = escapeHtml(rawId);

        const isChecked = preselectedDeviceIds.has(rawId);
        const checked = isChecked ? "checked" : "";
        const selectedClass = isChecked
            ? "border-blue-500 bg-blue-50 ring-1 ring-blue-200"
            : "";

        return `
            <label class="device-card ${selectedClass} flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs transition-all hover:border-blue-300 hover:bg-blue-50">
                <input
                    type="checkbox"
                    class="device-checkbox h-3.5 w-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    value="${id}"
                    data-device-text="${id}"
                    ${checked}>

                <span class="truncate font-medium text-slate-700" title="${id}">
                    ${id}
                </span>
            </label>
        `;
    }).join("");
}
let allFhirDevices = [];

function loadFhirDevices() {
    const itemDevice = document.getElementById("item_device");
    const countText = document.getElementById("deviceCountText");

    if (!itemDevice) return;

    itemDevice.innerHTML = `
        <div class="col-span-full rounded-xl border border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-400">
            <i class="bi bi-arrow-repeat"></i> 讀取設備中...
        </div>
    `;

    if (countText) countText.textContent = "讀取設備中...";

    fetch("/api/fhir/devices")
        .then(res => res.json())
        .then(result => {
            if (!result.success) {
                itemDevice.innerHTML = `
                    <div class="col-span-full rounded-xl border border-red-200 bg-red-50 p-8 text-center text-sm text-red-500">
                        ${result.message || "讀取設備失敗"}
                    </div>
                `;
                if (countText) countText.textContent = "讀取失敗";
                return;
            }

            allFhirDevices = result.data || [];
            renderDeviceList(allFhirDevices);
        })
        .catch(err => {
            console.error(err);
            itemDevice.innerHTML = `
                <div class="col-span-full rounded-xl border border-red-200 bg-red-50 p-8 text-center text-sm text-red-500">
                    讀取設備失敗
                </div>
            `;
            if (countText) countText.textContent = "讀取失敗";
        });
}

document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("deviceSearchInput");
    const clearBtn = document.getElementById("btnClearDeviceChecked");

    if (searchInput) {
        searchInput.addEventListener("input", function () {
            const keyword = this.value.trim().toLowerCase();

            const filtered = allFhirDevices.filter(device => {
                const text = `${device.device_id || ""} ${device.display || ""}`.toLowerCase();
                return text.includes(keyword);
            });

            renderDeviceList(filtered);
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", function () {
            document.querySelectorAll(".device-checkbox:checked").forEach(input => {
                input.checked = false;

                const card = input.closest(".device-card");
                if (card) {
                    card.classList.remove(
                        "border-blue-500",
                        "bg-blue-50",
                        "ring-1",
                        "ring-blue-200"
                    );
                }
            });
        });
    }
});

document.addEventListener("change", function (event) {
    if (!event.target.classList.contains("device-checkbox")) return;

    const checkbox = event.target;
    const deviceId = checkbox.value;

    // 同步記住目前勾選狀態
    if (checkbox.checked) {
        preselectedDeviceIds.add(deviceId);
    } else {
        preselectedDeviceIds.delete(deviceId);
    }

    const card = checkbox.closest(".device-card");
    if (!card) return;

    if (checkbox.checked) {
        card.classList.add("border-blue-500", "bg-blue-50", "ring-1", "ring-blue-200");
    } else {
        card.classList.remove("border-blue-500", "bg-blue-50", "ring-1", "ring-blue-200");
    }
});

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

const fhirDeviceForm = document.getElementById("fhirDeviceForm");

if (fhirDeviceForm) {
    fhirDeviceForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const selectedDevices = Array.from(
            document.querySelectorAll(".device-checkbox:checked")
        ).map(input => ({
            device_id: input.value,
            count: 0
        }));

        // if (selectedDevices.length === 0) {
        //     alert("請至少勾選一台設備");
        //     return;
        // }

        fetch("/api/project/save_devices", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                device_list: selectedDevices
            })
        })
        .then(res => res.json())
        .then(result => {
            if (result.success) {
                alert(result.message || "設備更新成功");

                const modal = bootstrap.Modal.getInstance(
                    document.getElementById("Modal_fhirDevice")
                );
                modal?.hide();

                window.location.reload();
            } else {
                alert(result.message || "設備更新失敗");
            }
        })
        .catch(err => {
            console.error(err);
            alert("設備更新失敗");
        });
    });
}