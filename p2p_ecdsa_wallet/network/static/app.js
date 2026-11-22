// Giao diện ví: chỉ gọi API của chính node đang phục vụ trang này.
"use strict";

const $ = (id) => document.getElementById(id);
const REFRESH_MS = 3000;
const PEER_REFRESH_MS = 10000;

let myAddress = "";
let peerInfo = [];          // [{url, online, address}]
let originalSignedTx = null; // Bản giao dịch vừa ký, để khôi phục sau khi sửa
let lastChainTip = "";
const openBlocks = new Set();

// ------------------------------------------------------------------ Tiện ích
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function short(value, n = 10) {
  if (!value) return "";
  return value.length > n ? `${value.slice(0, n)}…` : value;
}

function nameOf(address) {
  if (address === "SYSTEM") return "SYSTEM (thưởng)";
  if (address === myAddress) return "Ví của node này";
  const peer = peerInfo.find((p) => p.address === address);
  if (peer) return `Node :${peer.url.split(":").pop()}`;
  return short(address, 12);
}

function formatAmount(n) {
  return Number(n).toLocaleString("vi-VN", { maximumFractionDigits: 8 });
}

async function api(path, options = {}) {
  const init = { method: options.method || "GET", headers: {} };
  if (options.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = typeof options.body === "string" ? options.body : JSON.stringify(options.body);
  }
  const resp = await fetch(path, init);
  let data = {};
  try { data = await resp.json(); } catch (_) { /* không phải JSON */ }
  return { ok: resp.ok, status: resp.status, data };
}

function showResult(id, kind, html) {
  const box = $(id);
  box.hidden = false;
  box.className = `result ${kind}`;
  box.innerHTML = html;
}

async function withBusy(button, fn) {
  button.disabled = true;
  try { await fn(); } finally { button.disabled = false; }
}

// ------------------------------------------------------------------ Hiển thị
function renderStatus(s) {
  myAddress = s.address;
  document.title = `Ví Full Node :${s.port}`;
  $("node-port").textContent = `:${s.port}`;
  $("stat-length").textContent = s.chain_length;
  $("stat-mempool").textContent = s.mempool_size;
  $("stat-difficulty").textContent = s.difficulty;
  $("wallet-balance").textContent = formatAmount(s.balance);
  $("wallet-address").textContent = s.address;
  $("wallet-nonce").textContent = s.next_nonce;
}

function renderPeers() {
  const list = $("peer-list");
  if (!peerInfo.length) {
    list.innerHTML = '<li class="muted">Chưa có peer nào.</li>';
  } else {
    list.innerHTML = peerInfo.map((p) => `
      <li>
        <span class="dot ${p.online ? "on" : "off"}"></span>
        <span><strong>${escapeHtml(p.url)}</strong><br>
          <small class="muted">${p.online ? `Ví: ${escapeHtml(short(p.address, 20))}` : "Ngoại tuyến"}</small>
        </span>
      </li>`).join("");
  }

  // Cập nhật danh sách người nhận nhưng giữ lựa chọn hiện tại
  const options = peerInfo
    .filter((p) => p.online && p.address)
    .map((p) => ({ value: p.address, label: `Node :${p.url.split(":").pop()} — ${short(p.address, 14)}` }));
  for (const id of ["send-recipient-select", "tamper-recipient-select"]) {
    const select = $(id);
    const current = select.value;
    const placeholder = id === "send-recipient-select" ? "— Chọn ví của peer —" : "— Người nhận —";
    select.innerHTML = `<option value="">${placeholder}</option>` + options
      .map((o) => `<option value="${escapeHtml(o.value)}">${escapeHtml(o.label)}</option>`).join("");
    if (options.some((o) => o.value === current)) select.value = current;
    else if (id === "tamper-recipient-select" && options.length) select.value = options[0].value;
  }
}

function renderLogs(logs) {
  $("log-list").innerHTML = logs.slice().reverse().map((l) => `
    <li class="${escapeHtml(l.kind)}"><span class="log-time">${escapeHtml(l.time)}</span>${escapeHtml(l.message)}</li>
  `).join("") || '<li class="muted">Chưa có sự kiện.</li>';
}

function txRow(tx) {
  return `<tr>
    <td title="${escapeHtml(tx.sender)}">${escapeHtml(nameOf(tx.sender))}</td>
    <td title="${escapeHtml(tx.recipient)}">${escapeHtml(nameOf(tx.recipient))}</td>
    <td>${formatAmount(tx.amount)}</td>
    <td>${escapeHtml(tx.nonce)}</td>
    <td><code title="${escapeHtml(tx.signature || "")}">${escapeHtml(short(tx.signature || "—", 16))}</code></td>
  </tr>`;
}

function renderMempool(txs) {
  $("mempool-body").innerHTML = txs.length
    ? txs.map(txRow).join("")
    : '<tr><td colspan="5" class="muted">Mempool trống.</td></tr>';
}

function renderChain(chain) {
  const tip = chain.length ? chain[chain.length - 1].block_hash : "";
  if (tip === lastChainTip) return; // Không đổi thì không vẽ lại (giữ trạng thái mở/đóng)
  lastChainTip = tip;

  $("chain-list").innerHTML = chain.slice().reverse().map((b) => {
    const txs = b.transactions || [];
    const title = b.index === 0 ? "Khối #0 — Genesis" : `Khối #${b.index}`;
    return `
      <details class="block" data-hash="${escapeHtml(b.block_hash)}" ${openBlocks.has(b.block_hash) ? "open" : ""}>
        <summary>${title} · ${txs.length} giao dịch · <code>${escapeHtml(short(b.block_hash, 18))}</code></summary>
        <dl class="block-meta">
          <dt>Hash</dt><dd><code>${escapeHtml(b.block_hash)}</code></dd>
          <dt>Previous hash</dt><dd><code>${escapeHtml(b.previous_hash)}</code></dd>
          <dt>Nonce (PoW)</dt><dd>${escapeHtml(b.nonce)}</dd>
          <dt>Thời gian</dt><dd>${b.timestamp ? new Date(b.timestamp * 1000).toLocaleString("vi-VN") : "0 (cố định)"}</dd>
        </dl>
        ${txs.length ? `<div class="table-wrap"><table>
          <thead><tr><th>Từ</th><th>Đến</th><th>Số tiền</th><th>Nonce</th><th>Chữ ký</th></tr></thead>
          <tbody>${txs.map(txRow).join("")}</tbody></table></div>` : ""}
      </details>`;
  }).join("");

  document.querySelectorAll("#chain-list details").forEach((el) => {
    el.addEventListener("toggle", () => {
      if (el.open) openBlocks.add(el.dataset.hash); else openBlocks.delete(el.dataset.hash);
    });
  });
}

// ------------------------------------------------------------------ Làm mới dữ liệu
async function refresh() {
  try {
    const [status, mempool, chain, logs] = await Promise.all([
      api("/status"), api("/mempool"), api("/chain"), api("/logs"),
    ]);
    renderStatus(status.data);
    renderMempool(mempool.data.transactions || []);
    renderChain(chain.data.chain || []);
    renderLogs(logs.data.logs || []);
  } catch (_) {
    $("stat-length").textContent = "mất kết nối";
  }
}

async function refreshPeers() {
  try {
    const { data } = await api("/nodes/addresses");
    peerInfo = data.peers || [];
    renderPeers();
    lastChainTip = ""; // Vẽ lại chuỗi để cập nhật tên người gửi/nhận
  } catch (_) { /* node tạm thời không phản hồi */ }
}

// ------------------------------------------------------------------ Thao tác
$("btn-copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(myAddress);
    $("btn-copy").textContent = "Đã chép";
  } catch (_) {
    $("btn-copy").textContent = "Không chép được";
  }
  setTimeout(() => { $("btn-copy").textContent = "Sao chép"; }, 1500);
});

$("btn-mine").addEventListener("click", (e) => withBusy(e.target, async () => {
  showResult("action-result", "info", "Đang giải bài toán Proof of Work…");
  const { ok, data } = await api("/mine", { method: "POST" });
  if (ok) {
    const b = data.block;
    showResult("action-result", "ok",
      `Đào khối #${b.index} thành công sau ${data.mining_time}s · nonce = ${b.nonce}<br><code>${escapeHtml(b.block_hash)}</code>`);
  } else {
    showResult("action-result", "bad", escapeHtml(data.error || "Đào khối thất bại"));
  }
  await refresh();
}));

$("btn-sync").addEventListener("click", (e) => withBusy(e.target, async () => {
  const { data } = await api("/nodes/sync", { method: "POST" });
  showResult("action-result", "info", `${escapeHtml(data.message)} (độ dài ${data.length})`);
  await refresh();
}));

$("form-register").addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = $("register-url").value.trim();
  if (!url) return;
  await api("/nodes/register", { method: "POST", body: { peers: [url] } });
  $("register-url").value = "";
  await refreshPeers();
});

$("form-send").addEventListener("submit", (e) => {
  e.preventDefault();
  withBusy(e.submitter || e.target, async () => {
    const recipient = $("send-recipient").value.trim() || $("send-recipient-select").value;
    if (!recipient) {
      showResult("send-result", "bad", "Hãy chọn hoặc nhập địa chỉ người nhận.");
      return;
    }
    const { ok, data } = await api("/transactions/send", {
      method: "POST",
      body: { recipient, amount: Number($("send-amount").value) },
    });
    if (ok) {
      const tx = data.transaction;
      showResult("send-result", "ok",
        `Đã ký và phát tán: ${formatAmount(tx.amount)} → ${escapeHtml(nameOf(tx.recipient))} (nonce ${tx.nonce})<br>
         Chữ ký: <code>${escapeHtml(short(tx.signature, 40))}</code>`);
      $("send-recipient").value = "";
    } else {
      showResult("send-result", "bad", `Bị từ chối: ${escapeHtml(data.error)}`);
    }
    await refresh();
  });
});

// --- Kịch bản giả mạo
function readTamperJson() {
  try {
    return JSON.parse($("tamper-json").value);
  } catch (_) {
    showResult("tamper-result", "bad", "JSON không hợp lệ.");
    return null;
  }
}

function writeTamperJson(tx) {
  $("tamper-json").value = JSON.stringify(tx, null, 2);
}

$("form-sign").addEventListener("submit", (e) => {
  e.preventDefault();
  withBusy(e.submitter || e.target, async () => {
    const recipient = $("tamper-recipient-select").value || myAddress;
    const { ok, data } = await api("/transactions/sign", {
      method: "POST",
      body: { recipient, amount: Number($("tamper-amount").value) },
    });
    if (!ok) {
      showResult("tamper-result", "bad", escapeHtml(data.error));
      return;
    }
    originalSignedTx = data.transaction;
    writeTamperJson(originalSignedTx);
    showResult("tamper-result", "info",
      `Đã ký bằng Private Key của node. Mã băm SHA-256 được ký: <code>${escapeHtml(data.hash)}</code><br>
       Thử sửa dữ liệu (bước 2) hoặc gửi nguyên bản (bước 3) để so sánh kết quả.`);
  });
});

$("btn-tamper-amount").addEventListener("click", () => {
  const tx = readTamperJson();
  if (!tx) return;
  tx.amount = Number(tx.amount) + 1;
  writeTamperJson(tx);
  showResult("tamper-result", "info", `Đã sửa số tiền thành ${formatAmount(tx.amount)} nhưng giữ nguyên chữ ký cũ.`);
});

$("btn-tamper-recipient").addEventListener("click", () => {
  const tx = readTamperJson();
  if (!tx || !tx.recipient) return;
  const last = tx.recipient.slice(-1);
  tx.recipient = tx.recipient.slice(0, -1) + (last === "0" ? "1" : "0");
  writeTamperJson(tx);
  showResult("tamper-result", "info", "Đã sửa 1 ký tự cuối của địa chỉ người nhận nhưng giữ nguyên chữ ký cũ.");
});

$("btn-tamper-reset").addEventListener("click", () => {
  if (!originalSignedTx) return;
  writeTamperJson(originalSignedTx);
  showResult("tamper-result", "info", "Đã khôi phục giao dịch gốc (chưa bị sửa).");
});

$("btn-tamper-send").addEventListener("click", (e) => withBusy(e.target, async () => {
  if (!$("tamper-json").value.trim()) {
    showResult("tamper-result", "bad", "Hãy ký một giao dịch trước (bước 1).");
    return;
  }
  const tx = readTamperJson();
  if (!tx) return;
  const { ok, status, data } = await api("/transactions/receive", { method: "POST", body: tx });
  if (ok) {
    showResult("tamper-result", "ok", `HTTP ${status} — ${escapeHtml(data.message)}`);
  } else {
    showResult("tamper-result", "bad", `HTTP ${status} — ${escapeHtml(data.error)}`);
  }
  await refresh();
}));

// ------------------------------------------------------------------ Khởi động
refresh().then(refreshPeers);
setInterval(refresh, REFRESH_MS);
setInterval(refreshPeers, PEER_REFRESH_MS);
