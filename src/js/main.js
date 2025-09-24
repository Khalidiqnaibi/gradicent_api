// Config   
const API_BASE = "www.bindersoftware.com"; // empty = same origin; use "http://localhost:5050" if hosting elsewhere
const endpoints = {
      query: API_BASE + "/ai/query",
      add_document: API_BASE + "/ai/add_document",
      inspect: API_BASE + "/ai/inspect",
      switch_model: API_BASE + "/ai/switch_model",
      rebuild_retriever: API_BASE + "/ai/rebuild_retriever",
      root: API_BASE + "/ai/"
};

// Helpers
function el(id){ return document.getElementById(id) }
function showToast(msg, timeout=3500) {
      const t = el("toast");
      t.textContent = msg;
      t.style.display = "block";
      setTimeout(()=> t.style.display = "none", timeout);
}

// Server health check
async function checkServer() {
      try {
      const start = performance.now();
      const r = await fetch(endpoints.root);
      const ms = Math.round(performance.now() - start);
      if (!r.ok) throw new Error("no");
      el("serverStatus").classList.add("ok");
      el("statusText").textContent = "Server OK — " + ms + "ms";
      el("serverStatus").querySelector(".dot").style.background = "var(--success)";
      } catch (err) {
      el("statusText").textContent = "Server unreachable";
      el("serverStatus").classList.remove("ok");
      }
}

// Query flow
async function runQuery() {
      const q = el("question").value.trim();
      if(!q) { showToast("Write a question first"); return; }
      const top_k = Number(el("topkRange").value || 5);
      const mode = el("modeSelect").value || null;
      const return_sources = el("returnSources").checked;

      el("loaderWrap").style.display = "inline-block";
      el("answerText").textContent = "";
      el("answerMeta").textContent = "";

      const payload = { question: q, top_k, return_sources };
      if (mode) payload.mode = mode;

      try {
      const res = await fetch(endpoints.query, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Server error");

      // Show answer
      el("answerText").innerHTML = marked.parse(json.answer || "(no answer returned)");
      el("answerMeta").textContent = `top_k=${top_k} mode=${mode||"default"}`;

      // Populate provenance
      renderProvenance(json.sources || []);
      // QA sources
      renderQaSources(json.qa_sources || []);

      // Raw JSON
      el("rawJson").style.display = "block";
      el("rawJson").textContent = JSON.stringify(json, null, 2);

      } catch (err) {
      showToast("Query error: " + (err.message || err));
      el("answerText").textContent = "Error: " + (err.message || err);
      el("rawJson").textContent = err.stack || String(err);
      } finally {
      el("loaderWrap").style.display = "none";
      }
}

function renderProvenance(sources) {
      const wrap = el("sourcesList");
      wrap.innerHTML = "";
      if (!sources || sources.length === 0) {
      wrap.innerHTML = '<div class="muted">No vectorstore provenance returned.</div>';
      return;
      }
      sources.forEach((s, i) => {
      const card = document.createElement("div");
      card.className = "source-card";
      card.innerHTML = `
          <div style="flex:1">
          <div style="display:flex;justify-content:space-between;align-items:start">
              <div>
              <strong style="font-size:13px">${s.source_filename || s.chunk_id || ("source #" + (i+1))}</strong>
              <div class="source-meta">${s.page ? "page: " + s.page + " • " : ""}score: ${s.similarity_score!=null ? s.similarity_score.toFixed(4) : "n/a"}</div>
              </div>
              <div style="min-width:90px;text-align:right;font-size:12px;color:var(--muted)">${s.chunk_id || ""}</div>
          </div>
          ${s.preview ? `<div style="margin-top:8px;font-size:13px;color:var(--accent-2)">${s.preview}</div>` : ""}
          </div>
      `;
      wrap.appendChild(card);
      });
}

function renderQaSources(list) {
      const wrap = el("qaSources");
      wrap.innerHTML = "";
      if (!list || list.length === 0) {
      wrap.innerHTML = '<div class="muted">No QA sources returned (try toggling "Return QA sources").</div>';
      return;
      }
      list.forEach((d, idx) => {
      const div = document.createElement("div");
      div.className = "card";
      const snippet = (d.page_content || "").slice(0, 600);
      const md = d.metadata || {};
      div.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:start">
          <div>
              <strong>Source: ${md.source || md.source_filename || md.file || ("doc " + (idx+1))}</strong>
              <div class="muted" style="margin-top:4px">${md.chunk_id ? "chunk " + md.chunk_id : ""} ${md.page ? " • page " + md.page : ""}</div>
          </div>
          <div style="font-size:12px;color:var(--muted)">${md.owner || ""}</div>
          </div>
          <pre style="margin-top:8px; background:#fbfdff; padding:10px; border-radius:8px; max-height:220px; overflow:auto">${escapeHtml(snippet)}</pre>
      `;
      wrap.appendChild(div);
      });
}

function escapeHtml(s) {
      if (!s) return "";
      return s.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}

// Add document: file upload & text indexing
async function uploadFileOrText(file) {
      const status = el("uploadStatus");
      status.textContent = "";
      try {
      if (file) {
          const fd = new FormData();
          fd.append("file", file, file.name);

          const r = await fetch(endpoints.add_document, { method: "POST", body: fd });
          const json = await r.json();
          if (!r.ok) throw new Error(json.error || "upload failed");
          showToast("File indexed: " + (json.details?.[0]?.source || file.name));
      } else {
          const rawText = el("rawText").value.trim();
          if (!rawText) { showToast("No text to index"); return; }
          let meta = {};
          try { meta = JSON.parse(el("rawMeta").value || "{}"); } catch(e) { showToast("Invalid metadata JSON"); return; }

          const body = { raw_text: rawText, metadata: meta };
          const r = await fetch(endpoints.add_document, {
          method: "POST",
          headers: { "Content-Type":"application/json" },
          body: JSON.stringify(body)
          });
          const json = await r.json();
          if (!r.ok) throw new Error(json.error || "index failed");
          showToast("Text indexed: " + (json.details?.[0]?.source || "raw_text"));
          el("rawText").value = "";
      }
      status.textContent = "Indexed ✓";
      } catch (err) {
      status.textContent = "Error";
      showToast("Index error: " + (err.message || err));
      } finally {
      setTimeout(()=> status.textContent = "", 2000);
      }
}

// Inspector
async function runInspect() {
      const q = el("inspectQuery").value.trim();
      if (!q) { showToast("Type an inspect query"); return; }
      el("inspectResult").textContent = "Running...";
      try {
      const r = await fetch(endpoints.inspect + "?q=" + encodeURIComponent(q));
      const json = await r.json();
      if (!r.ok) throw new Error(json.error || "inspect failed");
      const dense = json.inspection?.dense || [];
      const sparse = json.inspection?.sparse || [];
      let out = "";
      out += "Dense results:\n";
      dense.forEach((it, i) => {
          out += `${i+1}. ${JSON.stringify(it[0] || it[1] || it)}\n`;
      });
      if (sparse.length) {
          out += "\nSparse scores:\n";
          sparse.slice(0,20).forEach(([i,score]) => {
          out += `id:${i} -> ${score}\n`;
          });
      }
      el("inspectResult").textContent = out;
      } catch (err) {
      el("inspectResult").textContent = "Error: " + (err.message || err);
      }
}

// Switch model
async function switchModel() {
      const mode = el("modelMode").value;
      const hfModel = el("modelName").value || null;
      try {
      const r = await fetch(endpoints.switch_model, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode, hf_model: hfModel })
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.error || "switch failed");
      showToast("Model switched: " + (json.mode || mode));
      } catch (err) {
      showToast("Switch failed: " + (err.message || err));
      }
}

// Rebuild retriever
async function rebuildRetriever() {
      const topDense = prompt("Top-k dense (default 10):", "10");
      const topSparse = prompt("Top-k sparse (default 10):", "10");
      if (topDense === null) return;
      try {
      const r = await fetch(endpoints.rebuild_retriever, {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({ top_k_dense: Number(topDense), top_k_sparse: Number(topSparse) })
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.error || "rebuild failed");
      showToast("Retriever rebuilt: dense="+json.top_k_dense+" sparse="+json.top_k_sparse);
      } catch (err) {
      showToast("Rebuild failed: " + (err.message || err));
      }
}

// Utilities
function downloadJSON(filename, data) {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename; document.body.appendChild(a); a.click();
      a.remove(); URL.revokeObjectURL(url);
}

const audioPlayer = new Audio();

function loadVoices() {
    fetch(endpoints.voices)
    .then(res => res.json())
    .then(data => {
        const select = el("voiceSelect");
        select.innerHTML = "";
        if (data.voices && data.voices.length) {
            data.voices.forEach(v => {
                const opt = document.createElement("option");
                opt.value = v.id;
                opt.textContent = `${v.name} (${v.lang})`;
                select.appendChild(opt);
            })
        }
    })
    .catch(err=> {
        console.error("Voice load error", err);
        showToast("Failed to load voices");
        logg.innerHTML = `Failed to load voices: ${err}`;
        
    })
}

async function speakAnswer() {
      const text = el("answerText").innerText || "";
      if (!text) { showToast("No answer to read yet"); return; }
      const voiceId = el("voiceSelect").value || null;
      try {
          const res = await fetch(endpoints.speak, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, voice_id: voiceId })
          });
          if (!res.ok) throw new Error("TTS failed");
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          audioPlayer.src = url;
          audioPlayer.play();
      } catch (err) {
          console.error("TTS error", err);
          showToast("TTS request failed");
      }
}

function stopSpeaking() {
      audioPlayer.pause();
      audioPlayer.currentTime = 0;
}

// Wire up events
document.addEventListener("DOMContentLoaded", () => {
  checkServer();
  loadVoices();
  setInterval(checkServer, 15000); // ping every 15s

  const logg= document.getElementById("log");

  el("readAnswer").addEventListener("click", speakAnswer);
  el("stopRead").addEventListener("click", stopSpeaking);

  el("askBtn").addEventListener("click", runQuery);
  el("clearBtn").addEventListener("click", ()=> {
    el("question").value = ""; el("answerText").textContent = ""; el("sourcesList").innerHTML = ""; el("qaSources").innerHTML = "";
  });
  el("sampleBtn").addEventListener("click", ()=> { el("question").value = "what is the protocol to use when examining a patient to develop a diagnosis."; });
  el("rawJsonBtn").addEventListener("click", ()=> {
    const p = el("rawJson");
    p.style.display = p.style.display === "block" ? "none" : "block";
  });

  // Top-k slider live update
  const topkRange = el("topkRange");
  const topkValue = el("topkValue");
  topkRange.addEventListener("input", ()=> topkValue.textContent = topkRange.value);

  // Upload
  const drop = el("dropzone");
  const fileInput = el("fileInput");
  drop.addEventListener("click", ()=> fileInput.click());
  fileInput.addEventListener("change", (ev)=> {
    const f = ev.target.files[0];
    if (f) uploadFileOrText(f);
    fileInput.value = "";
  });

  ["dragenter","dragover"].forEach(e => {
    drop.addEventListener(e, (ev)=> { ev.preventDefault(); drop.style.borderColor = "rgba(106,165,255,0.45)"; drop.style.background = "linear-gradient(90deg, rgba(106,165,255,0.03), rgba(86,217,196,0.02))"; });
  });
  ["dragleave","drop"].forEach(e => {
    drop.addEventListener(e, (ev)=> { ev.preventDefault(); drop.style.borderColor = "rgba(15,23,42,0.04)"; drop.style.background = "transparent"; });
  });
  drop.addEventListener("drop", (ev)=> {
    ev.preventDefault();
    const f = ev.dataTransfer.files && ev.dataTransfer.files[0];
    if (f) uploadFileOrText(f);
  });
  el("uploadTextBtn").addEventListener("click", ()=> uploadFileOrText(null));

  // Inspect + model controls
  el("inspectBtn").addEventListener("click", runInspect);
  el("clearInspect").addEventListener("click", ()=> el("inspectResult").textContent = "");
  el("switchModelBtn").addEventListener("click", switchModel);
  el("rebuildBtn").addEventListener("click", rebuildRetriever);

  // copy answer
  el("copyAnswer").addEventListener("click", async ()=> {
    const t = el("answerText").textContent || "";
    try { await navigator.clipboard.writeText(t); showToast("Answer copied"); } catch(e){ showToast("Copy failed") }
  });

  // download raw json
  el("downloadJson").addEventListener("click", ()=> {
    const raw = el("rawJson").textContent;
    if (!raw) { showToast("No JSON to download"); return; }
    try {
      const obj = JSON.parse(raw);
      downloadJSON("response.json", obj);
    } catch (e) {
      downloadJSON("response.txt", { raw });
    }
  });
});