const BUS_STOP_NAME = "野間口";   // ← あなたのバス停
(function () {
  "use strict";

  /**
   * file:// で開いたときは FastAPI のオリジンを指定（CORS 許可が必要）。
   * 同一サーバーで配信する場合は '' のまま /bus に POST します。
   */
  var API_ORIGIN =
    window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
  var BUS_URL = API_ORIGIN + "/bus";

  var REFRESH_MS = 3000;

  var els = {
    loadingScreen: document.getElementById("loadingScreen"),
    main: document.getElementById("main"),
    cardList: document.getElementById("cardList"),
    empty: document.getElementById("empty"),
    refreshIndicator: document.getElementById("refreshIndicator"),
    errorToast: document.getElementById("errorToast"),
  };

  var hasLoadedOnce = false;
  var errorHideTimer = null;

  function showError(message) {
    els.errorToast.textContent = message;
    els.errorToast.hidden = false;
    if (errorHideTimer) clearTimeout(errorHideTimer);
    errorHideTimer = setTimeout(function () {
      els.errorToast.hidden = true;
    }, 5000);
  }

  function setRefreshing(on) {
    els.refreshIndicator.classList.toggle("is-active", on);
  }

  function delayLabel(delay) {
    var d = Number(delay);
    if (!Number.isFinite(d) || d <= 0) {
      return { text: "定刻", className: "is-ontime" };
    }
    return { text: d + "分遅れ", className: "is-late" };
  }

  function normalizeItem(raw) {
    return {
      to: raw && raw.to != null ? String(raw.to) : "—",
      route: raw && raw.route != null ? String(raw.route) : "—",
      eta: Number(raw && raw.eta),
      delay: Number(raw && raw.delay),
    };
  }

  function sortByEta(a, b) {
    var ea = Number.isFinite(a.eta) ? a.eta : Infinity;
    var eb = Number.isFinite(b.eta) ? b.eta : Infinity;
    return ea - eb;
  }

function render(buses) {
  els.cardList.innerHTML = "";
  els.empty.textContent = "表示するバスがありません";

  if (!buses.length) {
    els.empty.hidden = false;
    return;
  }
  els.empty.hidden = true;

  buses.forEach(function (bus) {
    var li = document.createElement("li");
    li.className = "card";

    // 系統
    var route = document.createElement("div");
    route.className = "card-route";
    route.textContent = bus.route + "系統";

    // 行先
    var to = document.createElement("h2");
    to.className = "card-to";
    to.textContent = `${bus.to}行き`;

    // 到着時間
    var eta = document.createElement("p");
    eta.className = "card-eta";
    var mins = Number.isFinite(bus.eta)
      ? Math.max(0, Math.round(bus.eta))
      : "—";

    if (mins <= 3) {
      eta.style.color = "red";
      eta.style.fontWeight = "bold";
    }
    if (mins === "—") {
      eta.textContent = `${BUS_STOP_NAME}の到着予測は取得できません`;
    } else {
      eta.textContent = `${BUS_STOP_NAME}にあと${mins}分で到着します`;
    }

    // 遅延表示（ここを明示的に書く）
    var delayEl = document.createElement("p");
    delayEl.className = "card-delay";

    if (bus.delay > 0) {
      delayEl.textContent = `（${bus.delay}分遅れ）`;
      delayEl.style.color = "red";
    } else {
      delayEl.textContent = "（定刻）";
      delayEl.style.color = "green";
    }

    // 追加
    li.appendChild(route);
    li.appendChild(to);
    li.appendChild(eta);
    li.appendChild(delayEl);

    els.cardList.appendChild(li);
  });
}

  async function fetchBuses() {
    if (!hasLoadedOnce) {
      els.loadingScreen.hidden = false;
    }
    setRefreshing(true);

    try {
      var res = await fetch(BUS_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });

      if (!res.ok) {
        throw new Error("HTTP " + res.status);
      }

      var data = await res.json();
      if (!Array.isArray(data)) {
        throw new Error("配列形式のレスポンスではありません");
      }

      var buses = data.map(normalizeItem).sort(sortByEta);
      render(buses);
      hasLoadedOnce = true;
      els.loadingScreen.hidden = true;
      els.main.hidden = false;
    } catch (e) {
      if (!hasLoadedOnce) {
        els.loadingScreen.hidden = true;
        els.main.hidden = false;
        render([]);
        els.empty.hidden = false;
        els.empty.textContent =
          "データを取得できませんでした。API の起動と CORS を確認してください。";
      }
      showError("更新に失敗しました");
    } finally {
      setRefreshing(false);
    }
  }

  fetchBuses();
  setInterval(fetchBuses, REFRESH_MS);
})();
