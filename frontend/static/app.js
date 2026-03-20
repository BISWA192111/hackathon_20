const catalogState = {
  skills: [],
};

const aiState = {
  isOpen: false,
  messages: [],
};

const elements = {
  resumeText: document.getElementById("resume-text"),
  jdText: document.getElementById("jd-text"),
  resumeFile: document.getElementById("resume-file"),
  jdFile: document.getElementById("jd-file"),
  analyzeBtn: document.getElementById("analyze-btn"),
  status: document.getElementById("status"),
  metrics: document.getElementById("metrics"),
  gapTable: document.getElementById("gap-table"),
  roadmapList: document.getElementById("roadmap-list"),
  traceList: document.getElementById("trace-list"),
  qualityList: document.getElementById("quality-list"),
  advancedMetrics: document.getElementById("advanced-metrics"),
  marketInsights: document.getElementById("market-insights"),
  familyPill: document.getElementById("family-pill"),
  loadTechBtn: document.getElementById("load-tech"),
  loadOpsBtn: document.getElementById("load-ops"),
  aiChatToggle: document.getElementById("ai-chat-toggle"),
  aiChatPanel: document.getElementById("ai-chat-panel"),
  aiChatOverlay: document.getElementById("ai-chat-overlay"),
  aiChatMessages: document.getElementById("ai-chat-messages"),
  aiChatInput: document.getElementById("ai-chat-input"),
  aiSendBtn: document.getElementById("ai-send-btn"),
  aiCloseBtn: document.getElementById("ai-chat-close"),
  diagnosticTemplate: document.getElementById("diagnostic-template"),
  diagnosticRows: document.querySelector(".diagnostic-rows") || { appendChild: () => {} },
  storageInfo: document.getElementById("storage-info") || { innerHTML: "" },
  assistantSuggestions: document.getElementById("assistant-suggestions") || { innerHTML: "" },
  assistantQuestion: document.getElementById("assistant-question") || { value: "" },
  askAssistantBtn: document.getElementById("ask-assistant-btn"),
  assistantStatus: document.getElementById("assistant-status") || { textContent: "", className: "" },
  recentRuns: document.getElementById("recent-runs") || { innerHTML: "" },
};

let lastAnalysisPayload = null;

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
  if (!elements.status) {
    console.log("Status:", message);
    return;
  }
  elements.status.textContent = message;
  elements.status.className = "status-message";
  if (error) {
    elements.status.classList.add("error");
  } else if (message.includes("...") || message.includes("Analyzing")) {
    elements.status.classList.add("loading");
  }
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
  if (!elements.diagnosticRows || !elements.diagnosticRows.querySelectorAll) {
    console.log("⚠️ No diagnostic rows container found, returning empty array");
    return [];
  }
  
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
  if (!elements.metrics) return;
  
  const entries = [
    ["Coverage", formatPercent(metrics.coverage_ratio), "%"],
    ["Readiness", formatPercent(metrics.readiness_score), "%"],
    ["Optimized Hours", formatHours(metrics.optimized_hours), "h"],
    ["Hours Saved", formatHours(metrics.hours_saved), "h"],
    ["Residual Gap", Number(metrics.residual_gap || 0).toFixed(2), ""],
  ];
  elements.metrics.innerHTML = entries
    .map(
      ([label, value, unit]) =>
        `<div class="metric-card"><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="metric-unit">${unit}</div></div>`,
    )
    .join("");
}

function renderGaps(gaps) {
  if (!elements.gapTable) return;
  
  if (!gaps.length) {
    elements.gapTable.innerHTML = "<p style='color: var(--gray-600);'>No explicit gap found.</p>";
    return;
  }
  const header = "<tr><th>Skill</th><th>Current Level</th><th>Target Level</th><th>Gap</th></tr>";
  const rows = gaps
    .map(
      (g) =>
        `<tr><td><strong>${g.skill}</strong></td><td>${Number(g.current).toFixed(2)}</td><td>${Number(g.target).toFixed(2)}</td><td><strong>${Number(g.gap).toFixed(2)}</strong></td></tr>`,
    )
    .join("");
  elements.gapTable.innerHTML = `<table>${header}${rows}</table>`;
}

function renderRoadmap(roadmap) {
  if (!elements.roadmapList) return;
  
  if (!roadmap.length) {
    elements.roadmapList.innerHTML = "<p style='color: var(--gray-600);'>No roadmap generated.</p>";
    return;
  }
  elements.roadmapList.innerHTML = roadmap
    .map(
      (step, idx) => `
        <div class="roadmap-item">
          <div class="roadmap-number">${idx + 1}</div>
          <div class="roadmap-content">
            <h4>${step.module_id} - ${step.title}</h4>
            <p>${step.reason || ""}</p>
            <div class="roadmap-meta">Phase: ${step.phase} | Mode: ${step.learning_mode || "standard"} | Hours: ${Number(step.estimated_hours).toFixed(1)}</div>
            <div class="roadmap-meta">Priority: ${Number(step.priority_score || 0).toFixed(2)} | Similarity: ${Number(step.similarity_score || 0).toFixed(2)}</div>
          </div>
        </div>
      `,
    )
    .join("");
}

function renderTrace(trace) {
  if (!elements.traceList) return;
  
  elements.traceList.innerHTML = trace
    .map(
      (item) =>
        `<div class="trace-item">
          <div class="trace-step">${item.stage.replace(/_/g, " ").toUpperCase()}</div>
          <div class="trace-details">${item.detail}</div>
        </div>`,
    )
    .join("");
}

function renderQuality(quality) {
  if (!elements.qualityList) return;
  
  const lines = [];
  const passIcon = "✓";
  const failIcon = "✗";
  const icon = quality.roadmap_modules_in_catalog ? passIcon : failIcon;
  const status = quality.roadmap_modules_in_catalog ? "Pass" : "Fail";
  const itemClass = quality.roadmap_modules_in_catalog ? "quality-item" : "quality-item error";
  
  lines.push(`<div class="${itemClass}">
    <div class="quality-icon">${icon}</div>
    <div class="quality-content">
      <h4>Catalog Modules Verification</h4>
      <p>${status}: All roadmap modules verified against catalog</p>
    </div>
  </div>`);
  
  lines.push(`<div class="quality-item">
    <div class="quality-icon">✓</div>
    <div class="quality-content">
      <h4>Catalog Size</h4>
      <p>${quality.catalog_size.skills} skills, ${quality.catalog_size.modules} modules available</p>
    </div>
  </div>`);
  
  if (quality.unknown_modules && quality.unknown_modules.length > 0) {
    lines.push(`<div class="quality-item warning">
      <div class="quality-icon">⚠</div>
      <div class="quality-content">
        <h4>Unknown Modules Detected</h4>
        <p>${quality.unknown_modules.join(", ")}</p>
      </div>
    </div>`);
  }
  
  elements.qualityList.innerHTML = lines.join("");
}

function renderAdvancedMetrics(advancedMetrics) {
  if (!elements.advancedMetrics) return;
  
  if (!advancedMetrics) {
    elements.advancedMetrics.innerHTML = "<p style='color: var(--gray-600);'>Not available.</p>";
    return;
  }
  const readiness = advancedMetrics.readiness || {};
  const coverage = advancedMetrics.coverage || {};
  const efficiency = advancedMetrics.efficiency || {};
  const residual = advancedMetrics.residual_gaps || {};
  elements.advancedMetrics.innerHTML = `
    <div class="quality-item">
      <div class="quality-icon">📊</div>
      <div class="quality-content">
        <h4>Readiness Status</h4>
        <p>${readiness.status || "-"} (${Number(readiness.readiness_score || 0).toFixed(1)}%)</p>
      </div>
    </div>
    <div class="quality-item">
      <div class="quality-icon">📈</div>
      <div class="quality-content">
        <h4>Coverage</h4>
        <p>${Number(coverage.coverage_percentage || 0).toFixed(1)}% of gaps covered (${coverage.gaps_covered || 0}/${coverage.gaps_total || 0})</p>
      </div>
    </div>
    <div class="quality-item">
      <div class="quality-icon">⚡</div>
      <div class="quality-content">
        <h4>Efficiency</h4>
        <p>${Number(efficiency.efficiency_percentage || 0).toFixed(1)}% time reduction</p>
      </div>
    </div>
    <div class="quality-item">
      <div class="quality-icon">🎯</div>
      <div class="quality-content">
        <h4>Expected Readiness</h4>
        <p>${Number(residual.expected_readiness || 0).toFixed(1)}% after completing this path</p>
      </div>
    </div>
  `;
}

function renderMarketInsights(payload) {
  if (!elements.marketInsights) return;
  
  if (!payload || payload.enabled === false) {
    elements.marketInsights.innerHTML = "<p style='color: var(--gray-600);'>Market insights unavailable in this runtime.</p>";
    return;
  }

  const occupations = (payload.related_occupations || []).slice(0, 5);
  const topGaps = (payload.top_gap_skills || []).slice(0, 5);

  const occHtml = occupations.length
    ? occupations
        .map((occ) => `<div class="quality-item">
          <div class="quality-icon">💼</div>
          <div class="quality-content">
            <h4>${occ.title}</h4>
            <p>Match: ${(Number(occ.score || 0) * 100).toFixed(1)}%</p>
          </div>
        </div>`)
        .join("")
    : "<p style='color: var(--gray-600);'>No related occupations found.</p>";

  const gapHtml = topGaps.length
    ? topGaps
        .map((item) => {
          const market = item.market || {};
          return `<div class="quality-item">
            <div class="quality-icon">🔍</div>
            <div class="quality-content">
              <h4>${item.skill_id}</h4>
              <p>Gap: ${Number(item.gap || 0).toFixed(2)} | ${market.commonality || "unknown"} demand</p>
            </div>
          </div>`;
        })
        .join("")
    : "<p style='color: var(--gray-600);'>No market gap signals.</p>";

  elements.marketInsights.innerHTML = `
    <div class="quality-item">
      <div class="quality-icon">📊</div>
      <div class="quality-content">
        <h4>Market Value Score</h4>
        <p>${payload.market_value_score ?? "-"}</p>
      </div>
    </div>
    ${gapHtml}
    <hr style="margin: 16px 0; border: none; border-top: 1px solid var(--gray-200);">
    ${occHtml}
  `;
}

function renderStorage(storage) {
  if (!storage) {
    elements.storageInfo.innerHTML = "<p style='color: var(--gray-600);'>No storage metadata returned.</p>";
    return;
  }
  if (!storage.saved) {
    elements.storageInfo.innerHTML = `<div class="quality-item error">
      <div class="quality-icon">✗</div>
      <div class="quality-content">
        <h4>Storage Status</h4>
        <p>${storage.reason || storage.error || "Supabase not configured."}</p>
      </div>
    </div>`;
    return;
  }
  elements.storageInfo.innerHTML = `<div class="quality-item">
    <div class="quality-icon">✓</div>
    <div class="quality-content">
      <h4>Analysis Saved</h4>
      <p>Run ID: ${storage.run_id || "-"}</p>
    </div>
  </div>`;
}

function renderAssistant(payload) {
  if (!payload) {
    elements.assistantSuggestions.innerHTML = "<p class='muted'>No assistant output yet.</p>";
    return;
  }

  const suggestions = payload.suggestions || [];
  const followups = payload.follow_up_questions || [];
  const source = payload.source || "unknown";

  const suggestionHtml = suggestions.length
    ? suggestions
        .map(
          (s) =>
            `<div class="quality-item"><strong>${s.title || "-"}</strong><div class="muted">${s.rationale || ""}</div><div class="muted">Action: ${s.action || ""} | Priority: ${(s.priority || "").toUpperCase()}</div></div>`,
        )
        .join("")
    : "<p class='muted'>No suggestion items returned.</p>";

  const followUpHtml = followups.length
    ? followups.map((q) => `<div class="quality-item"><strong>Follow-up:</strong> ${q}</div>`).join("")
    : "";

  elements.assistantSuggestions.innerHTML = `
    <div class="quality-item"><strong>Assistant Source:</strong> ${source}</div>
    <div class="quality-item"><strong>Summary:</strong> ${payload.summary || "-"}</div>
    ${suggestionHtml}
    ${followUpHtml}
  `;
}

function renderRecentRuns(payload) {
  const runs = (payload && payload.runs) || [];
  const storage = payload && payload.storage;
  if (storage && storage.enabled === false) {
    elements.recentRuns.innerHTML = "<p class='muted'>Supabase not configured.</p>";
    return;
  }
  if (!runs.length) {
    elements.recentRuns.innerHTML = "<p class='muted'>No runs saved yet.</p>";
    return;
  }
  elements.recentRuns.innerHTML = runs
    .slice(0, 8)
    .map((run) => {
      const metrics = run.metrics || {};
      return `<div class="quality-item"><strong>${run.candidate_name || "Unnamed candidate"}</strong><div class="muted">${run.recommended_role_family || "-"} | Saved ${Number(metrics.hours_saved || 0).toFixed(1)}h</div><div class="muted">${run.id}</div></div>`;
    })
    .join("");
}

async function refreshRecentRuns() {
  try {
    const payload = await apiGet("/api/v1/runs?limit=8");
  } catch (error) {
    // Silently fail if runs endpoint not available
  }
}

function renderResult(data) {
  lastAnalysisPayload = data;
  const resultsSection = document.getElementById("results-section");
  if (resultsSection) {
    resultsSection.classList.add("active");
  }
  
  if (elements.familyPill) {
    elements.familyPill.textContent = `Role Family: ${data.recommended_role_family}`;
  }
  if (elements.metrics) renderMetrics(data.metrics);
  if (elements.gapTable) renderGaps(data.gaps || []);
  if (elements.roadmapList) renderRoadmap(data.roadmap || []);
  if (elements.traceList) renderTrace(data.trace || []);
  if (elements.qualityList) renderQuality(data.quality_checks || {});
  if (elements.advancedMetrics) renderAdvancedMetrics(data.advanced_metrics);
  if (elements.marketInsights) renderMarketInsights(data.market_insights);
  
  // Scroll to results
  if (resultsSection) {
    resultsSection.scrollIntoView({ behavior: "smooth" });
  }
}

async function askAssistant() {
  const question = (elements.assistantQuestion.value || "").trim();
  if (question.length < 3) {
    elements.assistantStatus.textContent = "Enter a valid question.";
    elements.assistantStatus.className = "status-message error";
    return;
  }

  elements.askAssistantBtn.disabled = true;
  elements.assistantStatus.textContent = "Asking...";
  elements.assistantStatus.className = "status-message loading";

  try {
    const payload = {
      question: question,
      max_suggestions: 5,
      context: lastAnalysisPayload
        ? {
            recommended_role_family: lastAnalysisPayload.recommended_role_family,
            metrics: lastAnalysisPayload.metrics,
            gaps: lastAnalysisPayload.gaps,
            roadmap: lastAnalysisPayload.roadmap,
            trace: lastAnalysisPayload.trace,
          }
        : {},
      run_id: lastAnalysisPayload && lastAnalysisPayload.storage ? lastAnalysisPayload.storage.run_id : null,
    };

    const response = await fetch("/api/v1/assistant/suggest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`Assistant request failed (${response.status})`);
    }
    const data = await response.json();
    elements.assistantStatus.textContent = "Response updated.";
    elements.assistantStatus.className = "status-message";
  } catch (error) {
    elements.assistantStatus.textContent = error.message || "Assistant unavailable.";
    elements.assistantStatus.className = "status-message error";
  } finally {
    elements.askAssistantBtn.disabled = false;
  }
}

async function analyze() {
  console.log("📊 Analyze button clicked");
  
  if (!elements.analyzeBtn) return;
  
  const diagnostic = collectDiagnosticRows();
  const resumeFile = elements.resumeFile && elements.resumeFile.files ? elements.resumeFile.files[0] : null;
  const jdFile = elements.jdFile && elements.jdFile.files ? elements.jdFile.files[0] : null;

  // Check for input first
  const resumeText = (elements.resumeText && elements.resumeText.value) ? elements.resumeText.value.trim() : "";
  const jdText = (elements.jdText && elements.jdText.value) ? elements.jdText.value.trim() : "";
  
  if (!resumeFile && !jdFile && (resumeText.length < 10 || jdText.length < 10)) {
    const errorMsg = "❌ Please provide: resume and JD (either files or text, minimum 10 characters each)";
    console.warn(errorMsg);
    setStatus(errorMsg, true);
    return;
  }

  setStatus("⏳ Analyzing... this may take 30-60 seconds");
  elements.analyzeBtn.disabled = true;
  elements.analyzeBtn.style.opacity = "0.6";

  try {
    let responseData;
    
      if (resumeFile && jdFile) {
      console.log("🔄 Using file upload");
      const form = new FormData();
      form.append("resume_file", resumeFile);
      form.append("jd_file", jdFile);
      form.append("diagnostic_json", JSON.stringify(diagnostic));

      const response = await fetch("/api/v1/analyze/files", {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Analysis failed (${response.status}): ${errorText}`);
      }
      responseData = await response.json();
    } else if (resumeText.length >= 10 && jdText.length >= 10) {
      console.log("🔄 Using text input");
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
        const errorText = await response.text();
        throw new Error(`Analysis failed (${response.status}): ${errorText}`);
      }
      responseData = await response.json();
    } else {
      throw new Error("❌ Please provide: resume and JD (either files or text, minimum 10 characters each)");
    }

    console.log("✅ Analysis successful:", responseData);
    renderResult(responseData);
    setStatus("✅ Roadmap generated successfully! Scroll down to see results.");
  } catch (error) {
    console.error("❌ Analysis error:", error);
    setStatus(error.message || "Request failed.", true);
  } finally {
    if (elements.analyzeBtn) {
      elements.analyzeBtn.disabled = false;
      elements.analyzeBtn.style.opacity = "1";
    }
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

// ==================== AI CHAT FUNCTIONS ====================

function toggleAIChat() {
  aiState.isOpen = !aiState.isOpen;
  if (elements.aiChatPanel) {
    if (aiState.isOpen) {
      elements.aiChatPanel.classList.add("active");
      if (elements.aiChatOverlay) {
        elements.aiChatOverlay.classList.add("active");
      }
      // Scroll to input area
      setTimeout(() => {
        if (elements.aiChatInput) elements.aiChatInput.focus();
      }, 100);
    } else {
      elements.aiChatPanel.classList.remove("active");
      if (elements.aiChatOverlay) {
        elements.aiChatOverlay.classList.remove("active");
      }
    }
  }
}

function addAIMessage(text, type = "assistant") {
  if (!elements.aiChatMessages) return;
  
  const messageDiv = document.createElement("div");
  messageDiv.className = `ai-message ${type}`;
  
  let content = text;
  if (type === "assistant") {
    // Parse markdown-style formatting
    content = text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/\n/g, "<br>");
  }
  
  messageDiv.innerHTML = content;
  messageDiv.style.animation = "messageAppear 0.3s ease";
  elements.aiChatMessages.appendChild(messageDiv);
  
  // Scroll to bottom
  setTimeout(() => {
    elements.aiChatMessages.scrollTop = elements.aiChatMessages.scrollHeight;
  }, 10);
}

async function sendAIMessage() {
  const input = elements.aiChatInput;
  if (!input) return;
  
  const message = input.value.trim();
  if (!message || message.length < 1) return;
  
  // Add user message to chat
  addAIMessage(message, "user");
  input.value = "";
  
  // Disable input while processing
  input.disabled = true;
  const sendBtn = elements.aiSendBtn;
  if (sendBtn) sendBtn.disabled = true;
  
  try {
    // Show typing indicator
    addAIMessage("✳️ Analyzing...", "system");
    
    // Prepare context from last analysis
    const context = lastAnalysisPayload ? {
      role_family: lastAnalysisPayload.recommended_role_family,
      metrics: lastAnalysisPayload.metrics,
      gaps: lastAnalysisPayload.gaps,
      current_roadmap: lastAnalysisPayload.roadmap,
      extracted_skills: catalogState.skills.slice(0, 10),
    } : {};
    
    // Send to backend
    const response = await fetch("/api/v1/assistant/enhance-roadmap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_message: message,
        context: context,
        session_id: Date.now().toString(),
      }),
    });
    
    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`Request failed (${response.status}):`, errorBody);
      throw new Error(`Request failed (${response.status}): ${errorBody}`);
    }
    
    const data = await response.json();
    
    // Remove typing indicator
    const systemMessages = elements.aiChatMessages.querySelectorAll(".ai-message.system");
    if (systemMessages.length > 0) {
      systemMessages[systemMessages.length - 1].remove();
    }
    
    // Process response
    if (data.enhanced_roadmap && data.enhanced_roadmap.length > 0) {
      addAIMessage("Here's your enhanced roadmap:", "assistant");
      renderVisualRoadmap(data.enhanced_roadmap);
      addAIMessage(data.response_text || "Roadmap updated successfully!", "assistant");
    } else if (data.response_text) {
      addAIMessage(data.response_text, "assistant");
    }
    
    // Add follow-up suggestion if available
    if (data.follow_up_question) {
      addAIMessage(`💡 **Try asking:** "${data.follow_up_question}"`, "assistant");
    }
  } catch (error) {
    // Remove typing indicator
    const systemMessages = elements.aiChatMessages.querySelectorAll(".ai-message.system");
    if (systemMessages.length > 0) {
      systemMessages[systemMessages.length - 1].remove();
    }
    console.error("AI Chat Error:", error);
    const errorMsg = error.message.includes("422") 
      ? "Unable to process request. Please ensure you've analyzed your resume and JD first." 
      : error.message;
    addAIMessage(`⚠️ Error: ${errorMsg}`, "assistant");
  } finally {
    input.disabled = false;
    if (sendBtn) sendBtn.disabled = false;
    input.focus();
  }
}

function renderVisualRoadmap(roadmapData) {
  if (!elements.aiChatMessages || !roadmapData || roadmapData.length === 0) return;
  
  // Create visual roadmap container
  const roadmapDiv = document.createElement("div");
  roadmapDiv.className = "ai-roadmap-visualization";
  roadmapDiv.style.cssText = `
    margin: 16px 0;
    padding: 16px;
    background: linear-gradient(135deg, #F8F9FA 0%, #F0F7FF 100%);
    border-radius: 8px;
    border-left: 4px solid var(--primary-blue);
  `;
  
  let html = '<div style="display: flex; flex-direction: column; gap: 12px;">';
  
  // Create timeline visualization
  roadmapData.slice(0, 5).forEach((step, idx) => {
    const hours = Number(step.estimated_hours || 0).toFixed(1);
    const priority = Number(step.priority_score || 0).toFixed(2);
    
    html += `
      <div style="display: flex; align-items: center; gap: 12px;">
        <div style="
          min-width: 32px;
          height: 32px;
          border-radius: 50%;
          background: linear-gradient(135deg, var(--primary-blue), #0052A3);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 14px;
        ">${idx + 1}</div>
        <div style="flex: 1;">
          <div style="font-weight: 600; color: var(--gray-900);">${step.title}</div>
          <div style="font-size: 12px; color: var(--gray-600);">
            📚 ${step.module_id} | ⏱️ ${hours}h | 🎯 Priority: ${priority}
          </div>
          <div style="font-size: 13px; color: var(--gray-700); margin-top: 4px;">${step.reason || ""}</div>
        </div>
      </div>
    `;
    
    // Add connector line
    if (idx < roadmapData.length - 1 && idx < 4) {
      html += '<div style="margin-left: 16px; height: 20px; border-left: 2px dashed var(--primary-blue);"></div>';
    }
  });
  
  html += '</div>';
  roadmapDiv.innerHTML = html;
  elements.aiChatMessages.appendChild(roadmapDiv);
  
  // Scroll to show roadmap
  setTimeout(() => {
    elements.aiChatMessages.scrollTop = elements.aiChatMessages.scrollHeight;
  }, 10);
}

async function bootstrap() {
  try {
    console.log("🚀 Bootstrapping application...");
    const catalog = await apiGet("/api/v1/catalog");
    catalogState.skills = (catalog.skills || []).sort((a, b) => a.label.localeCompare(b.label));
    console.log("✅ Catalog loaded:", catalogState.skills.length, "skills");
    setStatus("✅ Ready to analyze.");
  } catch (error) {
    console.error("❌ Bootstrap error:", error);
    setStatus("⚠️ Backend is not reachable. Demo mode available.", true);
  }
}

// Setup event listeners
if (elements.analyzeBtn) elements.analyzeBtn.addEventListener("click", analyze);
if (elements.loadTechBtn) elements.loadTechBtn.addEventListener("click", () => loadDemo("technical"));
if (elements.loadOpsBtn) elements.loadOpsBtn.addEventListener("click", () => loadDemo("operations"));

// AI Chat Event Listeners
if (elements.aiChatToggle) {
  elements.aiChatToggle.addEventListener("click", toggleAIChat);
}

if (elements.aiChatOverlay) {
  elements.aiChatOverlay.addEventListener("click", () => {
    toggleAIChat();
  });
}

if (elements.aiSendBtn) {
  elements.aiSendBtn.addEventListener("click", sendAIMessage);
}

if (elements.aiChatInput) {
  elements.aiChatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendAIMessage();
    }
  });
}

if (elements.aiCloseBtn) {
  elements.aiCloseBtn.addEventListener("click", toggleAIChat);
}

// Add welcome message to AI chat on first interaction
if (elements.aiChatMessages) {
  if (elements.aiChatMessages.children.length === 0) {
    addAIMessage("👋 Welcome to AI Roadmap Builder! I can help you enhance your learning path. Upload your resume and job description first, then ask me questions about your roadmap.", "assistant");
  }
}

// Setup file upload drag-and-drop
// File Upload Handlers
const resumeUploadArea = document.getElementById("resume-upload-area");
const jdUploadArea = document.getElementById("jd-upload-area");

console.log("Resume upload area:", resumeUploadArea);
console.log("JD upload area:", jdUploadArea);

function handleFileSelect(fileInput, uploadArea, textArea, fileType) {
  console.log(`handleFileSelect called for ${fileType}`);
  console.log("fileInput:", fileInput);
  console.log("uploadArea:", uploadArea);
  console.log("textArea:", textArea);
  
  const files = fileInput.files;
  console.log(`Files object:`, files);
  
  if (!files || files.length === 0) {
    console.log(`No file selected for ${fileType}`);
    return;
  }
  
  const file = files[0];
  console.log(`File selected: ${file.name}, size: ${file.size} bytes, type: ${file.type}`);
  
  // Validate file size (5MB)
  const maxSize = 5 * 1024 * 1024;
  if (file.size > maxSize) {
    const errorMsg = `❌ File too large. ${fileType} must be under 5MB, got ${(file.size / 1024 / 1024).toFixed(1)}MB`;
    console.error(errorMsg);
    setStatus(errorMsg, true);
    fileInput.value = '';
    return;
  }
  
  // Validate file type - check both extension and MIME type
  const fileName = file.name.toLowerCase();
  const validExts = ['.pdf', '.docx', '.doc', '.txt'];
  const validMimes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
  
  const ext = validExts.find(e => fileName.endsWith(e));
  const isValidType = ext || validMimes.includes(file.type);
  
  if (!isValidType) {
    const errorMsg = `❌ Invalid file type. Supported: PDF, DOCX, TXT. Got: ${file.name.split('.').pop()}`;
    console.error(errorMsg);
    setStatus(errorMsg, true);
    fileInput.value = '';
    return;
  }
  
  console.log(`✅ File validation passed`);
  
  // Update UI to show file selected
  if (uploadArea) {
    uploadArea.style.borderColor = "var(--accent-green)";
    uploadArea.style.backgroundColor = "#F0FFF4";
    
    const fileSize = (file.size / 1024).toFixed(1);
    
    uploadArea.innerHTML = `
      <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" style="color: var(--accent-green);">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <p style="color: var(--accent-green); font-weight: 600;">✓ File selected</p>
      <small style="color: var(--gray-600);">${fileName} (${fileSize}KB)</small>
    `;
  }
  
  const successMsg = `✅ ${fileType} file "${file.name}" ready for analysis`;
  console.log(successMsg);
  setStatus(successMsg, false);
  
  // Read file content and populate textarea if it's a text file
  if (file.type === 'text/plain' || fileName.endsWith('.txt')) {
    const reader = new FileReader();
    reader.onload = (e) => {
      if (textArea) {
        textArea.value = e.target.result;
        console.log(`✅ ${fileType} text file loaded into textarea`);
      }
    };
    reader.onerror = (e) => {
      console.error(`Error reading ${fileType} file:`, e);
    };
    reader.readAsText(file);
  } else {
    console.log(`Binary file detected (${file.type}). File is ready but cannot display in textarea.`);
  }
}

// Resume Upload Event Listeners
if (resumeUploadArea && elements.resumeFile) {
  console.log("Setting up Resume upload listeners");
  
  // Click to upload
  resumeUploadArea.addEventListener("click", (e) => {
    console.log("Resume upload area clicked");
    e.stopPropagation();
    elements.resumeFile.click();
  });
  
  // File input change
  elements.resumeFile.addEventListener("change", (e) => {
    console.log("Resume file input changed event fired");
    handleFileSelect(elements.resumeFile, resumeUploadArea, elements.resumeText, "Resume");
  });
  
  // Drag and drop - dragover
  resumeUploadArea.addEventListener("dragover", (e) => {
    console.log("Resume dragover");
    e.preventDefault();
    e.stopPropagation();
    resumeUploadArea.style.backgroundColor = "#0066CC";
    resumeUploadArea.style.color = "white";
    resumeUploadArea.style.borderColor = "#0066CC";
    resumeUploadArea.style.borderWidth = "3px";
  });
  
  // Drag and drop - dragleave
  resumeUploadArea.addEventListener("dragleave", (e) => {
    console.log("Resume dragleave");
    e.preventDefault();
    e.stopPropagation();
    resumeUploadArea.style.backgroundColor = "#F0F7FF";
    resumeUploadArea.style.color = "";
    resumeUploadArea.style.borderColor = "var(--primary-blue)";
    resumeUploadArea.style.borderWidth = "2px";
  });
  
  // Drag and drop - drop
  resumeUploadArea.addEventListener("drop", (e) => {
    console.log("Resume drop event", e.dataTransfer.files);
    e.preventDefault();
    e.stopPropagation();
    resumeUploadArea.style.backgroundColor = "#F0F7FF";
    resumeUploadArea.style.color = "";
    resumeUploadArea.style.borderColor = "var(--primary-blue)";
    resumeUploadArea.style.borderWidth = "2px";
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      console.log("Files dropped on resume area:", e.dataTransfer.files);
      elements.resumeFile.files = e.dataTransfer.files;
      // Manually trigger change event since programmatic file assignment doesn't always trigger it
      elements.resumeFile.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  
  console.log("✅ Resume upload listeners attached");
} else {
  console.warn("Resume upload area or file input not found");
}

// JD Upload Event Listeners
if (jdUploadArea && elements.jdFile) {
  console.log("Setting up JD upload listeners");
  
  // Click to upload
  jdUploadArea.addEventListener("click", (e) => {
    console.log("JD upload area clicked");
    e.stopPropagation();
    elements.jdFile.click();
  });
  
  // File input change
  elements.jdFile.addEventListener("change", (e) => {
    console.log("JD file input changed event fired");
    handleFileSelect(elements.jdFile, jdUploadArea, elements.jdText, "Job Description");
  });
  
  // Drag and drop - dragover
  jdUploadArea.addEventListener("dragover", (e) => {
    console.log("JD dragover");
    e.preventDefault();
    e.stopPropagation();
    jdUploadArea.style.backgroundColor = "#0066CC";
    jdUploadArea.style.color = "white";
    jdUploadArea.style.borderColor = "#0066CC";
    jdUploadArea.style.borderWidth = "3px";
  });
  
  // Drag and drop - dragleave
  jdUploadArea.addEventListener("dragleave", (e) => {
    console.log("JD dragleave");
    e.preventDefault();
    e.stopPropagation();
    jdUploadArea.style.backgroundColor = "#F0F7FF";
    jdUploadArea.style.color = "";
    jdUploadArea.style.borderColor = "var(--primary-blue)";
    jdUploadArea.style.borderWidth = "2px";
  });
  
  // Drag and drop - drop
  jdUploadArea.addEventListener("drop", (e) => {
    console.log("JD drop event", e.dataTransfer.files);
    e.preventDefault();
    e.stopPropagation();
    jdUploadArea.style.backgroundColor = "#F0F7FF";
    jdUploadArea.style.color = "";
    jdUploadArea.style.borderColor = "var(--primary-blue)";
    jdUploadArea.style.borderWidth = "2px";
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      console.log("Files dropped on JD area:", e.dataTransfer.files);
      elements.jdFile.files = e.dataTransfer.files;
      // Manually trigger change event since programmatic file assignment doesn't always trigger it
      elements.jdFile.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  
  console.log("✅ JD upload listeners attached");
} else {
  console.warn("JD upload area or file input not found");
}

bootstrap();
