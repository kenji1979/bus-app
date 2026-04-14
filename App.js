const CONFIG = {
  useMock: false,
  apiUrl: "/bus",
  pollIntervalMs: 30000,
};

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildCardHtml(item) {
  const route = item.route != null ? String(item.route) : "未定";
  const heading = item.heading != null ? String(item.heading) : String(item.to || "");
  const fromStop = item.from_stop != null ? String(item.from_stop) : "";
  const delay = Number(item.delay) || 0;
  const eta = item.eta;

  const routeLine = `${escapeHtml(route)}（${escapeHtml(heading)}行き）`;

  if (eta == null || eta === "") {
    return `
      <article class="bus-card bus-card--empty">
        <p class="bus-card__route">${routeLine}</p>
        <p class="bus-card__empty-msg">現在、到着予定のバスはありません</p>
      </article>
    `;
  }

  const delayHtml =
    delay > 0
      ? `<p class="bus-card__delay">（${escapeHtml(delay)}分遅れ）</p>`
      : "";

  return `
    <article class="bus-card">
      <p class="bus-card__route">${routeLine}</p>
      <p class="bus-card__eta">
        <span class="bus-card__from-label">${escapeHtml(fromStop)}まで</span>
        あと<span class="bus-card__eta-num">${escapeHtml(eta)}</span>分で到着
      </p>
      ${delayHtml}
    </article>
  `;
}

async function fetchBusData() {
  const listEl = document.getElementById("bus-list");

  try {
    const response = await fetch(CONFIG.apiUrl);
    if (!response.ok) {
      throw new Error("APIレスポンスエラー");
    }
    const data = await response.json();

    if (!Array.isArray(data)) {
      listEl.innerHTML = `<p class="error">データ形式が不正です</p>`;
      return;
    }

    if (data.length === 0) {
      listEl.innerHTML = `<p class="message">現在、到着予定のバスはありません</p>`;
      return;
    }

    listEl.innerHTML = data.map(buildCardHtml).join("");
  } catch (error) {
    console.error("データ取得エラー:", error);
    listEl.innerHTML = `<p class="error">データ取得に失敗しました</p>`;
  }
}

fetchBusData();
setInterval(fetchBusData, CONFIG.pollIntervalMs);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .catch((err) => console.warn("Service Worker の登録に失敗:", err));
  });
}
