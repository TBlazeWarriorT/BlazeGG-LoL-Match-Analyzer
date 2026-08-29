function showCustomConfirmModal(options) {
    var existingModal = document.getElementById("customBlazeModal");
    if (existingModal) existingModal.remove();

    var i18n = window.REPORT_I18N || {};
    var title = options.title || "Confirmation";
    var body = options.body || "";
    var confirmText = options.confirmText || "Confirm";
    var cancelText = options.cancelText || i18n.cancel || "Cancel";
    var confirmColor = options.confirmColor || "#ea580c";
    var confirmBorder = options.confirmBorder || "#f97316";

    var modalHtml = '<div id="customBlazeModal" class="modal-backdrop">' +
        '<div class="modal-card">' +
            '<div class="modal-title">' + title + '</div>' +
            '<div class="modal-body">' + body + '</div>' +
            '<div class="modal-actions">' +
                '<button type="button" class="modal-btn modal-btn-cancel" id="customModalCancelBtn">' + cancelText + '</button>' +
                '<button type="button" class="modal-btn modal-btn-confirm" id="customModalConfirmBtn" style="background:' + confirmColor + '; border-color:' + confirmBorder + ';">' + confirmText + '</button>' +
            '</div>' +
        '</div>' +
    '</div>';

    document.body.insertAdjacentHTML("beforeend", modalHtml);
    var modalEl = document.getElementById("customBlazeModal");

    function closeModal() {
        if (modalEl) {
            modalEl.classList.remove("active");
            setTimeout(function() { modalEl.remove(); }, 200);
        }
    }

    document.getElementById("customModalCancelBtn").onclick = closeModal;
    document.getElementById("customModalConfirmBtn").onclick = function() {
        closeModal();
        if (typeof options.onConfirm === "function") {
            options.onConfirm();
        }
    };

    setTimeout(function() {
        if (modalEl) modalEl.classList.add("active");
    }, 10);
}

function promptSearchSummoner(name, tag) {
    if (!name || !tag) return;
    var i18n = window.REPORT_I18N || {};
    var lang = i18n.lang || "en_US";
    var isPt = lang === "pt_BR";
    showCustomConfirmModal({
        title: isPt ? "🔍 Buscar Invocador" : "🔍 Search Summoner",
        body: isPt 
            ? "Deseja buscar as partidas recentes de <span class='modal-summoner-highlight'>" + name + "#" + tag + "</span>?" 
            : "Do you want to search recent matches for <span class='modal-summoner-highlight'>" + name + "#" + tag + "</span>?",
        confirmText: i18n.search_modal_confirm || "Search Matches ➔",
        confirmColor: "#ea580c",
        confirmBorder: "#f97316",
        onConfirm: function() {
            window.location.href = "/search?game_name=" + encodeURIComponent(name) + "&tag_line=" + encodeURIComponent(tag) + "&lang=" + lang;
        }
    });
}

function confirmDeleteSummonerModal(formEl, summonerLabel) {
    var i18n = window.REPORT_I18N || {};
    var isPt = (i18n.lang === "pt_BR");
    showCustomConfirmModal({
        title: i18n.delete_modal_title || "Delete Saved Matches",
        body: isPt 
            ? "Deseja realmente apagar as partidas de <span class='modal-summoner-highlight'>" + summonerLabel + "</span> do disco local?" 
            : "Do you really want to delete saved matches for <span class='modal-summoner-highlight'>" + summonerLabel + "</span> from local disk?",
        confirmText: isPt ? "Sim, Excluir" : "Yes, Delete",
        confirmColor: "#dc2626",
        confirmBorder: "#ef4444",
        onConfirm: function() {
            if (formEl) formEl.submit();
        }
    });
    return false;
}

function confirmClearAllCacheModal(formEl) {
    var i18n = window.REPORT_I18N || {};
    var isPt = (i18n.lang === "pt_BR");
    showCustomConfirmModal({
        title: "⚠️ " + (i18n.clear_all_title || "Clear All Cache"),
        body: isPt 
            ? "Deseja realmente apagar <b>todas</b> as partidas salvas no disco local? Esta ação é irreversível." 
            : "Do you really want to delete <b>all</b> cached matches from local disk? This action cannot be undone.",
        confirmText: isPt ? "Apagar Tudo" : "Clear All",
        confirmColor: "#dc2626",
        confirmBorder: "#ef4444",
        onConfirm: function() {
            if (formEl) formEl.submit();
        }
    });
    return false;
}

function closeClearAllModal() {
    var m = document.getElementById("clearAllPromptModal");
    if (m) {
        m.classList.remove("active");
        setTimeout(function() { m.remove(); }, 200);
    }
    window._pendingClearAllForm = null;
}

function executeClearAll() {
    var form = window._pendingClearAllForm;
    closeClearAllModal();
    if (form) {
        form.submit();
    }
}

var tabExpandedState = {};

function toggleTabMatches(tabIndex, totalCount) {
    var pane = document.getElementById("cache-tab-" + tabIndex);
    var btn = document.getElementById("expand-btn-" + tabIndex);
    if (!pane || !btn) return;

    var isExpanded = !!tabExpandedState[tabIndex];
    var hiddenMatches = pane.querySelectorAll(".match-item");
    var isPt = document.documentElement.lang.includes("pt") || (window.REPORT_I18N && window.REPORT_I18N.lang === "pt_BR");

    if (!isExpanded) {
        hiddenMatches.forEach(function(el) {
            el.classList.remove("match-hidden");
        });
        tabExpandedState[tabIndex] = true;
        var lessTxt = isPt ? "▲ Mostrar menos" : "▲ Show less";
        btn.querySelector("span").innerText = lessTxt;
    } else {
        hiddenMatches.forEach(function(el, idx) {
            if (idx >= 8) {
                el.classList.add("match-hidden");
            }
        });
        tabExpandedState[tabIndex] = false;
        var rem = totalCount - 8;
        var moreTxt = isPt ? "▼ Mostrar mais (" + rem + " restantes)" : "▼ Show more (" + rem + " remaining)";
        btn.querySelector("span").innerText = moreTxt;

        // Smoothly scroll back to the top of the tab container so context is kept
        var tabContainer = document.querySelector(".cache-tabs-nav");
        if (tabContainer) {
            tabContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    }

}

function switchCacheTab(tabIndex) {
    var buttons = document.querySelectorAll(".cache-tab-btn");
    var contents = document.querySelectorAll(".cache-tab-content");
    
    buttons.forEach(function(btn, i) {
        if (i === tabIndex) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    contents.forEach(function(content, i) {
        if (i === tabIndex) {
            content.classList.add("active");
            content.classList.remove("tab-anim-slide-in");

            // Dynamically set index --i on all visible match cards
            var visibleMatches = content.querySelectorAll(".match-item:not(.match-hidden)");
            visibleMatches.forEach(function(item, idx) {
                item.style.setProperty("--i", idx);
            });
            content.style.setProperty("--total-items", visibleMatches.length);

            // Trigger animation reflow on explicit user tab switch
            void content.offsetWidth;
            content.classList.add("tab-anim-slide-in");
        } else {
            content.classList.remove("active");
            content.classList.remove("tab-anim-slide-in");
        }
    });
}

var currentTimelinePhase = sessionStorage.getItem("blaze_timeline_phase") || "early";
var PHASES_ORDER = ["early", "mid", "late"];
var PHASE_NAMES = {
    "early": "Early Game (0-14m)",
    "mid": "Mid Game (14-25m)",
    "late": "Late Game (25m+)"
};

var isPhaseExpanded = sessionStorage.getItem("blaze_phase_expanded") === "true";

function syncTimelineState() {
    var i18n = window.REPORT_I18N || {};

    // 1. Process items inside both timeline panes
    ["timelinePaneKills", "timelinePaneItems"].forEach(function(paneId) {
        var pane = document.getElementById(paneId);
        if (!pane) return;
        var items = pane.querySelectorAll(".event-item");
        var visibleCountInCurrentPhase = 0;

        items.forEach(function(el) {
            var p = el.getAttribute("data-phase") || "early";
            var matchesPhase = (p === currentTimelinePhase);
            if (!matchesPhase) {
                el.style.display = "none";
            } else {
                if (!isPhaseExpanded && visibleCountInCurrentPhase >= 8) {
                    el.style.display = "none";
                } else {
                    el.style.display = "";
                }
                visibleCountInCurrentPhase++;
            }
        });
    });

    // 2. Count events per phase in the currently active pane for header & navigation buttons
    var paneKills = document.getElementById("timelinePaneKills");
    var paneItems = document.getElementById("timelinePaneItems");
    var activePane = (paneItems && paneItems.classList.contains("active")) ? paneItems : paneKills;
    
    var phaseCounts = { "early": 0, "mid": 0, "late": 0 };
    if (activePane) {
        var activeItems = activePane.querySelectorAll(".event-item");
        activeItems.forEach(function(el) {
            var p = el.getAttribute("data-phase") || "early";
            if (phaseCounts[p] !== undefined) {
                phaseCounts[p]++;
            }
        });
    }

    // 3. Update Phase Filter Buttons (Highlight active, gray out if 0 events in active tab)
    var filterBtns = document.querySelectorAll(".phase-filter-btn");
    filterBtns.forEach(function(b) {
        var onclickAttr = b.getAttribute("onclick") || "";
        var phaseMatch = onclickAttr.match(/'(early|mid|late)'/);
        if (phaseMatch) {
            var ph = phaseMatch[1];
            var count = phaseCounts[ph] || 0;
            if (count === 0) {
                b.classList.add("phase-disabled");
                b.style.opacity = "0.35";
                b.style.cursor = "not-allowed";
                b.style.pointerEvents = "none";
            } else {
                b.classList.remove("phase-disabled");
                b.style.opacity = "";
                b.style.cursor = "pointer";
                b.style.pointerEvents = "";
            }
            if (ph === currentTimelinePhase) {
                b.classList.add("active");
            } else {
                b.classList.remove("active");
            }
        }
    });

    // Update Top & Footer Expand / Collapse Buttons
    var topToggleBtn = document.getElementById("toggleTimelineTopBtn");
    var footerToggleBtn = document.getElementById("timelineTogglePhaseBtn");
    var totalInPhase = phaseCounts[currentTimelinePhase] || 0;
    var hasMoreInPhase = (totalInPhase > 8);

    var toggleTxt = isPhaseExpanded ? (i18n.collapse_timeline || "Recolher ⬆") : (i18n.expand_timeline || "Expandir ⬇");

    if (topToggleBtn) {
        if (hasMoreInPhase) {
            topToggleBtn.style.display = "inline-block";
            topToggleBtn.innerText = toggleTxt;
        } else {
            topToggleBtn.style.display = "none";
        }
    }

    if (footerToggleBtn) {
        if (hasMoreInPhase) {
            footerToggleBtn.style.display = "inline-flex";
            footerToggleBtn.innerText = toggleTxt;
        } else {
            footerToggleBtn.style.display = "none";
        }
    }

    // Update Next / Prev Phase Footer Buttons
    var currIdx = PHASES_ORDER.indexOf(currentTimelinePhase);
    var prevBtn = document.getElementById("timelinePrevPhaseBtn");
    var nextBtn = document.getElementById("timelineNextPhaseBtn");

    if (prevBtn) {
        var hasValidPrev = false;
        var prevTargetIdx = -1;
        for (var i = currIdx - 1; i >= 0; i--) {
            if (phaseCounts[PHASES_ORDER[i]] > 0) {
                hasValidPrev = true;
                prevTargetIdx = i;
                break;
            }
        }
        if (hasValidPrev) {
            prevBtn.style.display = "inline-flex";
            prevBtn.innerText = prevTargetIdx === 0 ? (i18n.nav_prev_early || "⬅ Early Game") : (i18n.nav_prev_mid || "⬅ Mid Game");
            prevBtn.setAttribute("data-target-idx", String(prevTargetIdx));
        } else {
            prevBtn.style.display = "none";
        }
    }

    if (nextBtn) {
        var hasValidNext = false;
        var nextTargetIdx = -1;
        for (var j = currIdx + 1; j < PHASES_ORDER.length; j++) {
            if (phaseCounts[PHASES_ORDER[j]] > 0) {
                hasValidNext = true;
                nextTargetIdx = j;
                break;
            }
        }
        if (hasValidNext) {
            nextBtn.style.display = "inline-flex";
            nextBtn.innerText = nextTargetIdx === 1 ? (i18n.nav_next_mid || "Avançar para Mid Game ➡") : (i18n.nav_next_late || "Avançar para Late Game ➡");
            nextBtn.setAttribute("data-target-idx", String(nextTargetIdx));
        } else {
            nextBtn.style.display = "none";
        }
    }
}

function togglePhaseExpansion() {
    isPhaseExpanded = !isPhaseExpanded;
    sessionStorage.setItem("blaze_phase_expanded", String(isPhaseExpanded));
    syncTimelineState();
}

function filterTimelinePhase(phase, btnEl) {
    currentTimelinePhase = phase;
    sessionStorage.setItem("blaze_timeline_phase", phase);
    syncTimelineState();
}

function navigateTimelinePhase(dir, btnEl) {
    var targetIdx = btnEl && btnEl.getAttribute("data-target-idx");
    var newIdx;
    if (targetIdx !== null && targetIdx !== undefined && targetIdx !== "") {
        newIdx = parseInt(targetIdx, 10);
    } else {
        var currIdx = PHASES_ORDER.indexOf(currentTimelinePhase);
        newIdx = currIdx + dir;
    }
    if (newIdx >= 0 && newIdx < PHASES_ORDER.length) {
        currentTimelinePhase = PHASES_ORDER[newIdx];
        sessionStorage.setItem("blaze_timeline_phase", currentTimelinePhase);
        syncTimelineState();
        
        // Smooth scroll to top of timeline controls bar
        var bar = document.querySelector(".timeline-controls-bar");
        if (bar) {
            bar.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }
}

function switchTimelineTab(tabName, btnEl) {
    var tabs = document.querySelectorAll(".timeline-tab-btn");
    tabs.forEach(function(b) { b.classList.remove("active"); });
    if (btnEl) btnEl.classList.add("active");

    var paneKills = document.getElementById("timelinePaneKills");
    var paneItems = document.getElementById("timelinePaneItems");

    if (tabName === "kills") {
        if (paneKills) paneKills.classList.add("active");
        if (paneItems) paneItems.classList.remove("active");
    } else {
        if (paneKills) paneKills.classList.remove("active");
        if (paneItems) paneItems.classList.add("active");
    }
    syncTimelineState();
}

function toggleTimeline() {
    var newState = !timelineExpanded;
    sessionStorage.setItem("blaze_timeline_expanded", String(newState));
    syncTimelineState();
}

function initSmartTooltips() {
    document.addEventListener("mouseover", function(e) {
        var trigger = e.target.closest(".stat-tooltip-trigger");
        if (!trigger) return;
        var popup = trigger.querySelector(".stat-popup-card");
        if (!popup) return;

        var rect = trigger.getBoundingClientRect();
        var cardHeight = popup.offsetHeight || 300;
        // Flip downwards aggressively with 60px buffer to protect the top
        if (rect.top < (cardHeight + 60)) {
            popup.classList.add("popup-flipped");
        } else {
            popup.classList.remove("popup-flipped");
        }
    });
}

window.addEventListener("DOMContentLoaded", function() {
    syncTimelineState();
    initSmartTooltips();
});

function autoResizeTextarea() {
    var ta = document.getElementById("rawSummaryText");
    if (ta) {
        ta.style.height = "auto";
        ta.style.height = (ta.scrollHeight + 10) + "px";
    }
}
window.addEventListener("load", autoResizeTextarea);

function copyRawSummary() {
    var copyText = document.getElementById("rawSummaryText");
    if (!copyText) return;
    copyText.select();
    copyText.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(copyText.value);
    
    var btn = document.querySelector(".copy-btn");
    if (btn) {
        var originalText = btn.innerText;
        btn.innerText = (window.REPORT_I18N && window.REPORT_I18N.copied) ? window.REPORT_I18N.copied : "Copiado! ✓";
        btn.style.background = "#16a34a";
        setTimeout(function() {
            btn.innerText = originalText;
            btn.style.background = "#2563eb";
        }, 2000);
    }
}

// Global Custom Tooltip Engine
function initCustomTooltips() {
    var tooltip = document.createElement("div");
    tooltip.className = "custom-tooltip";
    document.body.appendChild(tooltip);

    var activeEl = null;

    document.addEventListener("mouseover", function(e) {
        var target = e.target.closest("[title], [data-tooltip]");
        if (!target) return;

        if (target.hasAttribute("title") && !target.hasAttribute("data-tooltip")) {
            var rawTitle = target.getAttribute("title");
            if (rawTitle && rawTitle.trim()) {
                target.setAttribute("data-tooltip", rawTitle);
                target.removeAttribute("title");
            }
        }

        var text = target.getAttribute("data-tooltip");
        if (!text) return;

        activeEl = target;
        if (text.includes("<") && text.includes(">")) {
            tooltip.innerHTML = text;
        } else {
            tooltip.textContent = text;
        }
        tooltip.classList.add("visible");
        positionTooltip(e);

    });

    document.addEventListener("mousemove", function(e) {
        if (!activeEl) return;
        positionTooltip(e);
    });

    document.addEventListener("mouseout", function(e) {
        if (!activeEl) return;
        var related = e.relatedTarget;
        if (related && activeEl.contains(related)) return;
        activeEl = null;
        tooltip.classList.remove("visible");
    });

    function positionTooltip(e) {
        var gap = 12;
        var x = e.clientX + gap;
        var y = e.clientY + gap;

        var rect = tooltip.getBoundingClientRect();
        if (x + rect.width > window.innerWidth - 10) {
            x = e.clientX - rect.width - gap;
        }
        if (y + rect.height > window.innerHeight - 10) {
            y = e.clientY - rect.height - gap;
        }
        if (x < 10) x = 10;
        if (y < 10) y = 10;

        tooltip.style.left = x + "px";
        tooltip.style.top = y + "px";
    }
}
window.addEventListener("DOMContentLoaded", initCustomTooltips);

// Trigger sleek loading bar on analyze button click
document.addEventListener("click", function(e) {
    var btn = e.target.closest(".btn-analyze");
    if (btn) {
        btn.classList.add("is-loading");
    }
});

// ⚡ Smart Riot ID Paste / Input Splitter (Paste "Name#TAG" -> splits into Name & Tag)
function initRiotIdSmartPaste() {
    var nameInput = document.querySelector('input[name="game_name"]');
    var tagInput = document.querySelector('input[name="tag_line"]');
    if (!nameInput || !tagInput) return;

    function handleRiotIdSplit(val) {
        if (!val || typeof val !== "string" || !val.includes("#")) return false;
        var parts = val.split("#");
        var namePart = parts[0].trim();
        var tagPart = parts.slice(1).join("#").trim();
        nameInput.value = namePart;
        tagInput.value = tagPart;
        tagInput.focus();
        return true;
    }

    nameInput.addEventListener("paste", function(e) {
        var pasteData = (e.clipboardData || window.clipboardData).getData("text");
        if (pasteData && pasteData.includes("#")) {
            e.preventDefault();
            handleRiotIdSplit(pasteData);
        }
    });

    nameInput.addEventListener("input", function() {
        if (nameInput.value && nameInput.value.includes("#")) {
            handleRiotIdSplit(nameInput.value);
        }
    });
}

document.addEventListener("DOMContentLoaded", initRiotIdSmartPaste);
window.addEventListener("load", initRiotIdSmartPaste);






