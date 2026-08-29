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

function syncTimelineState() {
    var isExpanded = sessionStorage.getItem("blaze_timeline_expanded") === "true";
    timelineExpanded = isExpanded;
    var hiddenItems = document.querySelectorAll(".events-list .timeline-hidden, .events-list .timeline-visible-expanded");
    var btn = document.getElementById("toggleTimelineBtn");
    var topBtn = document.getElementById("toggleTimelineTopBtn");
    if (!btn && !topBtn) return;

    if (timelineExpanded) {
        hiddenItems.forEach(function(el) {
            el.classList.remove("timeline-hidden");
            el.classList.add("timeline-visible-expanded");
        });
        var lessTxt = window.REPORT_I18N ? window.REPORT_I18N.show_less : "Mostrar menos";
        if (btn) btn.innerText = lessTxt;
        if (topBtn) topBtn.innerText = lessTxt;
    } else {
        hiddenItems.forEach(function(el) {
            el.classList.add("timeline-hidden");
            el.classList.remove("timeline-visible-expanded");
        });
        var moreTxt = window.REPORT_I18N ? window.REPORT_I18N.show_more : "Mostrar mais eventos";
        if (btn) btn.innerText = moreTxt;
        if (topBtn) topBtn.innerText = moreTxt;
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
}

function toggleTimeline() {
    var newState = !timelineExpanded;
    sessionStorage.setItem("blaze_timeline_expanded", String(newState));
    syncTimelineState();
}

window.addEventListener("DOMContentLoaded", syncTimelineState);

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

// Clear stuck loading states on browser back/forward (BFCache navigation)
window.addEventListener("pageshow", function(e) {
    document.querySelectorAll(".btn-analyze.is-loading").forEach(function(btn) {
        btn.classList.remove("is-loading");
    });
});

function swapPageContent(targetUrl, pushToHistory) {
    fetch(targetUrl)
        .then(function(res) { return res.text(); })
        .then(function(htmlText) {
            var parser = new DOMParser();
            var doc = parser.parseFromString(htmlText, "text/html");

            document.title = doc.title;
            document.documentElement.lang = doc.documentElement.lang;

            var currentContainer = document.querySelector(".container");
            var newContainer = doc.querySelector(".container");
            if (currentContainer && newContainer) {
                currentContainer.innerHTML = newContainer.innerHTML;
            }

            var currentPicker = document.querySelector(".lang-picker");
            var newPicker = doc.querySelector(".lang-picker");
            if (currentPicker && newPicker) {
                currentPicker.innerHTML = newPicker.innerHTML;
            }

            if (pushToHistory) {
                window.history.pushState({ url: targetUrl }, "", targetUrl);
            }

            if (typeof autoResizeTextarea === "function") autoResizeTextarea();
            if (typeof syncTimelineState === "function") syncTimelineState();
            if (typeof initRiotIdSmartPaste === "function") initRiotIdSmartPaste();
        })
        .catch(function() {
            window.location.href = targetUrl;
        });
}

// ⚡ Seamless In-Place Language Switching (Zero reload, zero scroll jump)
document.addEventListener("click", function(e) {
    var langLink = e.target.closest(".lang-btn");
    if (!langLink || langLink.classList.contains("active")) return;
    
    e.preventDefault();
    var targetUrl = langLink.getAttribute("href");
    if (!targetUrl) return;

    swapPageContent(targetUrl, true);
});

// Handle browser back/forward buttons seamlessly
window.addEventListener("popstate", function() {
    swapPageContent(window.location.href, false);
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






