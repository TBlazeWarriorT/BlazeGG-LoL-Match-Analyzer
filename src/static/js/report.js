var timelineExpanded = false;
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

