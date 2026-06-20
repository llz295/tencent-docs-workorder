/* 网页版 UI — 与桌面 EXE 布局与功能对齐 */
const state = {
  menu: [],
  configs: {},
  taskRunning: false,
  lastOutput: null,
  calPickStart: null,
  calPickEnd: null,
  calRanges: [],
};

const WEEK = ["一", "二", "三", "四", "五", "六", "日"];

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

function setStatus(title, detail = "") {
  document.getElementById("status-text").textContent = title;
  document.getElementById("status-detail").textContent = detail;
  const dot = document.getElementById("status-dot");
  dot.classList.toggle("busy", state.taskRunning);
}

function appendLog(line) {
  const box = document.getElementById("log-box");
  if (!box) return;
  box.textContent += line + "\n";
  box.scrollTop = box.scrollHeight;
}

function connectLogStream() {
  const es = new EventSource("/api/logs/stream");
  es.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data.line) appendLog(data.line);
      if (data.status) {
        state.taskRunning = data.status.running;
        setStatus(data.status.status, data.status.detail || "");
        if (data.status.last_output) {
          state.lastOutput = data.status.last_output;
          const el = document.getElementById("result-path");
          if (el) el.textContent = data.status.last_output;
        }
        updateTaskButtons();
      }
    } catch (_) {}
  };
  es.onerror = () => setTimeout(connectLogStream, 3000);
}

function updateTaskButtons() {
  ["btn-dl", "btn-sum", "btn-both"].forEach((id) => {
    const b = document.getElementById(id);
    if (b) b.disabled = state.taskRunning;
  });
}

function buildNav() {
  const nav = document.getElementById("sidebar-nav");
  nav.innerHTML = "";
  state.menu.forEach((l1) => {
    const gt = document.createElement("div");
    gt.className = "nav-group-title";
    gt.textContent = l1.title;
    nav.appendChild(gt);
    l1.children.forEach((l2) => {
      const btn = document.createElement("button");
      btn.className = "nav-btn";
      btn.dataset.key = l2.key;
      btn.textContent = "  " + l2.title;
      btn.onclick = () => selectMenu(l2.key);
      nav.appendChild(btn);
    });
  });
}

function selectMenu(key) {
  const l1 = state.menu.find((m) => m.children.some((c) => c.key === key));
  const l2 = l1?.children.find((c) => c.key === key);
  if (!l2) return;

  document.querySelectorAll(".nav-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.key === key);
  });
  document.getElementById("page-title").textContent = l2.title;
  document.getElementById("breadcrumb").textContent =
    `${l1.title} / ${l2.title} / ${(l2.sections || []).join(" · ")}`;

  document.querySelectorAll(".panel").forEach((p) => {
    p.classList.toggle("active", p.dataset.panel === l2.panel);
  });
}

function section(title, inner) {
  return `<div class="section"><h4>${title}</h4>${inner}</div>`;
}

function formRow(label, input) {
  return `<div class="form-row"><label>${label}</label>${input}</div>`;
}

function buildPanels() {
  const root = document.getElementById("panels");
  root.innerHTML = `
    <div class="panel active" data-panel="dashboard">
      <div class="card-row">
        <div class="card">
          <h3>批量下载</h3>
          <p>从腾讯文档拉取全部录音师工单到本地目录。失败自动重试直至成功。</p>
          <button class="btn btn-primary" id="btn-dl">开始下载</button>
        </div>
        <div class="card">
          <h3>工单汇总</h3>
          <p>读取本地 Excel，生成主表 / 结算汇总 / 终表，可按时间段加分段主表。</p>
          <button class="btn btn-primary" id="btn-sum">开始汇总</button>
        </div>
        <div class="card">
          <h3>下载并汇总</h3>
          <p>先完成全部下载，再按汇总配置进入汇总流程。</p>
          <button class="btn btn-primary" id="btn-both">一键执行</button>
        </div>
      </div>
      <p class="hint">左侧菜单可修改并发、路径、弹窗行为等；运行日志见「系统 → 运行日志」。</p>
    </div>

    <div class="panel" data-panel="download">
      <div class="config-banner" id="dl-cfg-path"></div>
      ${section("表单 · 并发数量", formRow("同时下载文档数", '<input type="range" id="dl-concurrency" min="1" max="8" /><span id="dl-concurrency-val">5</span>'))}
      ${section("表单 · 失败重试", formRow("重试轮次间隔（秒）", '<input type="range" id="dl-retry" min="1" max="30" /><span id="dl-retry-val">3</span>'))}
      <div class="save-bar"><button class="btn btn-primary" id="save-dl">保存本页配置</button></div>
    </div>

    <div class="panel" data-panel="download_browser">
      <div class="config-banner" id="br-cfg-path"></div>
      ${section("表单 · 运行模式", formRow("无头模式（后台下载）", '<label class="switch"><input type="checkbox" id="br-headless" />启用</label>'))}
      ${section("表单 · 浏览器通道", formRow("通道（推荐 chrome）", '<input type="text" id="br-channel" placeholder="留空=Playwright Chromium" />'))}
      <p class="hint">填 chrome = 本机 Google Chrome；留空 = Playwright 自带 Chromium。</p>
      <div class="save-bar"><button class="btn btn-primary" id="save-br">保存本页配置</button></div>
    </div>

    <div class="panel" data-panel="summarize">
      <div class="config-banner" id="sum-cfg-path"></div>
      ${section("表单 · 弹窗与确认", [
        formRow("汇总前确认", '<label class="switch"><input type="checkbox" id="sum-prompt" />启用</label>'),
        formRow("下载后自动汇总", '<label class="switch"><input type="checkbox" id="sum-auto" />启用</label>'),
        formRow("汇总时选择工作表", '<label class="switch"><input type="checkbox" id="sum-sheet-prompt" />启用</label>'),
        formRow("汇总时弹出日历", '<label class="switch"><input type="checkbox" id="sum-date-prompt" />启用</label>'),
      ].join(""))}
      <div class="save-bar"><button class="btn btn-primary" id="save-sum">保存本页配置</button></div>
    </div>

    <div class="panel" data-panel="summarize_output">
      ${section("表单 · 文件名", formRow("输出文件名前缀", '<input type="text" id="sum-prefix" />'))}
      ${section("表单 · 固定工作表", [
        formRow("固定 sheet 名（留空则交互选择）", '<input type="text" id="sum-sheet-fixed" />'),
        formRow("样例文件关键字", '<input type="text" id="sum-sample-kw" />'),
      ].join(""))}
      <div class="save-bar"><button class="btn btn-primary" id="save-sum-out">保存本页配置</button></div>
    </div>

    <div class="panel" data-panel="pricing">
      <p class="hint">编辑 voice_actor_config.json（化名映射 + 单价）</p>
      <textarea class="json-editor" id="pricing-json"></textarea>
      <div class="save-bar"><button class="btn btn-primary" id="save-pricing">保存价格表</button></div>
    </div>

    <div class="panel" data-panel="paths">
      ${section("表单 · 目录", [
        formRow("工单下载目录", '<input type="text" id="path-dl" />'),
        formRow("汇总输出目录", '<input type="text" id="path-out" />'),
      ].join(""))}
      <div class="save-bar"><button class="btn btn-primary" id="save-paths">保存本页配置</button></div>
    </div>

    <div class="panel" data-panel="paths_login">
      ${section("表单 · 探测表格 URL", formRow("登录探测用表格链接", '<input type="text" id="path-probe" style="max-width:560px" />'))}
      ${section("表单 · 探针等待", formRow("探针下载超时（秒，无重试）", '<input type="number" id="path-probe-wait" min="5" max="120" value="20" />'))}
      ${section("表单 · 扫码超时", formRow("最长等待登录（秒）", '<input type="number" id="path-login-to" min="60" max="600" />'))}
      ${section("表单 · 启动方式", [
        formRow("界面模式", '<select id="path-ui-mode"><option value="ask">每次询问</option><option value="desktop">桌面程序</option><option value="web">网页版</option></select>'),
        formRow("网页版绑定", '<input type="text" id="path-web-host" placeholder="0.0.0.0" title="0.0.0.0=局域网可访问" style="max-width:160px" /> : <input type="number" id="path-web-port" min="1024" max="65535" style="max-width:80px" />'),
        '<p class="hint">0.0.0.0 允许局域网访问；127.0.0.1 仅本机。其他电脑用 http://服务器局域网IP:端口</p>',
      ].join(""))}
      <div class="save-bar"><button class="btn btn-primary" id="save-paths-login">保存本页配置</button></div>
    </div>

    <div class="panel" data-panel="docs">
      <p class="hint">录音师腾讯文档 URL 列表（doc_urls.json）</p>
      <textarea class="json-editor" id="docs-json" style="height:360px"></textarea>
      <div class="save-bar"><button class="btn btn-primary" id="save-docs">保存到文件</button></div>
    </div>

    <div class="panel" data-panel="advanced">
      ${section("表单 · 超时", [
        formRow("编辑器就绪（毫秒）", '<input type="number" id="adv-editor" />'),
        formRow("菜单就绪（毫秒）", '<input type="number" id="adv-menu" />'),
        formRow("表格加载等待（毫秒）", '<input type="number" id="adv-sheet" />'),
      ].join(""))}
      <div class="save-bar"><button class="btn btn-primary" id="save-adv">保存本页配置</button></div>
    </div>

    <div class="panel" data-panel="config_files">
      <div id="cfg-file-list"></div>
    </div>

    <div class="panel" data-panel="log">
      <div class="result-banner">
        <strong>最近一次汇总输出</strong>
        <div class="path" id="result-path">（汇总完成后将显示完整路径）</div>
      </div>
      ${section("实时日志", '<div class="log-box" id="log-box"></div><button class="btn" id="clear-log" style="margin-top:8px">清空日志</button>')}
    </div>
  `;
}

function bindSliders() {
  const pairs = [
    ["dl-concurrency", "dl-concurrency-val"],
    ["dl-retry", "dl-retry-val"],
  ];
  pairs.forEach(([id, vid]) => {
    const el = document.getElementById(id);
    const val = document.getElementById(vid);
    if (!el || !val) return;
    el.oninput = () => { val.textContent = el.value; };
  });
}

async function loadConfigs() {
  state.configs.app = await api("/api/config/app");
  state.configs.download = await api("/api/config/download");
  state.configs.summarize = await api("/api/config/summarize");
  state.configs.pricing = await api("/api/config/pricing");
  state.configs.docs = await api("/api/config/docs");
  applyConfigToForm();
}

function applyConfigToForm() {
  const a = state.configs.app;
  const d = state.configs.download;
  const s = state.configs.summarize;

  const set = (id, v) => { const e = document.getElementById(id); if (e) e.value = v; };
  const setChk = (id, v) => { const e = document.getElementById(id); if (e) e.checked = !!v; };

  set("dl-concurrency", d.concurrency || 5);
  document.getElementById("dl-concurrency-val").textContent = d.concurrency || 5;
  set("dl-retry", a.retry_round_delay_sec || 3);
  document.getElementById("dl-retry-val").textContent = a.retry_round_delay_sec || 3;

  setChk("br-headless", a.headless);
  set("br-channel", a.browser_channel || "");

  setChk("sum-prompt", s.prompt_before_summarize);
  setChk("sum-auto", s.auto_summarize_after_download);
  setChk("sum-sheet-prompt", s.prompt_for_sheet_name);
  setChk("sum-date-prompt", s.prompt_for_date_ranges);
  set("sum-prefix", s.output_filename_prefix || "");
  set("sum-sheet-fixed", s.sheet_name || "");
  set("sum-sample-kw", s.sample_file_keyword || "");

  set("path-dl", a.download_dir || "");
  set("path-out", a.summarize_output_dir || "");
  set("path-probe", a.probe_sheet_url || "");
  set("path-probe-wait", a.probe_wait_sec || 20);
  set("path-login-to", a.login_wait_timeout_sec || 300);
  set("path-ui-mode", a.ui_mode || "ask");
  set("path-web-host", a.web_host || "0.0.0.0");
  set("path-web-port", a.web_port || 8765);

  set("adv-editor", a.editor_ready_timeout_ms);
  set("adv-menu", a.menu_ready_timeout_ms);
  set("adv-sheet", a.sheet_load_wait_ms);

  document.getElementById("pricing-json").value = JSON.stringify(state.configs.pricing, null, 2);
  document.getElementById("docs-json").value = JSON.stringify(state.configs.docs, null, 2);

  if (document.getElementById("dl-cfg-path")) {
    document.getElementById("dl-cfg-path").textContent = "配置文件: data/download_config.json · data/app_config.json";
    document.getElementById("br-cfg-path").textContent = "配置文件: data/app_config.json";
    document.getElementById("sum-cfg-path").textContent = "配置文件: data/summarize_config.json";
  }
}

async function saveApp(partial) {
  const data = { ...state.configs.app, ...partial };
  await api("/api/config/app", { method: "POST", body: JSON.stringify({ data }) });
  state.configs.app = data;
  alert("配置已保存");
}

function bindSaveHandlers() {
  document.getElementById("save-dl").onclick = async () => {
    await api("/api/config/download", {
      method: "POST",
      body: JSON.stringify({ data: { concurrency: +document.getElementById("dl-concurrency").value } }),
    });
    await saveApp({ retry_round_delay_sec: +document.getElementById("dl-retry").value });
  };

  document.getElementById("save-br").onclick = () => saveApp({
    headless: document.getElementById("br-headless").checked,
    browser_channel: document.getElementById("br-channel").value.trim() || null,
  });

  const saveSumCfg = async () => {
    const data = {
      ...state.configs.summarize,
      prompt_before_summarize: document.getElementById("sum-prompt").checked,
      auto_summarize_after_download: document.getElementById("sum-auto").checked,
      prompt_for_sheet_name: document.getElementById("sum-sheet-prompt").checked,
      prompt_for_date_ranges: document.getElementById("sum-date-prompt").checked,
    };
    await api("/api/config/summarize", { method: "POST", body: JSON.stringify({ data }) });
    state.configs.summarize = data;
    alert("配置已保存");
  };
  document.getElementById("save-sum").onclick = saveSumCfg;

  document.getElementById("save-sum-out").onclick = async () => {
    const data = {
      ...state.configs.summarize,
      output_filename_prefix: document.getElementById("sum-prefix").value,
      sheet_name: document.getElementById("sum-sheet-fixed").value,
      sample_file_keyword: document.getElementById("sum-sample-kw").value,
    };
    await api("/api/config/summarize", { method: "POST", body: JSON.stringify({ data }) });
    state.configs.summarize = data;
    alert("配置已保存");
  };

  document.getElementById("save-pricing").onclick = async () => {
    const data = JSON.parse(document.getElementById("pricing-json").value);
    await api("/api/config/pricing", { method: "POST", body: JSON.stringify({ data }) });
    alert("价格表已保存");
  };

  document.getElementById("save-paths").onclick = () => saveApp({
    download_dir: document.getElementById("path-dl").value,
    summarize_output_dir: document.getElementById("path-out").value,
  });

  document.getElementById("save-paths-login").onclick = () => saveApp({
    probe_sheet_url: document.getElementById("path-probe").value,
    probe_wait_sec: Math.max(5, Math.min(120, +document.getElementById("path-probe-wait").value || 20)),
    login_wait_timeout_sec: +document.getElementById("path-login-to").value,
    ui_mode: document.getElementById("path-ui-mode").value,
    web_host: document.getElementById("path-web-host").value.trim() || "0.0.0.0",
    web_port: +document.getElementById("path-web-port").value || 8765,
  });

  document.getElementById("save-adv").onclick = () => saveApp({
    editor_ready_timeout_ms: +document.getElementById("adv-editor").value,
    menu_ready_timeout_ms: +document.getElementById("adv-menu").value,
    sheet_load_wait_ms: +document.getElementById("adv-sheet").value,
  });

  document.getElementById("save-docs").onclick = async () => {
    const data = JSON.parse(document.getElementById("docs-json").value);
    await api("/api/config/docs", { method: "POST", body: JSON.stringify({ data }) });
    alert("文档列表已保存");
  };

  document.getElementById("clear-log").onclick = () => {
    document.getElementById("log-box").textContent = "";
  };
}

function showModal(id) {
  return new Promise((resolve) => {
    const overlay = document.getElementById(id);
    overlay.classList.add("open");
    const okBtn = overlay.querySelector("[id$='-ok']");
    const cancelBtn = overlay.querySelector("[id$='-cancel']");
    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);
    function cleanup(result) {
      overlay.classList.remove("open");
      okBtn?.removeEventListener("click", onOk);
      cancelBtn?.removeEventListener("click", onCancel);
      resolve(result);
    }
    okBtn?.addEventListener("click", onOk);
    cancelBtn?.addEventListener("click", onCancel);
  });
}

function goToLogPanel() {
  for (const l1 of state.menu) {
    for (const l2 of l1.children) {
      if (l2.panel === "log") {
        selectMenu(l2.key);
        return;
      }
    }
  }
}

function toIsoLocal(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function buildCalendar() {
  const today = new Date();
  const curY = today.getFullYear(), curM = today.getMonth();
  const prev = new Date(curY, curM - 1, 1);
  const prevY = prev.getFullYear(), prevM = prev.getMonth();

  const container = document.getElementById("cal-container");
  container.innerHTML = "";
  [ { y: prevY, m: prevM, title: "上月（整月）" }, { y: curY, m: curM, title: "本月（整月）" } ].forEach(({ y, m, title }) => {
    const wrap = document.createElement("div");
    wrap.className = "cal-month";
    wrap.innerHTML = `<h5>${title}</h5>`;
    const table = document.createElement("table");
    table.className = "cal-table";
    const head = document.createElement("tr");
    WEEK.forEach((w) => { const th = document.createElement("th"); th.textContent = w; head.appendChild(th); });
    table.appendChild(head);

    const first = new Date(y, m, 1);
    const start = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(y, m + 1, 0).getDate();
    let day = 1;
    for (let r = 0; r < 6; r++) {
      const tr = document.createElement("tr");
      let rowHasDay = false;
      for (let c = 0; c < 7; c++) {
        const td = document.createElement("td");
        if ((r === 0 && c < start) || day > daysInMonth) {
          td.textContent = "";
        } else {
          const d = new Date(y, m, day);
          const btn = document.createElement("button");
          btn.className = "cal-day";
          btn.textContent = day;
          btn.dataset.iso = toIsoLocal(d);
          if (d.getDay() === 5) btn.classList.add("fri");
          if (m === prevM && day >= 25) btn.classList.add("ref");
          if (d.toDateString() === today.toDateString()) btn.classList.add("today");
          btn.onclick = () => onCalDayClick(btn.dataset.iso);
          td.appendChild(btn);
          day++;
          rowHasDay = true;
        }
        tr.appendChild(td);
      }
      if (!rowHasDay) break;
      table.appendChild(tr);
      if (day > daysInMonth) break;
    }
    wrap.appendChild(table);
    container.appendChild(wrap);
  });
  refreshCalHighlights();
}

function onCalDayClick(iso) {
  if (!state.calPickStart) {
    state.calPickStart = iso;
    state.calPickEnd = null;
  } else if (!state.calPickEnd) {
    if (iso < state.calPickStart) {
      state.calPickEnd = state.calPickStart;
      state.calPickStart = iso;
    } else {
      state.calPickEnd = iso;
    }
  } else {
    state.calPickStart = iso;
    state.calPickEnd = null;
  }
  refreshCalHighlights();
}

function refreshCalHighlights() {
  document.querySelectorAll(".cal-day").forEach((btn) => {
    btn.classList.remove("sel", "in-range");
    const iso = btn.dataset.iso;
    if (!iso) return;
    if (iso === state.calPickStart || iso === state.calPickEnd) btn.classList.add("sel");
    if (state.calPickStart && state.calPickEnd && iso >= state.calPickStart && iso <= state.calPickEnd) {
      btn.classList.add("in-range");
    }
  });
  const lbl = document.getElementById("cal-pick-label");
  if (state.calPickStart && state.calPickEnd) {
    lbl.textContent = `当前选择: ${state.calPickStart} ~ ${state.calPickEnd}（闭区间）`;
  } else if (state.calPickStart) {
    lbl.textContent = `当前选择: 起始 ${state.calPickStart}（请再点结束日）`;
  } else {
    lbl.textContent = "当前选择: （未选）";
  }
  const ul = document.getElementById("cal-ranges");
  ul.innerHTML = state.calRanges.map((r, i) =>
    `<li><span>${r[0]} ~ ${r[1]}</span><button class="btn btn-danger" data-idx="${i}" style="padding:2px 8px;font-size:12px">删除</button></li>`
  ).join("");
  ul.querySelectorAll("button").forEach((b) => {
    b.onclick = () => { state.calRanges.splice(+b.dataset.idx, 1); refreshCalHighlights(); };
  });
}

async function collectSummarizeOptions({ skipConfirm = false } = {}) {
  const prep = await api("/api/summarize/prep");
  const cfg = prep.config;
  let sheetName = cfg.sheet_name || null;
  let dateRanges = [];

  if (!skipConfirm && cfg.prompt_before_summarize) {
    const ok = await showModal("modal-confirm");
    if (!ok) return null;
  }

  if (cfg.prompt_for_sheet_name && !sheetName) {
    if (prep.sheets.length) {
      document.getElementById("sheet-sample-hint").textContent =
        prep.sample_file ? `样例文件: ${prep.sample_file}` : "";
      const sel = document.getElementById("sheet-select");
      sel.innerHTML = prep.sheets.map((n) => `<option value="${n}">${n}</option>`).join("");
      const ok = await showModal("modal-sheet");
      if (!ok) return null;
      sheetName = sel.value;
    } else {
      sheetName = prompt("请输入工作表名称") || null;
      if (!sheetName) return null;
    }
  }

  if (cfg.prompt_for_date_ranges) {
    state.calPickStart = state.calPickEnd = null;
    state.calRanges = [];
    buildCalendar();
    document.getElementById("cal-add").onclick = () => {
      if (!state.calPickStart || !state.calPickEnd) {
        alert("请先点击选择起始日和结束日（闭区间，含首尾）");
        return;
      }
      state.calRanges.push([state.calPickStart, state.calPickEnd]);
      state.calPickStart = state.calPickEnd = null;
      refreshCalHighlights();
    };
    document.getElementById("cal-clear").onclick = () => {
      state.calPickStart = state.calPickEnd = null;
      refreshCalHighlights();
    };
    const ok = await showModal("modal-calendar");
    if (!ok) return null;
    dateRanges = state.calRanges.map((r) => [r[0], r[1]]);
  }

  return { sheet_name: sheetName, date_ranges: dateRanges };
}

async function waitForTaskIdle() {
  // 先等到任务真正启动，避免 POST 返回前误判为「已空闲」
  let started = false;
  for (let i = 0; i < 60; i++) {
    const st = await api("/api/status");
    state.taskRunning = st.running;
    updateTaskButtons();
    if (st.running) {
      started = true;
      break;
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  if (!started) {
    throw new Error("任务未能启动，请稍后重试");
  }
  for (let i = 0; i < 7200; i++) {
    const st = await api("/api/status");
    state.taskRunning = st.running;
    updateTaskButtons();
    if (!st.running) return st;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("任务等待超时");
}

async function startDownload() {
  const workers = +document.getElementById("dl-concurrency")?.value || undefined;
  await api(`/api/tasks/download${workers ? "?workers=" + workers : ""}`, { method: "POST" });
  goToLogPanel();
}

async function startSummarize() {
  const payload = await collectSummarizeOptions();
  if (!payload) return;
  await api("/api/tasks/summarize", { method: "POST", body: JSON.stringify(payload) });
  goToLogPanel();
}

async function startBoth() {
  goToLogPanel();
  const workers = +document.getElementById("dl-concurrency")?.value || undefined;
  await api(`/api/tasks/download${workers ? "?workers=" + workers : ""}`, { method: "POST" });
  const afterDl = await waitForTaskIdle();
  if (afterDl.status.includes("失败")) {
    alert("下载失败，已跳过汇总");
    return;
  }
  const payload = await collectSummarizeOptions({ skipConfirm: true });
  if (payload === null) return;
  await api("/api/tasks/summarize", { method: "POST", body: JSON.stringify(payload) });
}

async function loadConfigFileList() {
  const files = await api("/api/config/files");
  const el = document.getElementById("cfg-file-list");
  if (!el) return;
  el.innerHTML = files.map((f) => `
    <div class="section">
      <strong>${f.title}</strong>
      <p class="hint">${f.description}</p>
      <div class="config-banner">${f.path}</div>
    </div>
  `).join("");
}

async function init() {
  buildPanels();
  bindSliders();
  bindSaveHandlers();
  state.menu = await api("/api/menu");
  buildNav();
  selectMenu("workbench.run");
  await loadConfigs();
  await loadConfigFileList();
  connectLogStream();

  document.getElementById("btn-dl").onclick = () => startDownload().catch((e) => alert(e.message));
  document.getElementById("btn-sum").onclick = () => startSummarize().catch((e) => alert(e.message));
  document.getElementById("btn-both").onclick = () => startBoth().catch((e) => alert(e.message));

  const st = await api("/api/status");
  state.taskRunning = st.running;
  setStatus(st.status, st.detail);
  updateTaskButtons();
}

init().catch((err) => {
  console.error(err);
  alert("网页版初始化失败: " + err.message);
});
