const catalogState = {
  skills: [],
};

const elements = {
  resumeText: document.getElementById("resume-text"),
  jdText: document.getElementById("jd-text"),
  resumeFile: document.getElementById("resume-file"),
  jdFile: document.getElementById("jd-file"),
  diagnosticRows: document.getElementById("diagnostic-rows"),
  diagnosticTemplate: document.getElementById("diagnostic-template"),
  addDiagnosticBtn: document.getElementById("add-diagnostic"),
  analyzeBtn: document.getElementById("analyze-btn"),
  status: document.getElementById("status"),
  metrics: document.getElementById("metrics"),
  gapTable: document.getElementById("gap-table"),
  roadmapList: document.getElementById("roadmap-list"),
  traceList: document.getElementById("trace-list"),
  qualityList: document.getElementById("quality-list"),
  familyPill: document.getElementById("family-pill"),
  loadTechBtn: document.getElementById("load-tech"),
  loadOpsBtn: document.getElementById("load-ops"),
};

async function apiGet(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function formatPercent(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return "-";
  return `${Math.round(n * 100)}%`;
}

function formatHours(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return "-";
  return `${n.toFixed(1)}h`;
}

function setStatus(message, error = false) {
  elements.status.textContent = message;
  elements.status.style.color = error ? "#fca5a5" : "#9db0c9";
}

function makeSkillOptions(select) {
  select.innerHTML = "";
  catalogState.skills.forEach((skill) => {
    const opt = document.createElement("option");
    opt.value = skill.skill_id;
    opt.textContent = `${skill.label} (${skill.category})`;
    select.appendChild(opt);
  });
}

function addDiagnosticRow(defaultSkillId = null, defaultRating = 60) {
  const fragment = elements.diagnosticTemplate.content.cloneNode(true);
  const row = fragment.querySelector(".diagnostic-row");
  const skillSelect = fragment.querySelector(".diag-skill");
  const ratingInput = fragment.querySelector(".diag-rating");
  const valueLabel = fragment.querySelector(".diag-value");
  const removeBtn = fragment.querySelector(".remove-row");

  makeSkillOptions(skillSelect);
  if (defaultSkillId) {
    skillSelect.value = defaultSkillId;
  }
  ratingInput.value = String(defaultRating);
  valueLabel.textContent = `${defaultRating}%`;

  ratingInput.addEventListener("input", () => {
    valueLabel.textContent = `${ratingInput.value}%`;
  });

  removeBtn.addEventListener("click", () => {
    row.remove();
  });

  elements.diagnosticRows.appendChild(fragment);
}

function collectDiagnosticRows() {
  const rows = [...elements.diagnosticRows.querySelectorAll(".diagnostic-row")];
  return rows.map((row) => {
    const skillId = row.querySelector(".diag-skill").value;
    const rating = Number(row.querySelector(".diag-rating").value) / 100;
    return {
      skill_id: skillId,
      self_rating: Number.isFinite(rating) ? rating : 0.0,
      confidence: 0.7,
    };
  });
}

function renderMetrics(metrics) {
  const entries = [
    ["Coverage", formatPercent(metrics.coverage_ratio)],
    ["Readiness", formatPercent(metrics.readiness_score)],
    ["Optimized Hours", formatHours(metrics.optimized_hours)],
    ["Hours Saved", formatHours(metrics.hours_saved)],
    ["Residual Gap", Number(metrics.residual_gap || 0).toFixed(2)],
  ];
  elements.metrics.innerHTML = entries
    .map(
      ([key, value]) =>
        `<div class="metric-card"><div class="key">${key}</div><div class="value">${value}</div></div>`,
    )
    .join("");
}

function renderGaps(gaps) {
  if (!gaps.length) {
    elements.gapTable.innerHTML = "<p class='muted'>No explicit gap found.</p>";
    return;
  }
  const header = "<tr><th>Skill</th><th>Current</th><th>Target</th><th>Gap</th></tr>";
  const rows = gaps
    .map(
      (g) =>
        `<tr><td>${g.skill}</td><td>${Number(g.current).toFixed(2)}</td><td>${Number(g.target).toFixed(2)}</td><td>${Number(g.gap).toFixed(2)}</td></tr>`,
    )
    .join("");
  elements.gapTable.innerHTML = `<table>${header}${rows}</table>`;
}

function renderRoadmap(roadmap) {
  if (!roadmap.length) {
    elements.roadmapList.innerHTML = "<p class='muted'>No roadmap generated.</p>";
    return;
  }
  elements.roadmapList.innerHTML = roadmap
    .map(
      (step) => `
        <div class="roadmap-item">
          <div class="title">${step.order}. ${step.module_id} - ${step.title}</div>
          <div class="meta">Phase: ${step.phase} | Hours: ${Number(step.estimated_hours).toFixed(1)}</div>
          <div class="meta">Reason: ${step.reason}</div>
        </div>
      `,
    )
    .join("");
}

function renderTrace(trace) {
  elements.traceList.innerHTML = trace
    .map(
      (item) =>
        `<div class="trace-item"><strong>${item.stage.replaceAll("_", " ")}</strong><div class="muted">${item.detail}</div></div>`,
    )
    .join("");
}

function renderQuality(quality) {
  const lines = [];
  lines.push(`<div class="quality-item">Catalog Modules Check: ${quality.roadmap_modules_in_catalog ? "Pass" : "Fail"}</div>`);
  lines.push(`<div class="quality-item">Catalog Skills: ${quality.catalog_size.skills}, Modules: ${quality.catalog_size.modules}</div>`);
  if (quality.unknown_modules && quality.unknown_modules.length > 0) {
    lines.push(`<div class="quality-item">Unknown Modules: ${quality.unknown_modules.join(", ")}</div>`);
  }
  elements.qualityList.innerHTML = lines.join("");
}

function renderResult(data) {
  elements.familyPill.textContent = `Role: ${data.recommended_role_family}`;
  renderMetrics(data.metrics);
  renderGaps(data.gaps || []);
  renderRoadmap(data.roadmap || []);
  renderTrace(data.trace || []);
  renderQuality(data.quality_checks || {});
}

async function analyze() {
  const diagnostic = collectDiagnosticRows();
  const resumeFile = elements.resumeFile.files[0];
  const jdFile = elements.jdFile.files[0];

  setStatus("Analyzing...");
  elements.analyzeBtn.disabled = true;

  try {
    let responseData;

    if (resumeFile && jdFile) {
      const form = new FormData();
      form.append("resume_file", resumeFile);
      form.append("jd_file", jdFile);
      form.append("diagnostic_json", JSON.stringify(diagnostic));

      const response = await fetch("/api/v1/analyze/files", {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        throw new Error(`Analysis failed (${response.status})`);
      }
      responseData = await response.json();
    } else {
      const resumeText = elements.resumeText.value.trim();
      const jdText = elements.jdText.value.trim();
      if (resumeText.length < 10 || jdText.length < 10) {
        throw new Error("Provide resume and JD text, or upload both files.");
      }

      const response = await fetch("/api/v1/analyze/text", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          resume_text: resumeText,
          jd_text: jdText,
          diagnostic: diagnostic,
        }),
      });
      if (!response.ok) {
        throw new Error(`Analysis failed (${response.status})`);
      }
      responseData = await response.json();
    }

    renderResult(responseData);
    setStatus("Roadmap generated successfully.");
  } catch (error) {
    setStatus(error.message || "Request failed.", true);
  } finally {
    elements.analyzeBtn.disabled = false;
  }
}

async function loadDemo(kind) {
  try {
    const payload = await apiGet(`/api/v1/demo/${kind}`);
    elements.resumeText.value = payload.resume || "";
    elements.jdText.value = payload.jd || "";
    setStatus(`${kind} demo loaded.`);
  } catch (error) {
    setStatus("Failed to load demo scenario.", true);
  }
}

async function bootstrap() {
  try {
    const catalog = await apiGet("/api/v1/catalog");
    catalogState.skills = (catalog.skills || []).sort((a, b) => a.label.localeCompare(b.label));
    addDiagnosticRow("communication", 65);
    addDiagnosticRow("problem_solving", 70);
    setStatus("Ready.");
  } catch (error) {
    setStatus("Backend is not reachable.", true);
  }
}

elements.addDiagnosticBtn.addEventListener("click", () => addDiagnosticRow());
elements.analyzeBtn.addEventListener("click", analyze);
elements.loadTechBtn.addEventListener("click", () => loadDemo("technical"));
elements.loadOpsBtn.addEventListener("click", () => loadDemo("operations"));

bootstrap();
