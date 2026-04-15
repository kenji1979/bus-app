const CONFIG = {
  useMock: false,
  apiUrl: "/bus",
  pollIntervalMs: 30000, // 30秒更新
};

async function fetchBusData() {
  const contentDiv = document.getElementById("bus-content");
  
  try {
    // GETリクエストでAPIを叩く
    const response = await fetch(CONFIG.apiUrl);
    
    if (!response.ok) {
      throw new Error("APIレスポンスエラー");
    }
    
    const data = await response.json();

    // バスがない場合
    if (data.length === 0) {
      contentDiv.innerHTML = `<p class="message">現在、到着予定のバスはありません</p>`;
      return;
    }

    // データがある場合（1件のみ取得）
    const bus = data[0];
    
    // 遅延がある場合のみ遅延表示のHTMLを作成
    const delayHtml = bus.delay > 0 
      ? `<p class="delay">（${bus.delay}分遅れ）</p>` 
      : "";

    // 画面の書き換え
    contentDiv.innerHTML = `
      <p class="route">${bus.route}（${bus.to}行き）</p>
      <p class="eta">あと<span class="eta-time">${bus.eta}</span>分で到着</p>
      ${delayHtml}
    `;

  } catch (error) {
    console.error("データ取得エラー:", error);
    contentDiv.innerHTML = `<p class="error">データ取得に失敗しました</p>`;
  }
}

// 画面表示時に最初の1回を実行
fetchBusData();

// 30秒ごとに自動更新
setInterval(fetchBusData, CONFIG.pollIntervalMs);