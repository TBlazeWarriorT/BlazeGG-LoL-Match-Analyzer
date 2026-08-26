var timelineExpanded = false;

function promptSearchSummoner(name, tag) {
    if (!name || !tag) return;
    var msg = (window.REPORT_I18N && window.REPORT_I18N.lang === 'pt_BR' || document.documentElement.lang.includes('pt')) 
        ? "Deseja buscar as partidas de " + name + "#" + tag + "?"
        : "Do you want to search matches for " + name + "#" + tag + "?";
    if (confirm(msg)) {
        var lang = (document.documentElement.lang.includes('pt')) ? 'pt_BR' : 'en_US';
        window.location.href = "/search?game_name=" + encodeURIComponent(name) + "&tag_line=" + encodeURIComponent(tag) + "&lang=" + lang;
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
        } else {
            content.classList.remove("active");
        }
    });
}

function toggleTimeline() {
    var hiddenItems = document.querySelectorAll(".events-list .timeline-hidden, .events-list .timeline-visible-expanded");
    var btn = document.getElementById("toggleTimelineBtn");
    var topBtn = document.getElementById("toggleTimelineTopBtn");
    if (!timelineExpanded) {
        hiddenItems.forEach(function(el) {
            el.classList.remove("timeline-hidden");
            el.classList.add("timeline-visible-expanded");
        });
        timelineExpanded = true;
        var lessTxt = window.REPORT_I18N ? window.REPORT_I18N.show_less : "Mostrar menos";
        if (btn) btn.innerText = lessTxt;
        if (topBtn) topBtn.innerText = lessTxt;
    } else {
        hiddenItems.forEach(function(el) {
            el.classList.add("timeline-hidden");
            el.classList.remove("timeline-visible-expanded");
        });
        timelineExpanded = false;
        var moreTxt = window.REPORT_I18N ? window.REPORT_I18N.show_more : "Mostrar mais eventos";
        if (btn) btn.innerText = moreTxt;
        if (topBtn) topBtn.innerText = moreTxt;
    }
}

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

