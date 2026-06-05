"use strict";

const HINTS = {
  claude: "Uses Anthropic's `claude` CLI. Install: npm i -g @anthropic-ai/claude-code, then sign in. Optional model: sonnet / opus.",
  gemini: "Uses Google's `gemini` CLI. Install: npm i -g @google/gemini-cli, then sign in.",
  ollama: "Open-source. Install from ollama.com, then `ollama pull llama3.1`. Set a model at right.",
  openrouter: "Hosted models (DeepSeek, Qwen, …). Set OPENROUTER_API_KEY before starting. Optional model, e.g. deepseek/deepseek-chat.",
  mock: "Offline preview — maps requirements to free courses from a built-in catalog. No model required.",
};

let AVAILABILITY = {};
let MODELS = {};

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

async function loadProviders() {
  try {
    const res = await fetch("/providers");
    const list = await res.json();
    list.forEach((p) => {
      AVAILABILITY[p.name] = p.available;
      MODELS[p.name] = p.models || [];
    });
  } catch (_) { /* non-fatal */ }
  // Default to the first detected engine so users aren't pointed at an
  // uninstalled one. Order follows the dropdown (claude, gemini, ollama,
  // openrouter, mock).
  const sel = document.getElementById("provider");
  if (!AVAILABILITY[sel.value]) {
    const firstAvail = Array.from(sel.options).find((o) => AVAILABILITY[o.value]);
    if (firstAvail) sel.value = firstAvail.value;
  }
  updateHint();
  buildModelOptions();
}

// Rebuild the model dropdown for the selected engine: a default entry, the
// engine's suggested models, and a "Custom…" escape hatch for any other id.
function buildModelOptions() {
  const provider = document.getElementById("provider").value;
  const sel = document.getElementById("model");
  sel.innerHTML = "";
  sel.appendChild(new Option("Default model", ""));
  (MODELS[provider] || []).forEach((m) => sel.appendChild(new Option(m, m)));
  sel.appendChild(new Option("Custom…", "__custom__"));
  sel.value = "";
  toggleCustom();
}

function toggleCustom() {
  const isCustom = document.getElementById("model").value === "__custom__";
  const custom = document.getElementById("model-custom");
  custom.classList.toggle("hidden", !isCustom);
  if (isCustom) custom.focus();
}

function updateHint() {
  const sel = document.getElementById("provider");
  const name = sel.value;
  const avail = AVAILABILITY[name];
  const detected = avail === undefined ? "" : avail ? " ✓ detected" : " — not detected on this machine";
  document.getElementById("provider-hint").textContent = (HINTS[name] || "") + detected;
}

function setStatus(kind, msg) {
  const s = document.getElementById("status");
  s.className = "status " + kind;
  s.textContent = msg;
}

function renderDownloads(files) {
  const wrap = document.getElementById("download-buttons");
  wrap.innerHTML = "";
  files.forEach((f) => {
    const a = el("a", null, f.label);
    a.href = f.url;
    a.setAttribute("download", "");
    wrap.appendChild(a);
  });
  document.getElementById("downloads").classList.remove("hidden");
}

// Build the requirement -> free-courses table from the plan preview.
function renderTable(plan) {
  const title = document.getElementById("preview-title");
  title.textContent = plan.role ? "Study plan — " + plan.role : "Study plan";

  const guide = document.getElementById("preview-guidance");
  guide.textContent = plan.guidance || "";
  guide.classList.toggle("hidden", !plan.guidance);

  const wrap = document.getElementById("preview-table");
  wrap.innerHTML = "";
  const table = el("table", "prep-table");

  const thead = el("thead");
  const htr = el("tr");
  ["#", "Requirement", "Free courses"].forEach((h, i) =>
    htr.appendChild(el("th", i === 0 ? "num" : null, h))
  );
  thead.appendChild(htr);
  table.appendChild(thead);

  const tbody = el("tbody");
  (plan.rows || []).forEach((row, i) => {
    const tr = el("tr");
    tr.appendChild(el("td", "num", String(i + 1)));

    const reqTd = el("td", "req");
    if (row.timebox) reqTd.appendChild(el("span", "timebox", row.timebox));
    reqTd.appendChild(document.createTextNode(row.requirement));
    tr.appendChild(reqTd);

    const td = el("td");
    const ul = el("ul");
    (row.courses || []).forEach((c) => {
      const li = el("li");
      const a = el("a", null, c.title);
      a.href = c.url;
      a.target = "_blank";
      a.rel = "noopener";
      li.appendChild(a);
      if (c.platform) li.appendChild(el("span", "platform", " — " + c.platform));
      ul.appendChild(li);
    });
    td.appendChild(ul);
    tr.appendChild(td);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  document.getElementById("preview").classList.remove("hidden");
}

async function onSubmit(ev) {
  ev.preventDefault();
  const form = ev.target;
  const btn = document.getElementById("go");
  const data = new FormData(form);
  // "Custom…" submits the free-text id instead of the sentinel option value.
  if (data.get("model") === "__custom__") {
    data.set("model", document.getElementById("model-custom").value.trim());
  }

  btn.disabled = true;
  setStatus("working", "Mapping… the first run on a local model can take a minute.");
  document.getElementById("downloads").classList.add("hidden");
  document.getElementById("preview").classList.add("hidden");

  try {
    const res = await fetch("/generate", { method: "POST", body: data });
    const payload = await res.json();
    if (!res.ok) {
      setStatus("error", payload.detail || "Mapping failed.");
      return;
    }
    renderDownloads(payload.files);
    renderTable(payload.preview);
    const n = (payload.preview.rows || []).length;
    setStatus("done", `Done. Mapped ${n} requirement${n === 1 ? "" : "s"} to free courses. Download the table below.`);
  } catch (err) {
    setStatus("error", "Network error: " + err.message);
  } finally {
    btn.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("provider").addEventListener("change", () => {
    updateHint();
    buildModelOptions();
  });
  document.getElementById("model").addEventListener("change", toggleCustom);
  document.getElementById("prep-form").addEventListener("submit", onSubmit);
  loadProviders();
});
