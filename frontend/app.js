/**
 * app.js — NutriPulse frontend logic.
 *
 * Rules (from AGENTS.md):
 * - All API calls live here — no inline scripts in HTML files.
 * - session_id is created once and stored in localStorage.
 * - API endpoints, request field names, and response field names are UNCHANGED.
 * - index.html uses: initProfileForm()
 * - plan.html uses:  initPlanPage()
 */

const API_BASE = "http://localhost:8000";

// ---------------------------------------------------------------------------
// Session management  (unchanged)
// ---------------------------------------------------------------------------

function getOrCreateSessionId() {
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("session_id", id);
  }
  return id;
}

// ---------------------------------------------------------------------------
// API calls  (unchanged)
// ---------------------------------------------------------------------------

async function apiPost(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `Server error ${response.status}`);
  }

  return data;
}

// ---------------------------------------------------------------------------
// Meal plan parser
// Converts the Granite markdown-ish meal_plan string into structured cards.
// Falls back to a single raw-text card if parsing produces nothing useful.
// ---------------------------------------------------------------------------

const MEAL_META = {
  "Breakfast":          { emoji: "🌅", order: 0 },
  "Mid-Morning Snack":  { emoji: "🍎", order: 1 },
  "Lunch":              { emoji: "🍱", order: 2 },
  "Evening Snack":      { emoji: "☕", order: 3 },
  "Dinner":             { emoji: "🌙", order: 4 },
  "Daily Totals":       { emoji: "📊", order: 5 },
};

/**
 * Parse Granite's meal_plan text into an array of section objects:
 * { title, emoji, lines[] }
 */
function parseMealSections(text) {
  const sections = [];
  let current = null;

  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();

    // Detect ## Section Header
    const headingMatch = line.match(/^#{1,3}\s+(.+)$/);
    if (headingMatch) {
      const title = headingMatch[1].replace(/[*_]/g, "").trim();
      current = { title, emoji: MEAL_META[title]?.emoji || "🍽️", lines: [] };
      sections.push(current);
      continue;
    }

    if (current && line) {
      current.lines.push(line);
    }
  }

  return sections;
}

/**
 * Extract a value from a line like "**Meal:** Idli with sambar"
 * Returns null if the pattern doesn't match.
 */
function extractField(lines, ...keys) {
  for (const key of keys) {
    for (const line of lines) {
      const cleaned = line.replace(/\*\*/g, "");
      const re = new RegExp(`^${key}\\s*:?\\s*(.+)$`, "i");
      const m = cleaned.match(re);
      if (m) return m[1].trim();
    }
  }
  return null;
}

/**
 * Parse macro string "1800 kcal | Protein: 90g | Carbs: 220g | Fat: 55g"
 * or individual fields. Returns { calories, protein, carbs, fat } strings or null.
 */
function parseMacros(lines) {
  // Try to find a combined macros line first
  for (const line of lines) {
    const cleaned = line.replace(/\*\*/g, "");
    // Pattern: "Calories: 450 kcal | Protein: 30g | Carbs: 50g | Fat: 12g"
    const cal = cleaned.match(/[Cc]alories?[:\s]+(\d+\s*(?:kcal)?)/);
    const pro = cleaned.match(/[Pp]rotein[:\s]+(\d+\s*g)/);
    const carb = cleaned.match(/[Cc]arbs?[:\s]+(\d+\s*g)/);
    const fat = cleaned.match(/[Ff]at[:\s]+(\d+\s*g)/);
    if (cal || pro || carb || fat) {
      return {
        calories: cal ? cal[1].trim() : null,
        protein:  pro ? pro[1].trim() : null,
        carbs:    carb ? carb[1].trim() : null,
        fat:      fat ? fat[1].trim() : null,
      };
    }
  }
  return null;
}

/**
 * Build an HTML meal card element for a parsed section.
 */
function buildMealCard(section) {
  const { title, emoji, lines } = section;
  const isTotals = title === "Daily Totals";

  const card = document.createElement("div");
  card.className = "meal-card" + (isTotals ? " totals-card" : "");
  card.setAttribute("data-meal", title);

  // Header — with swap button on non-totals cards
  const header = document.createElement("div");
  header.className = "mc-header";
  if (!isTotals) {
    header.innerHTML = `
      <span class="mc-emoji">${emoji}</span>
      <span class="mc-title">${title}</span>
      <button class="btn-swap" data-meal-title="${title}" title="Get a smart alternative for this meal">
        🔄 Swap Meal
      </button>`;
  } else {
    header.innerHTML = `<span class="mc-emoji">${emoji}</span><span class="mc-title">${title}</span>`;
  }
  card.appendChild(header);

  const body = document.createElement("div");
  body.className = "mc-body";

  if (isTotals) {
    // Totals: render all macro pills inline
    const macros = parseMacros(lines);
    const costLine = extractField(lines, "Total Estimated Cost", "Total Cost", "Estimated Cost");
    const pillsHtml = buildMacroPills(macros, costLine);
    body.innerHTML = pillsHtml ||
      `<span class="mc-ingredients">${lines.join(" · ") || "See plan above"}</span>`;
  } else {
    // Regular meal card
    const mealName = extractField(lines, "Meal", "Recipe", "Dish");
    const ingredients = extractField(lines, "Ingredients", "Ingredient");
    const cost = extractField(lines, "Estimated cost", "Cost");
    const why = extractField(lines, "Why this meal", "Why", "Reason");
    const macros = parseMacros(lines);

    if (mealName) {
      const nameEl = document.createElement("div");
      nameEl.className = "mc-meal-name";
      nameEl.textContent = mealName;
      body.appendChild(nameEl);
    }

    if (ingredients) {
      const ingEl = document.createElement("div");
      ingEl.className = "mc-ingredients";
      ingEl.textContent = ingredients;
      body.appendChild(ingEl);
    }

    // Macros + cost pills
    const pillsDiv = document.createElement("div");
    pillsDiv.className = "mc-macros";
    pillsDiv.innerHTML = buildMacroPills(macros, cost);
    if (pillsDiv.innerHTML) body.appendChild(pillsDiv);

    if (why) {
      const whyEl = document.createElement("div");
      whyEl.className = "mc-why";
      whyEl.textContent = why;
      body.appendChild(whyEl);
    }

    // Fallback: if nothing parsed, just show raw lines
    if (!mealName && !ingredients && !macros) {
      body.innerHTML = `<div class="mc-ingredients">${
        lines.map(l => l.replace(/\*\*/g, "")).join("<br>")
      }</div>`;
    }
  }

  card.appendChild(body);
  return card;
}

// ---------------------------------------------------------------------------
// Smart food swap handler
// ---------------------------------------------------------------------------

/**
 * Replace a single meal card with the swapped alternative returned by /swap-meal.
 * Called via event delegation on #mealGrid.
 */
async function handleSwap(btn) {
  const card = btn.closest(".meal-card");
  if (!card) return;

  const mealTitle    = btn.getAttribute("data-meal-title");
  const sessionId    = getOrCreateSessionId();
  const profile      = JSON.parse(localStorage.getItem("nutripulse_profile") || "{}");

  // Capture original meal text from the card's body before overwriting
  const bodyEl       = card.querySelector(".mc-body");
  const originalText = bodyEl ? bodyEl.innerText : mealTitle;

  // ── Loading state on this card only ──
  btn.disabled = true;
  btn.textContent = "⏳";
  const errorEl = card.querySelector(".swap-error");
  if (errorEl) errorEl.remove();

  try {
    const result = await apiPost("/swap-meal", {
      session_id:    sessionId,
      meal_title:    mealTitle,
      original_meal: originalText,
    });

    // ── Replace card body with swapped content ──
    const emoji = MEAL_META[mealTitle]?.emoji || "🍽️";

    // Update header — keep swap button but mark as swapped
    const header = card.querySelector(".mc-header");
    header.innerHTML = `
      <span class="mc-emoji">${emoji}</span>
      <span class="mc-title">${mealTitle}</span>
      <span class="swap-badge">✦ Swapped</span>
      <button class="btn-swap" data-meal-title="${mealTitle}" title="Swap again">
        🔄 Swap Again
      </button>`;

    // Build new body
    const newBody = document.createElement("div");
    newBody.className = "mc-body";

    const nameEl = document.createElement("div");
    nameEl.className = "mc-meal-name";
    nameEl.textContent = result.meal_name || "Alternative Meal";
    newBody.appendChild(nameEl);

    if (result.ingredients) {
      const ingEl = document.createElement("div");
      ingEl.className = "mc-ingredients";
      ingEl.textContent = result.ingredients;
      newBody.appendChild(ingEl);
    }

    // Macro pills from the parsed response fields
    const pillsDiv = document.createElement("div");
    pillsDiv.className = "mc-macros";
    pillsDiv.innerHTML = buildMacroPills(
      {
        calories: result.calories || null,
        protein:  result.protein  || null,
        carbs:    result.carbs    || null,
        fat:      result.fat      || null,
      },
      result.estimated_cost || null,
    );
    if (pillsDiv.innerHTML) newBody.appendChild(pillsDiv);

    if (result.swap_reason) {
      const reasonEl = document.createElement("div");
      reasonEl.className = "mc-why";
      reasonEl.textContent = result.swap_reason;
      newBody.appendChild(reasonEl);
    }

    // Swap out old body
    const oldBody = card.querySelector(".mc-body");
    card.replaceChild(newBody, oldBody);

    // Mark card as swapped
    card.classList.add("meal-card-swapped");

  } catch (err) {
    // Restore button and show inline error — don't break the page
    btn.disabled = false;
    btn.textContent = "🔄 Swap Meal";
    const errDiv = document.createElement("div");
    errDiv.className = "swap-error";
    errDiv.textContent = "Couldn't generate a swap. Try again.";
    card.appendChild(errDiv);
  }
}

function buildMacroPills(macros, cost) {
  if (!macros && !cost) return "";
  const parts = [];
  if (macros?.calories) parts.push(`<span class="macro-pill calories">🔥 ${macros.calories}</span>`);
  if (macros?.protein)  parts.push(`<span class="macro-pill protein">💪 ${macros.protein} protein</span>`);
  if (macros?.carbs)    parts.push(`<span class="macro-pill carbs">🌾 ${macros.carbs} carbs</span>`);
  if (macros?.fat)      parts.push(`<span class="macro-pill fat">🫐 ${macros.fat} fat</span>`);
  if (cost)             parts.push(`<span class="macro-pill cost">₹${cost.replace(/₹/g, "").trim()}</span>`);
  return parts.join("");
}

/**
 * Extract daily totals from the parsed sections for the summary strip.
 */
function extractSummaryTotals(sections) {
  const totalsSection = sections.find(s => s.title === "Daily Totals");
  if (!totalsSection) return null;
  const macros = parseMacros(totalsSection.lines);
  const cost = extractField(totalsSection.lines, "Total Estimated Cost", "Total Cost", "Estimated Cost");
  return { macros, cost };
}

// ---------------------------------------------------------------------------
// Profile page (index.html)  — unchanged logic, updated button text
// ---------------------------------------------------------------------------

function initProfileForm() {
  const form = document.getElementById("profileForm");
  if (!form) return;

  const submitBtn = document.getElementById("submitBtn");
  const errorMsg = document.getElementById("errorMsg");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorMsg.classList.add("hidden");

    const allergies = document
      .getElementById("allergies")
      .value.split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const foodPreferences = document
      .getElementById("food_preferences")
      .value.split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const profile = {
      session_id: getOrCreateSessionId(),
      age: parseInt(document.getElementById("age").value, 10),
      goal: document.getElementById("goal").value,
      dietary_preference: document.getElementById("dietary_preference").value,
      budget: parseFloat(document.getElementById("budget").value),
      activity_level: document.getElementById("activity_level").value,
      allergies,
      food_preferences: foodPreferences,
      health_condition: document.getElementById("health_condition").value,
    };

    localStorage.setItem("nutripulse_profile", JSON.stringify(profile));

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="btn-generate-icon">⏳</span> Generating your plan…';

    try {
      const result = await apiPost("/meal-plan", profile);
      localStorage.setItem("nutripulse_plan", JSON.stringify(result));
      window.location.href = "plan.html";
    } catch (err) {
      errorMsg.textContent = err.message;
      errorMsg.classList.remove("hidden");
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span class="btn-generate-icon">✦</span> Generate My Meal Plan';
    }
  });
}

// ---------------------------------------------------------------------------
// Plan page (plan.html)
// ---------------------------------------------------------------------------

function initPlanPage() {
  const loadingState = document.getElementById("loadingState");
  const planCard     = document.getElementById("planCard");
  const feedbackCard = document.getElementById("feedbackCard");
  const errorState   = document.getElementById("errorState");

  if (!loadingState) return;

  // Animate loading steps while waiting
  let stepIdx = 0;
  const steps = ["lstep1", "lstep2", "lstep3"];
  const stepTimer = setInterval(() => {
    if (stepIdx > 0) {
      document.getElementById(steps[stepIdx - 1])?.classList.replace("active", "done");
    }
    if (stepIdx < steps.length) {
      document.getElementById(steps[stepIdx])?.classList.add("active");
      stepIdx++;
    } else {
      clearInterval(stepTimer);
    }
  }, 4000);

  const stored = localStorage.getItem("nutripulse_plan");

  if (!stored) {
    clearInterval(stepTimer);
    showError("No meal plan found. Please fill in your profile first.");
    return;
  }

  const planData = JSON.parse(stored);
  clearInterval(stepTimer);
  displayPlan(planData);

  // Smart swap — event delegation on the grid (handles dynamically added buttons)
  document.getElementById("mealGrid").addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-swap");
    if (btn) handleSwap(btn);
  });

  // Regenerate
  document.getElementById("regenerateBtn").addEventListener("click", async () => {
    const profile = JSON.parse(localStorage.getItem("nutripulse_profile"));
    if (!profile) { window.location.href = "index.html"; return; }
    showLoading();
    try {
      const result = await apiPost("/meal-plan", profile);
      localStorage.setItem("nutripulse_plan", JSON.stringify(result));
      displayPlan(result);
    } catch (err) {
      showError(err.message);
    }
  });

  // Feedback
  document.getElementById("feedbackBtn").addEventListener("click", async () => {
    const feedbackInput = document.getElementById("feedbackInput");
    const feedbackError = document.getElementById("feedbackError");
    const feedbackBtn   = document.getElementById("feedbackBtn");
    const text = feedbackInput.value.trim();

    if (!text) {
      feedbackError.textContent = "Please enter your feedback before submitting.";
      feedbackError.classList.remove("hidden");
      return;
    }

    feedbackError.classList.add("hidden");
    feedbackBtn.disabled = true;
    feedbackBtn.textContent = "Revising…";

    try {
      const sessionId = getOrCreateSessionId();
      const result = await apiPost("/feedback", {
        session_id: sessionId,
        feedback_text: text,
      });
      localStorage.setItem("nutripulse_plan", JSON.stringify(result));
      displayPlan(result);
      feedbackInput.value = "";
    } catch (err) {
      feedbackError.textContent = err.message;
      feedbackError.classList.remove("hidden");
    } finally {
      feedbackBtn.disabled = false;
      feedbackBtn.innerHTML = "✦ Revise My Plan";
    }
  });

  // ── Helpers ──

  function displayPlan(data) {
    const mealGrid    = document.getElementById("mealGrid");
    const explText    = document.getElementById("explanationText");

    // Parse meal_plan string into sections
    const sections = parseMealSections(data.meal_plan);

    // Populate summary strip from Daily Totals section
    const totals = extractSummaryTotals(sections);
    if (totals) {
      const set = (id, val) => {
        const el = document.getElementById(id);
        if (el && val) el.textContent = val;
      };
      set("sumCalories", totals.macros?.calories || "—");
      set("sumProtein",  totals.macros?.protein  || "—");
      set("sumCarbs",    totals.macros?.carbs     || "—");
      set("sumFat",      totals.macros?.fat       || "—");
      set("sumCost",     totals.cost ? `₹${totals.cost.replace(/₹/g, "").trim()}` : "—");
    }

    // Build meal cards
    mealGrid.innerHTML = "";
    if (sections.length > 0) {
      // Sort by known order, put unknowns last
      sections
        .sort((a, b) => (MEAL_META[a.title]?.order ?? 99) - (MEAL_META[b.title]?.order ?? 99))
        .forEach(section => mealGrid.appendChild(buildMealCard(section)));
    } else {
      // Fallback: display raw text in a single card
      const raw = document.createElement("div");
      raw.className = "meal-card";
      raw.setAttribute("data-meal", "Meal Plan");
      raw.innerHTML = `
        <div class="mc-header"><span class="mc-emoji">🍽️</span><span class="mc-title">Your Meal Plan</span></div>
        <div class="mc-body"><div class="mc-ingredients">${
          data.meal_plan.replace(/\n/g, "<br>").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        }</div></div>`;
      mealGrid.appendChild(raw);
    }

    explText.textContent = data.explanation;

    loadingState.classList.add("hidden");
    errorState.classList.add("hidden");
    planCard.classList.remove("hidden");
    feedbackCard.classList.remove("hidden");
  }

  function showLoading() {
    planCard.classList.add("hidden");
    feedbackCard.classList.add("hidden");
    errorState.classList.add("hidden");
    loadingState.classList.remove("hidden");
    // Reset step indicators
    steps.forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.classList.remove("active", "done"); }
    });
    document.getElementById("lstep1")?.classList.add("active");
  }

  function showError(message) {
    document.getElementById("errorText").textContent = message;
    loadingState.classList.add("hidden");
    planCard.classList.add("hidden");
    feedbackCard.classList.add("hidden");
    errorState.classList.remove("hidden");
  }
}

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("profileForm")) {
    initProfileForm();
  } else if (document.getElementById("loadingState")) {
    initPlanPage();
  }
});
